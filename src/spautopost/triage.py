"""Advisory normalization merge, priority scoring, and duplicate-post guard.

正本: Issue #14, docs/specs/normalization-and-triage.md, docs/specs/data-model.md.

責務:
- 複数 source 由来の Advisory を identity key（CVE / JVN / vendor advisory ID）で
  名寄せ（dedup）して 1 つの Advisory に統合する。
- 加点方式の priority score と urgency label を算出する（決定論・ローカルのみ）。
- 再投稿防止に使える stable な duplicate post key を生成する。

非責務（Issue #14 非対象）: ML ベースの優先度付け、資産台帳との完全照合、
自動公開判定、storage schema 変更（triage は computation であり DTO を変更しない）。
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from .storage.models import Advisory, Audience, Severity, Urgency

# --- scoring weights（docs/specs/normalization-and-triage.md の Priority Score 表） ---

SEVERITY_POINTS: Mapping[Severity, int] = {
    "critical": 40,
    "high": 30,
    "medium": 15,
    "low": 0,
    "unknown": 0,
}
KEV_LISTED_POINTS = 40
EXPLOIT_CONFIRMED_POINTS = 30
PATCH_AVAILABLE_POINTS = 10
INTERNAL_RELEVANCE_CONFIRMED_POINTS = 30
INTERNET_FACING_POINTS = 15
SOURCE_CONFIDENCE_LOW_PENALTY = -10

# urgency 閾値（同 Spec の推奨 urgency）。
URGENCY_EMERGENCY_MIN = 80
URGENCY_HIGH_MIN = 60
URGENCY_NORMAL_MIN = 30

# Severity Mapping（CVSS -> severity）。
CVSS_CRITICAL_MIN = 9.0
CVSS_HIGH_MIN = 7.0
CVSS_MEDIUM_MIN = 4.0
CVSS_LOW_MIN = 0.1

_SEVERITY_RANK: Mapping[Severity, int] = {
    "unknown": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}

# KEV 由来 tag（source_adapters.normalize_kev_document が付与する）。
_KEV_TAGS = frozenset({"kev", "known-exploited"})

ExploitStatus = Literal["confirmed", "likely", "unknown", "none"]
KevStatus = Literal["listed", "not_listed", "unknown"]
InternalRelevance = Literal["confirmed", "suspected", "unknown", "not_applicable"]
SourceConfidence = Literal["high", "medium", "low", "unknown"]


@dataclass(frozen=True)
class TriageSignals:
    """priority score の加点に使うトリアージ信号。

    kev_status は Advisory tags に KEV 印があれば ``listed`` に自動昇格する。
    その他の信号は data-model.md 由来で、既定値は安全側（加点なし）に倒す。
    """

    exploit_status: ExploitStatus = "unknown"
    kev_status: KevStatus = "unknown"
    patch_available: bool | None = None
    internal_relevance: InternalRelevance = "unknown"
    internet_facing: bool = False
    source_confidence: SourceConfidence = "medium"


@dataclass(frozen=True)
class TriageResult:
    """1 Advisory に対するトリアージ結果（storage には保存しない computation 値）。"""

    advisory: Advisory
    signals: TriageSignals
    priority_score: int
    urgency: Urgency
    duplicate_key: str


def severity_from_cvss(score: float | None) -> Severity:
    """CVSS base score を severity ラベルへ写像する。"""
    if score is None:
        return "unknown"
    if score >= CVSS_CRITICAL_MIN:
        return "critical"
    if score >= CVSS_HIGH_MIN:
        return "high"
    if score >= CVSS_MEDIUM_MIN:
        return "medium"
    if score >= CVSS_LOW_MIN:
        return "low"
    return "unknown"


def is_kev_listed(advisory: Advisory, signals: TriageSignals) -> bool:
    """明示信号または KEV tag のどちらかで KEV 掲載とみなす。"""
    if signals.kev_status == "listed":
        return True
    return any(tag in _KEV_TAGS for tag in advisory.tags)


def priority_score(advisory: Advisory, signals: TriageSignals) -> int:
    """加点方式で priority score を算出する（決定論）。"""
    score = SEVERITY_POINTS.get(advisory.severity, 0)
    if is_kev_listed(advisory, signals):
        score += KEV_LISTED_POINTS
    if signals.exploit_status == "confirmed":
        score += EXPLOIT_CONFIRMED_POINTS
    if signals.patch_available:
        score += PATCH_AVAILABLE_POINTS
    if signals.internal_relevance == "confirmed":
        score += INTERNAL_RELEVANCE_CONFIRMED_POINTS
    if signals.internet_facing:
        score += INTERNET_FACING_POINTS
    if signals.source_confidence == "low":
        score += SOURCE_CONFIDENCE_LOW_PENALTY
    return score


def urgency_for_score(score: int) -> Urgency:
    """priority score から urgency ラベルを決める。"""
    if score >= URGENCY_EMERGENCY_MIN:
        return "emergency"
    if score >= URGENCY_HIGH_MIN:
        return "high"
    if score >= URGENCY_NORMAL_MIN:
        return "normal"
    return "low"


def duplicate_post_key(advisory: Advisory, *, audience: Audience = "mixed") -> str:
    """再投稿防止に使う stable key。identity key + 正規化 title + audience から導く。"""
    cves = sorted(set(_upper(advisory.cve_ids)))
    jvns = sorted(set(_upper(advisory.jvn_ids)))
    vendors = sorted(set(_upper(advisory.vendor_advisory_ids)))
    parts = [
        "cve:" + ",".join(cves),
        "jvn:" + ",".join(jvns),
        "vendor:" + ",".join(vendors),
        "title:" + _normalize_title(advisory.title),
        "audience:" + audience,
    ]
    if not (cves or jvns or vendors):
        parts.append("advisory_id:" + advisory.advisory_id)
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return f"dup-{digest}"


def triage(
    advisory: Advisory,
    signals: TriageSignals | None = None,
    *,
    audience: Audience = "mixed",
) -> TriageResult:
    """1 Advisory に対して score / urgency / duplicate key を一括算出する。"""
    resolved = signals or TriageSignals()
    score = priority_score(advisory, resolved)
    return TriageResult(
        advisory=advisory,
        signals=resolved,
        priority_score=score,
        urgency=urgency_for_score(score),
        duplicate_key=duplicate_post_key(advisory, audience=audience),
    )


def merge_advisories(advisories: Iterable[Advisory], *, now: datetime) -> tuple[Advisory, ...]:
    """identity key を共有する Advisory を 1 つに統合する（dedup）。

    CVE / JVN / vendor advisory ID のいずれかを共有する Advisory は推移的に同一視する。
    identity key を持たない Advisory は統合せず単独で残す（人間レビュー対象）。
    結果は merged advisory_id で安定ソートして返す。
    """
    items = list(advisories)
    groups = _group_by_identity(items)
    merged = [_merge_group(group, now=now) for group in groups]
    return tuple(sorted(merged, key=lambda adv: adv.advisory_id))


# --- merge internals -------------------------------------------------------


def _group_by_identity(advisories: Sequence[Advisory]) -> list[list[Advisory]]:
    """union-find で identity token を共有する Advisory をグループ化する。"""
    parent = list(range(len(advisories)))

    def find(node: int) -> int:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(a: int, b: int) -> None:
        parent[find(a)] = find(b)

    token_owner: dict[str, int] = {}
    for index, advisory in enumerate(advisories):
        for token in _identity_tokens(advisory):
            owner = token_owner.get(token)
            if owner is None:
                token_owner[token] = index
            else:
                union(index, owner)

    grouped: dict[int, list[Advisory]] = {}
    for index, advisory in enumerate(advisories):
        grouped.setdefault(find(index), []).append(advisory)
    return list(grouped.values())


def _identity_tokens(advisory: Advisory) -> set[str]:
    tokens: set[str] = set()
    tokens.update(f"cve:{value}" for value in _upper(advisory.cve_ids))
    tokens.update(f"jvn:{value}" for value in _upper(advisory.jvn_ids))
    tokens.update(f"vendor:{value}" for value in _upper(advisory.vendor_advisory_ids))
    return tokens


def _merge_group(group: Sequence[Advisory], *, now: datetime) -> Advisory:
    if len(group) == 1:
        return group[0]

    primary = _primary_advisory(group)
    cvss_score = _max_cvss(group)
    severity = _max_severity(group)
    cvss_severity = severity_from_cvss(cvss_score)
    if _SEVERITY_RANK[cvss_severity] > _SEVERITY_RANK[severity]:
        severity = cvss_severity

    return Advisory(
        advisory_id=_merged_advisory_id(group),
        title=primary.title,
        summary=primary.summary,
        created_at=min(adv.created_at for adv in group),
        normalized_at=now,
        source_record_id=_shared_source_record_id(group),
        published_at=_min_optional(adv.published_at for adv in group),
        updated_at=_max_optional(adv.updated_at for adv in group),
        severity=severity,
        cve_ids=_sorted_normalized_union(adv.cve_ids for adv in group),
        jvn_ids=_sorted_normalized_union(adv.jvn_ids for adv in group),
        vendor_advisory_ids=_sorted_normalized_union(adv.vendor_advisory_ids for adv in group),
        cvss_version=primary.cvss_version,
        cvss_score=cvss_score,
        cvss_vector=primary.cvss_vector,
        references=_merged_references(group),
        tags=_sorted_union(adv.tags for adv in group),
    )


def _primary_advisory(group: Sequence[Advisory]) -> Advisory:
    """title / summary / CVSS メタを採用する代表 Advisory を決定論で選ぶ。"""
    return max(
        group,
        key=lambda adv: (
            _SEVERITY_RANK.get(adv.severity, 0),
            adv.cvss_score is not None,
            adv.cvss_score or 0.0,
            adv.advisory_id,
        ),
    )


def _merged_advisory_id(group: Sequence[Advisory]) -> str:
    for prefix, key in (("cve", "cve_ids"), ("jvn", "jvn_ids"), ("vendor", "vendor_advisory_ids")):
        values = _sorted_normalized_union(getattr(adv, key) for adv in group)
        if values:
            return f"merged-{prefix}-{values[0].lower()}"
    joined = "|".join(sorted(adv.advisory_id for adv in group))
    digest = hashlib.sha256(joined.encode("utf-8")).hexdigest()
    return f"merged-{digest[:16]}"


def _shared_source_record_id(group: Sequence[Advisory]) -> str | None:
    ids = {adv.source_record_id for adv in group}
    if len(ids) == 1:
        return next(iter(ids))
    return None


def _max_severity(group: Sequence[Advisory]) -> Severity:
    return max((adv.severity for adv in group), key=lambda sev: _SEVERITY_RANK.get(sev, 0))


def _max_cvss(group: Sequence[Advisory]) -> float | None:
    scores = [adv.cvss_score for adv in group if adv.cvss_score is not None]
    return max(scores) if scores else None


def _merged_references(group: Sequence[Advisory]) -> tuple[Mapping[str, str], ...]:
    by_url: dict[str, Mapping[str, str]] = {}
    no_url_refs: list[Mapping[str, str]] = []
    for advisory in group:
        for reference in advisory.references:
            url = reference.get("url", "")
            if not url:
                no_url_refs.append(reference)
            elif url not in by_url:
                by_url[url] = reference
    return tuple(by_url[url] for url in sorted(by_url)) + tuple(no_url_refs)


def _sorted_union(sequences: Iterable[Sequence[str]]) -> tuple[str, ...]:
    values: set[str] = set()
    for sequence in sequences:
        values.update(sequence)
    return tuple(sorted(values))


def _sorted_normalized_union(sequences: Iterable[Sequence[str]]) -> tuple[str, ...]:
    values: set[str] = set()
    for sequence in sequences:
        values.update(_upper(sequence))
    return tuple(sorted(values))


def _upper(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(value.upper() for value in values)


def _normalize_title(title: str) -> str:
    return " ".join(title.lower().split())


def _min_optional(values: Iterable[datetime | None]) -> datetime | None:
    present = [value for value in values if value is not None]
    return min(present) if present else None


def _max_optional(values: Iterable[datetime | None]) -> datetime | None:
    present = [value for value in values if value is not None]
    return max(present) if present else None
