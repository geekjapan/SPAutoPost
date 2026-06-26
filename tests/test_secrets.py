"""secrets モジュールの単体テスト。"""

from __future__ import annotations

from spautopost.secrets import (
    REDACTED,
    is_secret_ref,
    iter_secret_refs,
    redact_config,
    secret_env_name,
)


def test_is_secret_ref_detects_env_prefix() -> None:
    assert is_secret_ref("env:SPAUTOPOST_TOKEN") is True
    assert is_secret_ref("plain-value") is False
    assert is_secret_ref(123) is False


def test_secret_env_name_strips_prefix() -> None:
    assert secret_env_name("env:SPAUTOPOST_TOKEN") == "SPAUTOPOST_TOKEN"


def test_iter_secret_refs_finds_nested_refs() -> None:
    data = {
        "storage": {"database_url": "env:DB_URL"},
        "sources": [{"api_key": "env:NVD_KEY"}],
        "plain": "value",
    }

    refs = dict(iter_secret_refs(data))

    assert refs[("storage", "database_url")] == "DB_URL"
    assert refs[("sources", "0", "api_key")] == "NVD_KEY"
    assert all(name in {"DB_URL", "NVD_KEY"} for name in refs.values())


def test_redact_config_replaces_secret_refs() -> None:
    data = {"storage": {"database_url": "env:DB_URL", "sqlite_path": "./x.sqlite3"}}

    redacted = redact_config(data)

    assert redacted["storage"]["database_url"] == REDACTED
    assert redacted["storage"]["sqlite_path"] == "./x.sqlite3"
    # 入力は変更されない（immutability）
    assert data["storage"]["database_url"] == "env:DB_URL"
