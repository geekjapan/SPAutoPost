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


def _write_sqlite_config(config_dir: Path, sqlite_path: Path) -> None:
    """既存 default.yml の sqlite_path を tmp の書込可能パスへ差し替える。"""
    text = (config_dir / "default.yml").read_text(encoding="utf-8")
    text = text.replace("./data/spautopost.dev.sqlite3", str(sqlite_path))
    (config_dir / "default.yml").write_text(text, encoding="utf-8")


def test_migrate_dry_run_lists_pending(
    config_dir: Path,
    valid_environ: dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _set_env(monkeypatch, valid_environ)
    _write_sqlite_config(config_dir, tmp_path / "cli.sqlite3")

    code = main(["--config-dir", str(config_dir), "--dry-run", "migrate"])

    out = capsys.readouterr().out
    assert code == 0
    assert "pending migrations (sqlite)" in out
    assert "0001_baseline" in out


def test_migrate_applies_then_reports_no_pending(
    config_dir: Path,
    valid_environ: dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _set_env(monkeypatch, valid_environ)
    _write_sqlite_config(config_dir, tmp_path / "cli.sqlite3")

    code = main(["--config-dir", str(config_dir), "--no-dry-run", "migrate"])
    out = capsys.readouterr().out
    assert code == 0
    assert "applied migrations (sqlite): 0001_baseline" in out

    # 2 回目は再適用されず、未適用も無い（冪等）。
    code2 = main(["--config-dir", str(config_dir), "--no-dry-run", "migrate"])
    out2 = capsys.readouterr().out
    assert code2 == 0
    assert "no pending migrations (sqlite)" in out2


def test_import_advisory_dry_run_preview(
    config_dir: Path,
    valid_environ: dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _set_env(monkeypatch, valid_environ)
    input_file = tmp_path / "advisory.yaml"
    input_file.write_text(
        """
title: Test advisory
summary: Test summary.
severity: medium
urgency: normal
references:
  - label: Vendor
    url: https://example.com/advisory
    type: vendor
""",
        encoding="utf-8",
    )

    code = main(["--config-dir", str(config_dir), "--dry-run", "import-advisory", str(input_file)])

    out = capsys.readouterr().out
    assert code == 0
    assert '"dry_run": true' in out
    assert '"title": "Test advisory"' in out
    assert '"urgency": "normal"' in out


def test_import_advisory_invalid_input_returns_three(
    config_dir: Path,
    valid_environ: dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _set_env(monkeypatch, valid_environ)
    input_file = tmp_path / "invalid.yaml"
    input_file.write_text("title: only title\n", encoding="utf-8")

    code = main(["--config-dir", str(config_dir), "--dry-run", "import-advisory", str(input_file)])

    assert code == 3
    err = capsys.readouterr().err
    assert "advisory input validation failed" in err
    assert "summary is required" in err
    assert "references is required" in err


def test_import_advisory_read_error_returns_one(
    config_dir: Path,
    valid_environ: dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _set_env(monkeypatch, valid_environ)

    code = main(["--config-dir", str(config_dir), "--dry-run", "import-advisory", str(tmp_path)])

    assert code == 1
    err = capsys.readouterr().err
    assert "advisory input read failed" in err
