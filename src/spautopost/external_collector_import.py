"""External collector からの normalized advisory import 境界。

正本: openspec/changes/issue-21-add-scheduler-external-collector-boundary/
      docs/specs/external-collector-boundary.md

責務:
- 外部 collector が生成した JSON/YAML ファイルを schema 検証して取り込む。
- validated advisory を SourceRecord + Advisory DTO に変換し StoragePort で保存する。
- 不正レコードは fail fast で reject し、有効なレコードのみ受け入れる。

非責務: API import / queue import（Port 定義のみ、実装は後続 Issue）。
        認証・認可・Secret。crawling 本体。
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse

import yaml

from .storage.models import Advisory, AuditEvent, SourceRecord
from .storage.port import StoragePort

IMPORT_SCHEMA_VERSION = "1.0"
IMPORT_PARSER_VERSION = "external-collector-import-v1"

_CVE_RE = re.compile(r"^CVE-\d{4}-\d{4,}$")
_JVN_RE = re.compile(r"^(JVNDB-\d{4}-\d{6}|JVN#\d{8}|JVNVU#\d{8})$")
_SEVERITIES = frozenset({"critical", "high", "medium", "low", "unknown"})


class ExternalCollectorImportError(ValueError):
    """import ファイル全体が無効な場合（ファイルレベルエラー）。"""


@dataclass(frozen=True)
class RejectedRecord:
    """schema 検証で reject されたレコードの情報。"""

    index: int
    reason: str
    raw: Mapping[str, object]


@dataclass(frozen=True)
class ImportResult:
    """import 処理の結果サマリー。"""

    accepted_count: int
    rejected_count: int
    rejected_records: Sequence[RejectedRecord]
    source_records: Sequence[SourceRecord]
    advisories: Sequence[Advisory]


# --- Port Protocol (将来の API / queue 実装者向け) -------------------------


class ExternalCollectorImportPort(Protocol):
    """外部 collector import の抽象 Port。

    将来の実装（API import / queue import）はこの Protocol を実装するだけでよく、
    SPAutoPost 本体の呼び出し側を変更しなくてよい。
    """

    def import_advisories(
        self, storage: StoragePort, *, now: datetime | None = None, dry_run: bool = False
    ) -> ImportResult: ...


# --- File import 実装 -------------------------------------------------------


@dataclass(frozen=True)
class FileExternalCollectorImporter:
    """JSON/YAML ファイルから normalized advisory を import する実装。"""

    path: Path

    def import_advisories(
        self, storage: StoragePort, *, now: datetime | None = None, dry_run: bool = False
    ) -> ImportResult:
        """ファイルを読み込み、schema 検証後に storage へ保存する。"""
        payload = _load_file(self.path)
        _validate_envelope(payload)
        return _process_advisories(payload, storage, now=now, dry_run=dry_run)


def import_from_file(
    path: Path,
    storage: StoragePort,
    *,
    now: datetime | None = None,
    dry_run: bool = False,
) -> ImportResult:
    """convenience: ファイルを読み込んで storage へ保存する。"""
    return FileExternalCollectorImporter(path=path).import_advisories(
        storage, now=now, dry_run=dry_run
    )


# --- Schema validation ------------------------------------------------------


def _load_file(path: Path) -> Mapping[str, object]:
    """JSON または YAML ファイルを読み込む。"""
    text = path.read_text(encoding="utf-8")
    try:
        if path.suffix.lower() in {".yaml", ".yml"}:
            data = yaml.safe_load(text)
        else:
            data = json.loads(text)
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise ExternalCollectorImportError(f"ファイルの解析に失敗しました: {exc}") from exc
    if not isinstance(data, dict):
        raise ExternalCollectorImportError(
            "import ファイルのルートはオブジェクトである必要があります"
        )
    return data


def _validate_envelope(payload: Mapping[str, object]) -> None:
    """import ファイルのエンベロープ（必須フィールド）を検証する。"""
    issues: list[str] = []
    schema_version = _nonempty_str(payload.get("schema_version"))
    if not schema_version:
        issues.append("schema_version は必須です")
    elif schema_version != IMPORT_SCHEMA_VERSION:
        issues.append(
            f"schema_version '{schema_version}' はサポート外です（対応: '{IMPORT_SCHEMA_VERSION}'）"
        )
    if not _nonempty_str(payload.get("producer")):
        issues.append("producer は必須です")
    if not _nonempty_str(payload.get("generated_at")):
        issues.append("generated_at は必須です")
    else:
        _parse_datetime(str(payload["generated_at"]), "generated_at", issues)
    advisories = payload.get("advisories")
    if not isinstance(advisories, list):
        issues.append("advisories は配列である必要があります")
    if issues:
        raise ExternalCollectorImportError("; ".join(issues))


def _validate_advisory(raw: Mapping[str, object], index: int) -> list[str]:
    """advisory レコードの検証。issues が空なら有効。"""
    issues: list[str] = []
    if not _nonempty_str(raw.get("title")):
        issues.append(f"advisories[{index}].title は必須です")
    refs = raw.get("references")
    if not isinstance(refs, list) or len(refs) == 0:
        issues.append(f"advisories[{index}].references は 1 件以上必要です")
    else:
        for ri, ref in enumerate(refs):
            if not isinstance(ref, dict):
                issues.append(
                    f"advisories[{index}].references[{ri}] はオブジェクトである必要があります"
                )
                continue
            if not _nonempty_str(ref.get("label")):
                issues.append(f"advisories[{index}].references[{ri}].label は必須です")
            url = ref.get("url")
            if not isinstance(url, str) or not _valid_url(url.strip()):
                issues.append(
                    f"advisories[{index}].references[{ri}].url は http(s) URL である必要があります"
                )
    severity = raw.get("severity")
    if severity is not None and (not isinstance(severity, str) or severity not in _SEVERITIES):
        issues.append(f"advisories[{index}].severity は無効な値です: {severity}")
    for key, pattern, name in [("cve_ids", _CVE_RE, "CVE ID"), ("jvn_ids", _JVN_RE, "JVN ID")]:
        val = raw.get(key)
        if val is not None:
            if not isinstance(val, list):
                issues.append(f"advisories[{index}].{key} は配列である必要があります")
            else:
                for i, item in enumerate(val):
                    if not isinstance(item, str):
                        issues.append(f"advisories[{index}].{key}[{i}] は文字列である必要があります")
                    elif not pattern.fullmatch(item.strip()):
                        issues.append(
                            f"advisories[{index}].{key} に無効な {name} が含まれています: {item}"
                        )
    vendor_ids = raw.get("vendor_advisory_ids")
    if vendor_ids is not None:
        if not isinstance(vendor_ids, list):
            issues.append(f"advisories[{index}].vendor_advisory_ids は配列である必要があります")
        else:
            for i, item in enumerate(vendor_ids):
                if not isinstance(item, str):
                    issues.append(
                        f"advisories[{index}].vendor_advisory_ids[{i}] は文字列である必要があります"
                    )
    return issues


def _process_advisories(
    payload: Mapping[str, object],
    storage: StoragePort,
    *,
    now: datetime | None,
    dry_run: bool = False,
) -> ImportResult:
    """advisory を変換し storage に保存する。"""
    timestamp = _utc_now(now)
    producer = str(payload["producer"])
    raw_list: list[Mapping[str, object]] = payload["advisories"]  # type: ignore[assignment]

    accepted: list[tuple[SourceRecord, Advisory]] = []
    rejected: list[RejectedRecord] = []
    correlation_id = _nonempty_str(payload.get("correlation_id")) or uuid.uuid4().hex
    seen_advisory_ids: set[str] = set()

    for index, raw in enumerate(raw_list):
        if not isinstance(raw, dict):
            rejected.append(
                RejectedRecord(
                    index=index, reason="advisory はオブジェクトである必要があります", raw={}
                )
            )
            continue
        issues = _validate_advisory(raw, index)
        if issues:
            rejected.append(RejectedRecord(index=index, reason="; ".join(issues), raw=raw))
            continue
        pair = _to_storage_pair(raw, producer=producer, timestamp=timestamp)
        adv_id = pair[1].advisory_id
        if adv_id in seen_advisory_ids:
            rejected.append(
                RejectedRecord(
                    index=index,
                    reason=f"advisory_id '{adv_id}' がバッチ内で重複しています",
                    raw=raw,
                )
            )
            continue
        seen_advisory_ids.add(adv_id)
        accepted.append(pair)

    source_records = [p[0] for p in accepted]
    advisories = [p[1] for p in accepted]

    if not dry_run:
        audit_event = _import_audit_event(
            producer=producer,
            accepted=len(accepted),
            rejected=len(rejected),
            correlation_id=correlation_id,
            now=timestamp,
        )
        with storage.transaction():
            for sr, adv in accepted:
                storage.source_records.upsert(sr)
                storage.advisories.upsert(adv)
            storage.audit_events.append(audit_event)

    return ImportResult(
        accepted_count=len(accepted),
        rejected_count=len(rejected),
        rejected_records=tuple(rejected),
        source_records=tuple(source_records),
        advisories=tuple(advisories),
    )


def _to_storage_pair(
    raw: Mapping[str, object],
    *,
    producer: str,
    timestamp: datetime,
) -> tuple[SourceRecord, Advisory]:
    """raw advisory dict を SourceRecord + Advisory に変換する。"""
    raw_hash = _hash_json(dict(raw))
    source_record_id = f"ext-{producer}-{raw_hash[:12]}"
    raw_advisory_id = _nonempty_str(raw.get("advisory_id")) or raw_hash[:16]
    # Hash the (producer, advisory_id) tuple to make the final ID unambiguous regardless
    # of whether producer or advisory_id contain the '-' delimiter.
    advisory_id_hash = _hash_json({"producer": producer, "advisory_id": raw_advisory_id})[:12]
    title = str(raw["title"]).strip()
    summary = _nonempty_str(raw.get("summary")) or title
    refs: list[Mapping[str, str]] = []
    raw_refs = raw.get("references") or []
    raw_refs = raw_refs if isinstance(raw_refs, list) else []
    for ref in raw_refs:
        if isinstance(ref, dict):
            label = str(ref.get("label", "")).strip()
            url = str(ref.get("url", "")).strip()
            ref_type = str(ref.get("type", "other")).strip()
            if label and url:
                refs.append({"label": label, "url": url, "type": ref_type})
    source_url = refs[0]["url"] if refs else None

    severity = str(raw.get("severity") or "unknown")
    if severity not in _SEVERITIES:
        severity = "unknown"

    source_record = SourceRecord(
        source_record_id=source_record_id,
        source_type="external_collector",
        source_name=producer,
        source_url=source_url,
        retrieved_at=timestamp,
        raw_hash=raw_hash,
        parser_version=IMPORT_PARSER_VERSION,
        created_at=timestamp,
    )
    advisory = Advisory(
        advisory_id=f"ext-{producer}-{advisory_id_hash}",
        title=title,
        summary=summary,
        source_record_id=source_record_id,
        created_at=timestamp,
        normalized_at=timestamp,
        severity=severity,  # type: ignore[arg-type]
        cve_ids=tuple(_text_list(raw, "cve_ids")),
        jvn_ids=tuple(_text_list(raw, "jvn_ids")),
        vendor_advisory_ids=tuple(_text_list(raw, "vendor_advisory_ids")),
        references=tuple(refs),
        tags=("external_collector", f"producer:{producer}"),
    )
    return source_record, advisory


def _import_audit_event(
    *,
    producer: str,
    accepted: int,
    rejected: int,
    correlation_id: str,
    now: datetime,
) -> AuditEvent:
    return AuditEvent(
        audit_event_id=uuid.uuid4().hex,
        event_type="source_fetch",
        correlation_id=correlation_id,
        result="success" if rejected == 0 else "warning",
        created_at=now,
        source_name=producer,
        related_ids={
            "accepted_count": accepted,
            "rejected_count": rejected,
        },
    )


# --- Helpers ----------------------------------------------------------------


def _nonempty_str(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _valid_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _text_list(raw: Mapping[str, object], key: str) -> list[str]:
    value = raw.get(key)
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if isinstance(item, str) and str(item).strip()]


def _parse_datetime(value: str, key: str, issues: list[str]) -> datetime | None:
    text = value.removesuffix("Z") + "+00:00" if value.endswith("Z") else value
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        issues.append(f"{key} は ISO-8601 形式の日時である必要があります")
        return None


def _hash_json(value: Mapping[str, object]) -> str:
    raw = json.dumps(value, ensure_ascii=True, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _utc_now(now: datetime | None) -> datetime:
    value = now or datetime.now(UTC)
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("now must include timezone")
    return value.astimezone(UTC)
