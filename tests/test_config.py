"""config モジュールの単体テスト。"""

from __future__ import annotations

from pathlib import Path

import pytest

from spautopost.config import load_and_validate, validate_config
from spautopost.errors import ConfigValidationError


def _base_config() -> dict[str, object]:
    return {
        "app": {"environment": "development", "dry_run": True},
        "storage": {"provider": "sqlite", "sqlite_path": "./x.sqlite3"},
        "llm": {"provider": "test_mock"},
        "sharepoint": {
            "mode": "site-page",
            "allow_publish": False,
            "tenant_id": "env:T",
            "site_id": "env:S",
            "page_library_id": "env:L",
            "dedicated_site": True,
            "news_promote": False,
            "idempotency_scope": "site-and-page-library",
        },
        "security": {"require_approval": True},
    }


def _environ() -> dict[str, str]:
    return {"T": "t", "S": "s", "L": "l"}


def test_load_and_validate_reads_and_merges_environment(
    config_dir: Path, valid_environ: dict[str, str]
) -> None:
    (config_dir / "test.yml").write_text(
        "app:\n  environment: test\n  dry_run: false\n", encoding="utf-8"
    )

    config = load_and_validate("test", config_dir, valid_environ)

    assert config.app.environment == "test"
    assert config.app.dry_run is False
    assert config.storage.provider == "sqlite"
    assert config.llm.provider == "test_mock"


def test_dry_run_defaults_to_true_when_absent() -> None:
    raw = _base_config()
    raw["app"] = {"environment": "development"}

    config = validate_config(raw, _environ())

    assert config.app.dry_run is True


def test_missing_secret_raises_with_name_not_value() -> None:
    raw = _base_config()

    with pytest.raises(ConfigValidationError) as excinfo:
        validate_config(raw, {})  # 環境変数が無い

    joined = "\n".join(excinfo.value.issues)
    assert "missing required secret env var: T" in joined
    assert "sharepoint.tenant_id" in joined


def test_unknown_key_is_rejected() -> None:
    raw = _base_config()
    raw["unexpected"] = 1

    with pytest.raises(ConfigValidationError) as excinfo:
        validate_config(raw, _environ())

    assert any("unknown config key: unexpected" in i for i in excinfo.value.issues)


def test_unknown_nested_key_is_rejected() -> None:
    raw = _base_config()
    raw["app"]["typo"] = 1  # type: ignore[index]

    with pytest.raises(ConfigValidationError) as excinfo:
        validate_config(raw, _environ())

    assert any("unknown config key: app.typo" in i for i in excinfo.value.issues)


def test_postgresql_requires_database_url() -> None:
    raw = _base_config()
    raw["storage"] = {"provider": "postgresql"}

    with pytest.raises(ConfigValidationError) as excinfo:
        validate_config(raw, _environ())

    assert any("storage.database_url is required" in i for i in excinfo.value.issues)


def test_unknown_provider_is_rejected() -> None:
    raw = _base_config()
    raw["llm"] = {"provider": "nope"}

    with pytest.raises(ConfigValidationError) as excinfo:
        validate_config(raw, _environ())

    assert any("llm.provider must be one of" in i for i in excinfo.value.issues)


@pytest.mark.parametrize("provider", ["test_mock", "test_manual"])
def test_llm_provider_types_are_supported_without_gate(provider: str) -> None:
    raw = _base_config()
    raw["llm"] = {"provider": provider}

    config = validate_config(raw, _environ())

    assert config.llm.provider == provider


@pytest.mark.parametrize("provider", ["production_api", "production_flow", "generic_api"])
def test_production_providers_require_production_approved(provider: str) -> None:
    raw = _base_config()
    raw["llm"] = {"provider": provider}

    with pytest.raises(ConfigValidationError) as excinfo:
        validate_config(raw, _environ())

    assert any("production_approved" in i for i in excinfo.value.issues)


@pytest.mark.parametrize("provider", ["production_api", "production_flow", "generic_api"])
def test_production_providers_accepted_when_production_approved_true(provider: str) -> None:
    raw = _base_config()
    raw["llm"] = {"provider": provider, "production_approved": True}
    if provider == "generic_api":
        raw["llm"].update(  # type: ignore[union-attr]
            {
                "endpoint_url": "https://api.example.test/v1/chat/completions",
                "model": "gpt-4o",
                "auth_env_var": "LLM_API_KEY",
            }
        )

    config = validate_config(raw, _environ())

    assert config.llm.provider == provider
    assert config.llm.production_approved is True


def test_allow_publish_requires_approval() -> None:
    raw = _base_config()
    raw["sharepoint"]["allow_publish"] = True  # type: ignore[index]
    raw["security"] = {"require_approval": False}

    with pytest.raises(ConfigValidationError) as excinfo:
        validate_config(raw, _environ())

    assert any("require_approval" in i for i in excinfo.value.issues)


def test_missing_target_ids_are_reported() -> None:
    raw = _base_config()
    raw["sharepoint"] = {"mode": "site-page", "allow_publish": False}

    with pytest.raises(ConfigValidationError) as excinfo:
        validate_config(raw, _environ())

    issues = "\n".join(excinfo.value.issues)
    assert "sharepoint.tenant_id is required" in issues
    assert "sharepoint.site_id is required" in issues
