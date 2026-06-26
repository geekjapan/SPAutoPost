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
SHAREPOINT_MODES = frozenset({"site-page"})
IDEMPOTENCY_SCOPES = frozenset({"site-and-page-library"})

_SECTION_KEYS: dict[str, frozenset[str]] = {
    "app": frozenset({"environment", "dry_run", "log_level"}),
    "server": frozenset({"admin_ui_enabled", "admin_api_enabled", "auth_provider"}),
    "storage": frozenset({"provider", "database_url", "sqlite_path"}),
    "llm": frozenset(
        {
            "provider",
            "prompt_version",
            "azure",
            "endpoint_url",
            "model",
            "auth_env_var",
            "timeout_seconds",
            "max_retries",
            "provider_name",
            "production_approved",
        }
    ),
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
    "graph": frozenset({"local_poc_auth", "hosted_auth", "client_id", "scopes"}),
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


_AZURE_AUTH_TYPES = frozenset({"api_key", "managed_identity"})
_AZURE_DEFAULT_API_VERSION = "2024-02-01"
_AZURE_DEFAULT_TIMEOUT_SECS = 60
_AZURE_DEFAULT_MAX_RETRIES = 3


@dataclass(frozen=True)
class AzureOpenAIConfig:
    """Azure OpenAI / Foundry provider の設定。"""

    endpoint: str
    deployment: str
    api_version: str
    auth_type: str
    api_key_ref: str | None
    timeout_secs: int
    max_retries: int
    production_approved: bool


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    prompt_version: str | None
    endpoint_url: str | None = None
    model: str | None = None
    auth_env_var: str | None = None
    timeout_seconds: int = 30
    max_retries: int = 3
    provider_name: str | None = None
    production_approved: bool = False
    azure: AzureOpenAIConfig | None = None


@dataclass(frozen=True)
class GraphConfig:
    """Microsoft Graph 認証設定（local PoC delegated 経路）。

    ``client_id`` は public client の application id で機密ではない（env 参照も可）。
    ``scopes`` 未指定時は空 tuple とし、auth provider 側で既定 scope を適用する。
    """

    local_poc_auth: str
    hosted_auth: str
    client_id: str | None
    scopes: tuple[str, ...]


@dataclass(frozen=True)
class Config:
    app: AppConfig
    storage: StorageConfig
    sharepoint: SharePointConfig
    security: SecurityConfig
    llm: LLMConfig
    graph: GraphConfig
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
    graph = _validate_graph(raw, issues)
    _validate_publish_consistency(sharepoint, security, issues)
    _validate_secret_refs(raw, environ, issues)
    if issues:
        raise ConfigValidationError(issues)
    return Config(
        app=app,
        storage=storage,
        sharepoint=sharepoint,
        security=security,
        llm=llm,
        graph=graph,
        raw=raw,
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


def _int(sec: Mapping[str, Any], key: str, default: int, path: str, issues: list[str]) -> int:
    if key not in sec:
        return default
    value = sec[key]
    if not isinstance(value, int) or isinstance(value, bool):
        issues.append(f"{path} must be an integer")
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
    if not dedicated_site:
        issues.append("sharepoint.dedicated_site must be true (M1 requires dedicated site only)")
    news_promote = _bool(sec, "news_promote", False, "sharepoint.news_promote", issues)
    if news_promote:
        issues.append("sharepoint.news_promote must be false (M1 does not implement News promote)")
    idempotency_scope = _opt_str(sec, "idempotency_scope", "sharepoint.idempotency_scope", issues)
    if not idempotency_scope:
        issues.append("sharepoint.idempotency_scope is required")
    elif idempotency_scope not in IDEMPOTENCY_SCOPES:
        issues.append(f"sharepoint.idempotency_scope must be one of {sorted(IDEMPOTENCY_SCOPES)}")
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
    endpoint_url = _opt_str(sec, "endpoint_url", "llm.endpoint_url", issues)
    model = _opt_str(sec, "model", "llm.model", issues)
    auth_env_var = _opt_str(sec, "auth_env_var", "llm.auth_env_var", issues)
    provider_name = _opt_str(sec, "provider_name", "llm.provider_name", issues)
    timeout_seconds = _int(sec, "timeout_seconds", 30, "llm.timeout_seconds", issues)
    if timeout_seconds <= 0:
        issues.append("llm.timeout_seconds must be a positive integer")
    max_retries = _int(sec, "max_retries", 3, "llm.max_retries", issues)
    if max_retries < 0:
        issues.append("llm.max_retries must be 0 or greater")
    production_approved = _bool(
        sec, "production_approved", False, "llm.production_approved", issues
    )
    azure = _validate_azure_llm(sec, str(provider) if isinstance(provider, str) else "", issues)
    # 本番系 provider は情報セキュリティ部門の承認を必須とする。承認はフラットな
    # llm.production_approved、または production_api では llm.azure.production_approved の
    # いずれかで満たせる（azure provider は build 時に承認を独立して再強制する）。
    azure_approved = azure is not None and azure.production_approved
    production_providers = frozenset({"production_api", "production_flow", "generic_api"})
    if provider in production_providers and not (production_approved or azure_approved):
        issues.append(
            f"llm.production_approved must be true to use provider={provider!r}; "
            "obtain information-security department approval first "
            "(see docs/specs/llm-provider.md)"
        )
    return LLMConfig(
        provider=provider if isinstance(provider, str) else "",
        prompt_version=prompt_version,
        endpoint_url=endpoint_url,
        model=model,
        auth_env_var=auth_env_var,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        provider_name=provider_name,
        production_approved=production_approved,
        azure=azure,
    )


def _validate_azure_llm(
    llm_sec: Mapping[str, Any], provider: str, issues: list[str]
) -> AzureOpenAIConfig | None:
    azure_raw = llm_sec.get("azure")
    if provider == "production_api":
        if azure_raw is None:
            issues.append("llm.azure is required when llm.provider is 'production_api'")
            return None
        if not isinstance(azure_raw, Mapping):
            issues.append("llm.azure must be a mapping")
            return None
    else:
        if not isinstance(azure_raw, Mapping):
            return None
    sec = dict(azure_raw)
    endpoint = _opt_str(sec, "endpoint", "llm.azure.endpoint", issues) or ""
    deployment = _opt_str(sec, "deployment", "llm.azure.deployment", issues) or ""
    if provider == "production_api":
        if not endpoint:
            issues.append("llm.azure.endpoint is required when llm.provider is 'production_api'")
        if not deployment:
            issues.append("llm.azure.deployment is required when llm.provider is 'production_api'")
    api_version = (
        _opt_str(sec, "api_version", "llm.azure.api_version", issues) or _AZURE_DEFAULT_API_VERSION
    )
    auth_type = _opt_str(sec, "auth_type", "llm.azure.auth_type", issues) or "api_key"
    if auth_type not in _AZURE_AUTH_TYPES:
        issues.append(f"llm.azure.auth_type must be one of {sorted(_AZURE_AUTH_TYPES)}")
        auth_type = "api_key"
    api_key_ref = _opt_str(sec, "api_key", "llm.azure.api_key", issues)
    if provider == "production_api" and auth_type == "api_key":
        if not api_key_ref:
            issues.append(
                "llm.azure.api_key is required when llm.provider is 'production_api'"
                " and auth_type is 'api_key'"
            )
        elif not api_key_ref.startswith("env:"):
            issues.append(
                "llm.azure.api_key must be an env: reference (e.g. env:AZURE_OPENAI_API_KEY);"
                " plaintext secrets are not allowed"
            )
    timeout_secs_raw = sec.get("timeout_secs", _AZURE_DEFAULT_TIMEOUT_SECS)
    timeout_secs = _AZURE_DEFAULT_TIMEOUT_SECS
    if isinstance(timeout_secs_raw, int):
        timeout_secs = timeout_secs_raw
    elif timeout_secs_raw is not None:
        issues.append("llm.azure.timeout_secs must be an integer")
    max_retries_raw = sec.get("max_retries", _AZURE_DEFAULT_MAX_RETRIES)
    max_retries = _AZURE_DEFAULT_MAX_RETRIES
    if isinstance(max_retries_raw, int):
        if max_retries_raw < 0:
            issues.append("llm.azure.max_retries must be >= 0")
        else:
            max_retries = max_retries_raw
    elif max_retries_raw is not None:
        issues.append("llm.azure.max_retries must be an integer")
    production_approved = _bool(
        sec, "production_approved", False, "llm.azure.production_approved", issues
    )
    return AzureOpenAIConfig(
        endpoint=endpoint,
        deployment=deployment,
        api_version=api_version,
        auth_type=auth_type,
        api_key_ref=api_key_ref,
        timeout_secs=timeout_secs,
        max_retries=max_retries,
        production_approved=production_approved,
    )


def _validate_graph(raw: Mapping[str, Any], issues: list[str]) -> GraphConfig:
    sec = _section(raw, "graph")
    local_poc_auth = _opt_str(sec, "local_poc_auth", "graph.local_poc_auth", issues) or "delegated"
    hosted_auth = _opt_str(sec, "hosted_auth", "graph.hosted_auth", issues) or "undecided"
    client_id = _opt_str(sec, "client_id", "graph.client_id", issues)
    scopes = _validate_scopes(sec, issues)
    return GraphConfig(
        local_poc_auth=local_poc_auth,
        hosted_auth=hosted_auth,
        client_id=client_id,
        scopes=scopes,
    )


def _validate_scopes(sec: Mapping[str, Any], issues: list[str]) -> tuple[str, ...]:
    value = sec.get("scopes")
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        issues.append("graph.scopes must be a list of strings")
        return ()
    return tuple(value)


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
