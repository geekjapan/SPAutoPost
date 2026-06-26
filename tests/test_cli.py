"""CLI の単体テスト。"""

from __future__ import annotations

import json
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


def test_run_sample_source_job_generates_draft(
    config_dir: Path,
    valid_environ: dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _set_env(monkeypatch, valid_environ)
    _write_sqlite_config(config_dir, tmp_path / "sample-job.sqlite3")

    code = main(["--config-dir", str(config_dir), "run-sample-source-job"])

    preview = json.loads(capsys.readouterr().out)
    assert code == 0
    assert preview["generated_count"] == 1
    assert preview["draft_ids"] == ["draft-sample-advisory-sample-2026-0001"]
    assert preview["source_record_ids"][0].startswith("sample-src-")


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


def _write_advisory(path: Path) -> None:
    path.write_text(
        """
title: Example の脆弱性
summary: 権限昇格の可能性があります。
severity: high
urgency: high
references:
  - label: Vendor
    url: https://example.com/advisory
    type: vendor
""",
        encoding="utf-8",
    )


def test_preview_draft_shows_payload_and_audit_event(
    config_dir: Path,
    valid_environ: dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _set_env(monkeypatch, valid_environ)
    input_file = tmp_path / "advisory.yaml"
    _write_advisory(input_file)

    code = main(["--config-dir", str(config_dir), "preview-draft", str(input_file)])

    out = capsys.readouterr().out
    assert code == 0
    assert '"dry_run": true' in out
    # 投稿予定 payload（Site Page 必須セクション）と監査イベントの両方が出る
    assert '"payload"' in out
    assert "概要" in out
    assert "参考情報" in out
    assert '"event_type": "publish_dry_run"' in out
    assert '"provider_name": "test_mock"' in out
    assert '"prompt_version": "v1"' in out
    assert '"operation": "dry-run"' in out
    assert "generation_input_hash" in out


def test_preview_draft_always_uses_mock_provider(
    config_dir: Path,
    valid_environ: dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _set_env(monkeypatch, valid_environ)
    default_config = config_dir / "default.yml"
    default_config.write_text(
        default_config.read_text(encoding="utf-8").replace(
            "provider: test_mock", "provider: production_api"
        ),
        encoding="utf-8",
    )
    input_file = tmp_path / "advisory.yaml"
    _write_advisory(input_file)

    code = main(["--config-dir", str(config_dir), "preview-draft", str(input_file)])

    out = capsys.readouterr().out
    assert code == 0
    assert '"provider_name": "test_mock"' in out


def test_preview_draft_defaults_prompt_version(
    config_dir: Path,
    valid_environ: dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _set_env(monkeypatch, valid_environ)
    default_config = config_dir / "default.yml"
    default_config.write_text(
        default_config.read_text(encoding="utf-8").replace("  prompt_version: v1\n", ""),
        encoding="utf-8",
    )
    input_file = tmp_path / "advisory.yaml"
    _write_advisory(input_file)

    code = main(["--config-dir", str(config_dir), "preview-draft", str(input_file)])

    out = capsys.readouterr().out
    assert code == 0
    assert '"prompt_version": "v1"' in out


def test_preview_draft_redacts_secret_targets(
    config_dir: Path,
    valid_environ: dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _set_env(monkeypatch, valid_environ)
    input_file = tmp_path / "advisory.yaml"
    _write_advisory(input_file)

    code = main(["--config-dir", str(config_dir), "preview-draft", str(input_file)])

    out = capsys.readouterr().out
    assert code == 0
    # env: 参照も解決済み Secret 値も出ない
    assert "***" in out
    assert "env:SPAUTOPOST_SHAREPOINT_SITE_ID" not in out
    assert "site-xyz" not in out
    assert "lib-xyz" not in out


def test_preview_draft_invalid_input_returns_three(
    config_dir: Path,
    valid_environ: dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _set_env(monkeypatch, valid_environ)
    input_file = tmp_path / "invalid.yaml"
    input_file.write_text("title: only title\n", encoding="utf-8")

    code = main(["--config-dir", str(config_dir), "preview-draft", str(input_file)])

    assert code == 3
    assert "advisory input validation failed" in capsys.readouterr().err


def test_publish_draft_dry_run_records_publication_and_audit(
    config_dir: Path,
    valid_environ: dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _set_env(monkeypatch, valid_environ)
    _write_sqlite_config(config_dir, tmp_path / "publish.sqlite3")
    input_file = tmp_path / "advisory.yaml"
    _write_advisory(input_file)

    # 既定は dry-run（--no-dry-run なし）→ 外部投稿せず Publication / AuditEvent を記録。
    code = main(["--config-dir", str(config_dir), "publish-draft", str(input_file)])

    out = capsys.readouterr().out
    assert code == 0
    preview = json.loads(out)
    assert preview["dry_run"] is True
    assert preview["publication"]["publication_status"] == "dry_run"
    assert preview["publication"]["operation"] == "dry-run"
    assert preview["audit_events"][0]["event_type"] == "publish_dry_run"
    # env: 参照は出力境界で redaction される。
    assert "env:SPAUTOPOST_SHAREPOINT_SITE_ID" not in out
    assert "site-xyz" not in out
