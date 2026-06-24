"""Manual advisory input parsing and validation."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TypeGuard, cast
from urllib.parse import urlparse

import yaml

from .storage.models import Advisory, Severity, Urgency

PARSER_VERSION = "manual-advisory-v1"

_CVE_RE = re.compile(r"^CVE-\d{4}-\d{4,}$")
_JVN_RE = re.compile(r"^(JVNDB-\d{4}-\d{6}|JVN#\d{8}|JVNVU#\d{8})$")
_SEVERITIES = frozenset({"critical", "high", "medium", "low", "unknown"})
_URGENCIES = frozenset({"emergency", "high", "normal", "low"})
_REFERENCE_TYPES = frozenset({"vendor", "nvd", "jvn", "kev", "advisory", "patch", "other"})


class AdvisoryInputError(ValueError):
    """Manual advisory input validation failure."""

    def __init__(self, issues: Sequence[str]) -> None:
        self.issues = list(issues)
        super().__init__("\n".join(self.issues))


@dataclass(frozen=True)
class ManualAdvisoryInput:
    advisory: Advisory
    urgency: Urgency | None = None


def load_manual_advisory(path: Path, *, now: datetime | None = None) -> ManualAdvisoryInput:
    """Load a YAML / JSON advisory file into the existing Advisory DTO."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise AdvisoryInputError([f"input is not valid YAML/JSON: {exc}"]) from exc

    data = _as_mapping(raw)
    timestamp = _utc_now(now)
    return _manual_advisory_from_mapping(data, timestamp)


def _manual_advisory_from_mapping(
    data: Mapping[str, object], timestamp: datetime
) -> ManualAdvisoryInput:
    issues: list[str] = []
    title = _required_text(data, "title", issues)
    summary = _required_text(data, "summary", issues)
    references = _references(data, issues)
    severity = _severity(data, issues)
    urgency = _urgency(data, issues)
    cve_ids = _id_list(data, "cve_ids", _CVE_RE, "CVE ID", issues)
    jvn_ids = _id_list(data, "jvn_ids", _JVN_RE, "JVN ID", issues)
    vendor_advisory_ids = _text_list(data, "vendor_advisory_ids", issues)
    tags = _text_list(data, "tags", issues)
    published_at = _datetime_field(data, "published_at", issues)
    updated_at = _datetime_field(data, "updated_at", issues)
    advisory_id = _optional_text(data, "advisory_id", issues) or _generated_id(data)

    if issues:
        raise AdvisoryInputError(issues)

    return ManualAdvisoryInput(
        advisory=Advisory(
            advisory_id=advisory_id,
            title=title,
            summary=summary,
            created_at=timestamp,
            normalized_at=timestamp,
            published_at=published_at,
            updated_at=updated_at,
            severity=severity,
            cve_ids=cve_ids,
            jvn_ids=jvn_ids,
            vendor_advisory_ids=vendor_advisory_ids,
            references=references,
            tags=tags,
        ),
        urgency=urgency,
    )


def _as_mapping(raw: object) -> Mapping[str, object]:
    if not isinstance(raw, Mapping):
        raise AdvisoryInputError(["input root must be an object"])
    data: dict[str, object] = {}
    issues: list[str] = []
    for key, value in raw.items():
        if not isinstance(key, str):
            issues.append("input keys must be strings")
            continue
        data[key] = value
    if issues:
        raise AdvisoryInputError(issues)
    return data


def _required_text(data: Mapping[str, object], key: str, issues: list[str]) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        issues.append(f"{key} is required")
        return ""
    return value.strip()


def _optional_text(data: Mapping[str, object], key: str, issues: list[str]) -> str | None:
    if key not in data or data[key] is None:
        return None
    value = data[key]
    if not isinstance(value, str) or not value.strip():
        issues.append(f"{key} must be a non-empty string")
        return None
    return value.strip()


def _id_list(
    data: Mapping[str, object],
    key: str,
    pattern: re.Pattern[str],
    label: str,
    issues: list[str],
) -> tuple[str, ...]:
    values = _text_list(data, key, issues)
    for value in values:
        if not pattern.fullmatch(value):
            issues.append(f"{key} contains invalid {label}: {value}")
    return values


def _text_list(data: Mapping[str, object], key: str, issues: list[str]) -> tuple[str, ...]:
    if key not in data or data[key] is None:
        return ()
    value = data[key]
    if not _is_sequence(value):
        issues.append(f"{key} must be a list of strings")
        return ()
    items: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            issues.append(f"{key}[{index}] must be a non-empty string")
            continue
        items.append(item.strip())
    return tuple(items)


def _references(data: Mapping[str, object], issues: list[str]) -> tuple[Mapping[str, str], ...]:
    value = data.get("references")
    if not _is_sequence(value):
        issues.append("references is required")
        return ()
    if not value:
        issues.append("references must not be empty")
        return ()

    references: list[Mapping[str, str]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            issues.append(f"references[{index}] must be an object")
            continue
        ref = {str(key): ref_value for key, ref_value in item.items() if isinstance(key, str)}
        label = ref.get("label")
        url = ref.get("url")
        ref_type = ref.get("type")
        if not isinstance(label, str) or not label.strip():
            issues.append(f"references[{index}].label is required")
        if not isinstance(url, str) or not _valid_url(url):
            issues.append(f"references[{index}].url must be an http(s) URL")
        if not isinstance(ref_type, str) or ref_type not in _REFERENCE_TYPES:
            issues.append(f"references[{index}].type is invalid")
        if isinstance(label, str) and isinstance(url, str) and isinstance(ref_type, str):
            references.append({"label": label.strip(), "url": url.strip(), "type": ref_type})
    return tuple(references)


def _severity(data: Mapping[str, object], issues: list[str]) -> Severity:
    value = data.get("severity", "unknown")
    if not isinstance(value, str) or value not in _SEVERITIES:
        issues.append("severity is invalid")
        return "unknown"
    return cast("Severity", value)


def _urgency(data: Mapping[str, object], issues: list[str]) -> Urgency | None:
    if "urgency" not in data or data["urgency"] is None:
        return None
    value = data["urgency"]
    if not isinstance(value, str) or value not in _URGENCIES:
        issues.append("urgency is invalid")
        return None
    return cast("Urgency", value)


def _datetime_field(data: Mapping[str, object], key: str, issues: list[str]) -> datetime | None:
    if key not in data or data[key] is None:
        return None
    value = data[key]
    if not isinstance(value, str):
        issues.append(f"{key} must be an ISO-8601 datetime string")
        return None
    text = value.removesuffix("Z") + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        issues.append(f"{key} must be an ISO-8601 datetime string")
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        issues.append(f"{key} must include timezone")
        return None
    return parsed.astimezone(UTC)


def _valid_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _generated_id(data: Mapping[str, object]) -> str:
    payload = json.dumps(data, ensure_ascii=True, sort_keys=True, default=str)
    return "manual-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def _utc_now(now: datetime | None) -> datetime:
    value = now or datetime.now(UTC)
    if value.tzinfo is None or value.utcoffset() is None:
        raise AdvisoryInputError(["now must include timezone"])
    return value.astimezone(UTC)


def _is_sequence(value: object) -> TypeGuard[Sequence[object]]:
    return isinstance(value, Sequence) and not isinstance(value, str | bytes)
