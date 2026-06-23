"""CLI の単体テスト。"""

from __future__ import annotations

from pathlib import Path

import pytest

from spautopost.cli import main


def _set_env(monkeypatch: pytest.MonkeyPatch, environ: dict[str, str]) -> None:
    for key, value in environ.items():
        monkeypatch.setenv(key, value)


def test_help_returns_zero(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["--help"])
    assert excinfo.value.code == 0
    assert "spautopost" in capsys.readouterr().out


def test_no_command_prints_help_and_returns_zero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main([]) == 0
    assert "usage" in capsys.readouterr().out.lower()


def test_validate_config_ok(
    config_dir: Path,
    valid_environ: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _set_env(monkeypatch, valid_environ)

    code = main(["--env", "development", "--config-dir", str(config_dir), "validate-config"])

    assert code == 0
    assert "OK: config valid" in capsys.readouterr().out


def test_validate_config_invalid_returns_two(
    config_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # 必須 Secret env vars を設定しない -> validation error
    monkeypatch.delenv("SPAUTOPOST_TENANT_ID", raising=False)

    code = main(["--config-dir", str(config_dir), "validate-config"])

    assert code == 2
    err = capsys.readouterr().err
    assert "config validation failed" in err
    assert "missing required secret env var" in err


def test_missing_config_dir_returns_one(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["--config-dir", str(tmp_path / "absent"), "validate-config"])

    assert code == 1
    assert "config not found" in capsys.readouterr().err


def test_show_config_redacts_secrets(
    config_dir: Path,
    valid_environ: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _set_env(monkeypatch, valid_environ)

    code = main(["--config-dir", str(config_dir), "show-config"])

    out = capsys.readouterr().out
    assert code == 0
    assert "***" in out
    assert "env:SPAUTOPOST_TENANT_ID" not in out
    # 実 Secret 値も漏れない
    assert "tenant-xyz" not in out
