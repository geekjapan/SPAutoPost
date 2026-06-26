"""SPAutoPost の設定ロードと検証。

設計の正本: docs/specs/configuration.md
ランタイム依存を増やさないため、検証は stdlib のみで実装する（pydantic 等は不採用）。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .errors import ConfigValidationError
from .secrets import iter_secret_refs

ENVIRONMENTS = frozenset({"development", "test", "production"})
STORAGE_PROVIDERS = frozenset({"postgresql", "sqlite"})
LLM_PROVIDERS = frozenset(
    {"production_api", "production_flow", "generic_api", "test_mock", "test_manual"}
)
SHAREPOINT_MODES = frozenset({"site-page", "list"})

_SECTION_KEYS: dict[str, frozenset[str]] = {
    "app": frozenset({"environment", "dry_run", "log_level"}),
    "server": frozenset({"admin_ui_enabled", "admin_api_enabled", "auth_provider"}),
    "storage": frozenset({"provider", "database_url", "sqlite_path"}),
    "llm": frozenset({"provider", "prompt_version"}),
    "sharepoint": frozenset(
        {
            "mode",
            "default_draft",
            "allow_publish",
            "tenant_id",
            "site_id",
            "page_library_id",
            "dedicated_site",
            "news_promote",
            "idempotency_scope",
        }
    ),
    "graph": frozenset({"local_poc_auth", "hosted_auth"}),
    "security": frozenset({"block_auto_publish", "require_approval", "redact_secrets_in_logs"}),
}
_FREEFORM_SECTIONS = frozenset({"sources"})
_ALLOWED_TOP = frozenset(_SECTION_KEYS) | _FREEFORM_SECTIONS


@dataclass(frozen=True)
class AppConfig:
    environment: str
    dry_run: bool
    log_level: str


@dataclass(frozen=True)
class StorageConfig:
    provider: str
    database_url: str | None
    sqlite_path: str | None


@dataclass(frozen=True)
class SharePointConfig:
    mode: str
    default_draft: bool
    allow_publish: bool
    tenant_id: str | None
    site_id: str | None
    page_library_id: str | None
    dedicated_site: bool
    news_promote: bool
    idempotency_scope: str | None


@dataclass(frozen=True)
class SecurityConfig:
    block_auto_publish: bool
    require_approval: bool
    redact_secrets_in_logs: bool


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    prompt_version: str | None


@dataclass(frozen=True)
class Config:
    app: AppConfig
    storage: StorageConfig
    sharepoint: SharePointConfig
    security: SecurityConfig
    llm: LLMConfig
    raw: Mapping[str, Any]


def load_and_validate(environment: str, config_dir: Path, environ: Mapping[str, str]) -> Config:
    """環境を選んで config を読み込み、検証済み Config を返す。"""
    raw = load_raw_config(environment, config_dir)
    return validate_config(raw, environ)


def load_raw_config(environment: str, config_dir: Path) -> dict[str, Any]:
    """``default.yml`` を基底に環境別ファイルを上書きした生の設定を返す。"""
    base = _read_yaml(config_dir / "default.yml")
    overlay_path = config_dir / f"{environment}.yml"
    overlay = _read_yaml(overlay_path) if overlay_path.exists() else {}
    return _deep_merge(base, overlay)


def validate_config(raw: Mapping[str, Any], environ: Mapping[str, str]) -> Config:
    """設定を検証する。問題があれば ConfigValidationError を送出する。"""
    issues: list[str] = []
    _validate_unknown_keys(raw, issues)
    app = _validate_app(raw, issues)
    storage = _validate_storage(raw, issues)
    sharepoint = _validate_sharepoint(raw, issues)
    security = _validate_security(raw, issues)
    llm = _validate_llm(raw, issues)
    _validate_publish_consistency(sharepoint, security, issues)
    _validate_secret_refs(raw, environ, issues)
    if issues:
        raise ConfigValidationError(issues)
    return Config(
        app=app, storage=storage, sharepoint=sharepoint, security=security, llm=llm, raw=raw
    )


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigValidationError([f"config file is not a mapping: {path}"])
    return data


def _deep_merge(base: Mapping[str, Any], overlay: Mapping[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = dict(base)
    for key, value in overlay.items():
        existing = merged.get(key)
        if isinstance(existing, Mapping) and isinstance(value, Mapping):
            merged[key] = _deep_merge(existing, value)
        else:
            merged[key] = value
    return merged


def _section(raw: Mapping[str, Any], name: str) -> dict[str, Any]:
    value = raw.get(name)
    return dict(value) if isinstance(value, Mapping) else {}


def _bool(sec: Mapping[str, Any], key: str, default: bool, path: str, issues: list[str]) -> bool:
    if key not in sec:
        return default
    value = sec[key]
    if not isinstance(value, bool):
        issues.append(f"{path} must be a boolean")
        return default
    return value


def _opt_str(sec: Mapping[str, Any], key: str, path: str, issues: list[str]) -> str | None:
    if key not in sec or sec[key] is None:
        return None
    value = sec[key]
    if not isinstance(value, str):
        issues.append(f"{path} must be a string")
        return None
    return value


def _validate_unknown_keys(raw: Mapping[str, Any], issues: list[str]) -> None:
    for key in raw:
        if key not in _ALLOWED_TOP:
            issues.append(f"unknown config key: {key}")
            continue
        if key in _FREEFORM_SECTIONS:
            continue
        section = raw[key]
        if isinstance(section, Mapping):
            allowed = _SECTION_KEYS[str(key)]
            for sub in section:
                if sub not in allowed:
                    issues.append(f"unknown config key: {key}.{sub}")


def _validate_app(raw: Mapping[str, Any], issues: list[str]) -> AppConfig:
    sec = _section(raw, "app")
    environment = sec.get("environment")
    if not isinstance(environment, str) or environment not in ENVIRONMENTS:
        issues.append(f"app.environment must be one of {sorted(ENVIRONMENTS)}")
        environment = "development"
    dry_run = _bool(sec, "dry_run", True, "app.dry_run", issues)
    log_level = _opt_str(sec, "log_level", "app.log_level", issues) or "info"
    return AppConfig(environment=environment, dry_run=dry_run, log_level=log_level)


def _validate_storage(raw: Mapping[str, Any], issues: list[str]) -> StorageConfig:
    sec = _section(raw, "storage")
    provider = sec.get("provider")
    if provider not in STORAGE_PROVIDERS:
        issues.append(f"storage.provider must be one of {sorted(STORAGE_PROVIDERS)}")
    database_url = _opt_str(sec, "database_url", "storage.database_url", issues)
    sqlite_path = _opt_str(sec, "sqlite_path", "storage.sqlite_path", issues)
    if provider == "postgresql" and not database_url:
        issues.append("storage.database_url is required when provider=postgresql")
    if provider == "sqlite" and not sqlite_path:
        issues.append("storage.sqlite_path is required when provider=sqlite")
    return StorageConfig(
        provider=provider if isinstance(provider, str) else "",
        database_url=database_url,
        sqlite_path=sqlite_path,
    )


def _validate_sharepoint(raw: Mapping[str, Any], issues: list[str]) -> SharePointConfig:
    sec = _section(raw, "sharepoint")
    mode = sec.get("mode")
    if mode not in SHAREPOINT_MODES:
        issues.append(f"sharepoint.mode must be one of {sorted(SHAREPOINT_MODES)}")
    default_draft = _bool(sec, "default_draft", True, "sharepoint.default_draft", issues)
    allow_publish = _bool(sec, "allow_publish", False, "sharepoint.allow_publish", issues)
    targets = {
        "tenant_id": _opt_str(sec, "tenant_id", "sharepoint.tenant_id", issues),
        "site_id": _opt_str(sec, "site_id", "sharepoint.site_id", issues),
        "page_library_id": _opt_str(sec, "page_library_id", "sharepoint.page_library_id", issues),
    }
    for name, value in targets.items():
        if not value:
            issues.append(f"sharepoint.{name} is required")
    dedicated_site = _bool(sec, "dedicated_site", True, "sharepoint.dedicated_site", issues)
    news_promote = _bool(sec, "news_promote", False, "sharepoint.news_promote", issues)
    idempotency_scope = _opt_str(sec, "idempotency_scope", "sharepoint.idempotency_scope", issues)
    return SharePointConfig(
        mode=mode if isinstance(mode, str) else "",
        default_draft=default_draft,
        allow_publish=allow_publish,
        tenant_id=targets["tenant_id"],
        site_id=targets["site_id"],
        page_library_id=targets["page_library_id"],
        dedicated_site=dedicated_site,
        news_promote=news_promote,
        idempotency_scope=idempotency_scope,
    )


def _validate_security(raw: Mapping[str, Any], issues: list[str]) -> SecurityConfig:
    sec = _section(raw, "security")
    return SecurityConfig(
        block_auto_publish=_bool(
            sec, "block_auto_publish", True, "security.block_auto_publish", issues
        ),
        require_approval=_bool(sec, "require_approval", True, "security.require_approval", issues),
        redact_secrets_in_logs=_bool(
            sec, "redact_secrets_in_logs", True, "security.redact_secrets_in_logs", issues
        ),
    )


def _validate_llm(raw: Mapping[str, Any], issues: list[str]) -> LLMConfig:
    sec = _section(raw, "llm")
    provider = sec.get("provider")
    if provider not in LLM_PROVIDERS:
        issues.append(f"llm.provider must be one of {sorted(LLM_PROVIDERS)}")
    prompt_version = _opt_str(sec, "prompt_version", "llm.prompt_version", issues)
    return LLMConfig(
        provider=provider if isinstance(provider, str) else "",
        prompt_version=prompt_version,
    )


def _validate_publish_consistency(
    sharepoint: SharePointConfig, security: SecurityConfig, issues: list[str]
) -> None:
    if sharepoint.allow_publish and not security.require_approval:
        issues.append("sharepoint.allow_publish=true requires security.require_approval=true")


def _validate_secret_refs(
    raw: Mapping[str, Any], environ: Mapping[str, str], issues: list[str]
) -> None:
    for path, name in iter_secret_refs(raw):
        if not environ.get(name):
            location = ".".join(path)
            issues.append(f"missing required secret env var: {name} (referenced at {location})")
