"""M1 sample source job.

外部 API や crawler には接続せず、deterministic fixture から SourceRecord、
Advisory、DraftPost の縦串を作る。
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any, cast

from .llm import DraftInput, LLMProvider, TargetAudience, Urgency
from .storage.models import Advisory, AuditEvent, DraftPost, Severity, SourceRecord
from .storage.port import StoragePort

SAMPLE_SOURCE_NAME = "sample-source"
SAMPLE_SOURCE_PARSER_VERSION = "sample-source-v1"
SAMPLE_TARGET_AUDIENCE: TargetAudience = "mixed"
SAMPLE_TARGET_LANGUAGE = "ja"
SAMPLE_TEMPLATE_ID = "site-page-v1"
SAMPLE_DEFAULT_PROMPT_VERSION = "v1"
SAMPLE_URGENCY: Urgency = "high"


@dataclass(frozen=True)
class SampleSourceCandidate:
    """sample source が返す投稿候補。"""

    external_id: str
    title: str
    summary: str
    source_url: str
    published_at: datetime
    updated_at: datetime
    severity: Severity
    cve_ids: Sequence[str]
    references: Sequence[Mapping[str, str]]
    tags: Sequence[str]


@dataclass(frozen=True)
class SampleSourceJobResult:
    """sample source job の結果。"""

    source_record: SourceRecord
    advisory: Advisory
    draft_post: DraftPost
    audit_events: Sequence[AuditEvent] = ()


def fetch_sample_source_candidates() -> tuple[SampleSourceCandidate, ...]:
    """投稿候補を deterministic に返す。外部通信はしない。"""
    published = datetime(2026, 6, 20, 9, 0, tzinfo=UTC)
    updated = datetime(2026, 6, 22, 10, 30, tzinfo=UTC)
    return (
        SampleSourceCandidate(
            external_id="sample-2026-0001",
            title="Example Product の重要なセキュリティ更新",
            summary=(
                "Example Product に権限昇格につながる可能性がある脆弱性が公開され、"
                "ベンダーから更新プログラムが案内されています。"
            ),
            source_url="https://example.com/security/sample-2026-0001",
            published_at=published,
            updated_at=updated,
            severity="high",
            cve_ids=("CVE-2026-0001",),
            references=(
                {
                    "label": "Example Vendor Advisory",
                    "url": "https://example.com/security/sample-2026-0001",
                    "type": "vendor",
                },
            ),
            tags=("sample", "m1", "vendor-advisory"),
        ),
    )


def advisory_from_sample_candidate(
    candidate: SampleSourceCandidate, *, now: datetime | None = None
) -> tuple[SourceRecord, Advisory]:
    """sample candidate を source metadata と Advisory に変換する。"""
    timestamp = _utc_now(now)
    raw_payload = _candidate_payload(candidate)
    raw_hash = _hash_json(raw_payload)
    source_record_id = f"sample-src-{raw_hash[:12]}"
    advisory_id = f"sample-advisory-{candidate.external_id}"

    source_record = SourceRecord(
        source_record_id=source_record_id,
        source_type="vendor",
        source_name=SAMPLE_SOURCE_NAME,
        source_url=candidate.source_url,
        retrieved_at=timestamp,
        raw_hash=raw_hash,
        parser_version=SAMPLE_SOURCE_PARSER_VERSION,
        created_at=timestamp,
        http_status=200,
    )
    advisory = Advisory(
        advisory_id=advisory_id,
        title=candidate.title,
        summary=candidate.summary,
        source_record_id=source_record_id,
        created_at=timestamp,
        normalized_at=timestamp,
        published_at=candidate.published_at,
        updated_at=candidate.updated_at,
        severity=candidate.severity,
        cve_ids=tuple(candidate.cve_ids),
        references=tuple(candidate.references),
        tags=tuple(candidate.tags),
    )
    return source_record, advisory


def run_sample_source_job(
    storage: StoragePort,
    provider: LLMProvider,
    *,
    now: datetime | None = None,
) -> tuple[SampleSourceJobResult, ...]:
    """sample source から DraftPost を生成し、StoragePort 経由で保存する。"""
    timestamp = _utc_now(now)
    metadata = provider.get_provider_metadata()
    prompt_version = metadata.prompt_version or SAMPLE_DEFAULT_PROMPT_VERSION
    correlation_id = uuid.uuid4().hex
    results: list[SampleSourceJobResult] = []

    for candidate in fetch_sample_source_candidates():
        source_record, advisory = advisory_from_sample_candidate(candidate, now=timestamp)
        draft_id = f"draft-{advisory.advisory_id}"
        audit_events = [
            _source_fetch_audit_event(
                source_record=source_record,
                advisory=advisory,
                correlation_id=correlation_id,
                now=timestamp,
            )
        ]
        existing_draft = storage.draft_posts.get(draft_id)
        if existing_draft is None:
            draft_output = provider.generate_draft(
                DraftInput(
                    advisory=_json_ready(asdict(advisory)),
                    target_audience=SAMPLE_TARGET_AUDIENCE,
                    target_language=SAMPLE_TARGET_LANGUAGE,
                    urgency=SAMPLE_URGENCY,
                    template_id=SAMPLE_TEMPLATE_ID,
                    prompt_version=prompt_version,
                    references=[dict(ref) for ref in advisory.references],
                )
            )
            draft = DraftPost(
                draft_id=draft_id,
                title=draft_output.title,
                audience=SAMPLE_TARGET_AUDIENCE,
                urgency=SAMPLE_URGENCY,
                summary_for_users=draft_output.summary_for_users,
                impact=draft_output.impact,
                status="generated",
                created_at=timestamp,
                updated_at=timestamp,
                advisory_id=advisory.advisory_id,
                advisory_ids=(advisory.advisory_id,),
                required_actions=tuple(draft_output.required_actions),
                admin_actions=tuple(draft_output.admin_actions),
                references=tuple(draft_output.references),
                generated_by_provider=metadata.provider_name,
                prompt_version=prompt_version,
                generation_input_hash=draft_output.generation_input_hash,
                validation_warnings=(
                    *draft_output.warnings,
                    *draft_output.uncertainty_notes,
                    *draft_output.validation_hints,
                ),
            )
            audit_events.append(
                _draft_generate_audit_event(
                    provider_name=metadata.provider_name,
                    provider_type=metadata.provider_type,
                    prompt_version=prompt_version,
                    source_record=source_record,
                    advisory=advisory,
                    draft=draft,
                    correlation_id=correlation_id,
                    now=timestamp,
                )
            )
        else:
            draft = existing_draft
        results.append(
            SampleSourceJobResult(
                source_record=source_record,
                advisory=advisory,
                draft_post=draft,
                audit_events=tuple(audit_events),
            )
        )

    with storage.transaction():
        for result in results:
            storage.source_records.upsert(result.source_record)
            storage.advisories.upsert(result.advisory)
            if storage.draft_posts.get(result.draft_post.draft_id) is None:
                storage.draft_posts.upsert(result.draft_post)
            for event in result.audit_events:
                storage.audit_events.append(event)
    return tuple(results)


def _source_fetch_audit_event(
    *,
    source_record: SourceRecord,
    advisory: Advisory,
    correlation_id: str,
    now: datetime,
) -> AuditEvent:
    return AuditEvent(
        audit_event_id=uuid.uuid4().hex,
        event_type="source_fetch",
        correlation_id=correlation_id,
        result="success",
        created_at=now,
        source_name=source_record.source_name,
        related_ids={
            "source_record_id": source_record.source_record_id,
            "advisory_id": advisory.advisory_id,
        },
    )


def _draft_generate_audit_event(
    *,
    provider_name: str,
    provider_type: str,
    prompt_version: str,
    source_record: SourceRecord,
    advisory: Advisory,
    draft: DraftPost,
    correlation_id: str,
    now: datetime,
) -> AuditEvent:
    related_ids: dict[str, object] = {
        "source_record_id": source_record.source_record_id,
        "advisory_id": advisory.advisory_id,
        "draft_id": draft.draft_id,
    }
    if draft.generation_input_hash:
        related_ids["generation_input_hash"] = draft.generation_input_hash
    return AuditEvent(
        audit_event_id=uuid.uuid4().hex,
        event_type="draft_generate",
        correlation_id=correlation_id,
        result="success",
        created_at=now,
        source_name=source_record.source_name,
        provider_name=provider_name,
        provider_type=provider_type,
        prompt_version=prompt_version,
        related_ids=related_ids,
    )


def _candidate_payload(candidate: SampleSourceCandidate) -> dict[str, Any]:
    return cast("dict[str, Any]", _json_ready(asdict(candidate)))


def _hash_json(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _json_ready(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [_json_ready(item) for item in value]
    return value


def _utc_now(now: datetime | None) -> datetime:
    value = now or datetime.now(UTC)
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("now must include timezone")
    return value.astimezone(UTC)


__all__ = [
    "SAMPLE_SOURCE_NAME",
    "SampleSourceCandidate",
    "SampleSourceJobResult",
    "advisory_from_sample_candidate",
    "fetch_sample_source_candidates",
    "run_sample_source_job",
]
