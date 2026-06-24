"""SPAutoPost CLI / batch entrypoint。

最終運用形ではなく、Azure Container Apps Jobs の command entrypoint を想定する。
起動シーケンス: config load -> validation -> command dispatch。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from collections.abc import Sequence
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from . import __version__
from .advisory_input import AdvisoryInputError, ManualAdvisoryInput, load_manual_advisory
from .config import Config, load_and_validate
from .dry_run import (
    GENERATION_FAILED,
    audit_event_to_dict,
    build_error_audit_event,
    build_preview_audit_event,
    build_site_page_payload,
)
from .errors import ConfigValidationError
from .llm import DraftInput, LLMProviderConfigError, TargetAudience, Urgency, build_llm_provider
from .secrets import redact_config

# dry-run preview の固定方針（draft-composition.md: MVP は mixed / 日本語標準）。
PREVIEW_AUDIENCE: TargetAudience = "mixed"
PREVIEW_LANGUAGE = "ja"
PREVIEW_TEMPLATE_ID = "site-page-v1"
DEFAULT_PROMPT_VERSION = "v1"
DEFAULT_URGENCY: Urgency = "normal"

DEFAULT_CONFIG_DIR = Path("config")
DEFAULT_ENV = "development"

EXIT_OK = 0
EXIT_RUNTIME_ERROR = 1
EXIT_CONFIG_INVALID = 2
EXIT_INPUT_INVALID = 3


def build_parser() -> argparse.ArgumentParser:
    """CLI パーサを構築する。"""
    parser = argparse.ArgumentParser(
        prog="spautopost",
        description="SharePoint security-advisory auto-posting tool (MVP core)",
    )
    parser.add_argument("--version", action="version", version=f"spautopost {__version__}")
    parser.add_argument(
        "--env",
        default=os.environ.get("SPAUTOPOST_ENV", DEFAULT_ENV),
        help="設定環境 (development/test/production)",
    )
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=DEFAULT_CONFIG_DIR,
        help="config ディレクトリ (default: ./config)",
    )
    dry = parser.add_mutually_exclusive_group()
    dry.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        default=None,
        help="dry-run を強制有効化（外部投稿しない）",
    )
    dry.add_argument(
        "--no-dry-run",
        dest="dry_run",
        action="store_false",
        help="dry-run を無効化（publish は人間ゲート対象）",
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("validate-config", help="config を検証して結果を表示する")
    sub.add_parser("show-config", help="検証済み config を Secret 秘匿付きで表示する")
    sub.add_parser(
        "migrate",
        help="アクティブ provider の baseline migration を適用する（--dry-run で未適用一覧のみ）",
    )
    import_advisory = sub.add_parser(
        "import-advisory",
        help="YAML / JSON の手動 advisory を検証し normalized preview を表示する",
    )
    import_advisory.add_argument("input_file", type=Path, help="manual advisory YAML / JSON file")
    preview_draft = sub.add_parser(
        "preview-draft",
        help="手動 advisory から原稿を生成し、投稿予定 payload と監査イベントを dry-run 表示する",
    )
    preview_draft.add_argument("input_file", type=Path, help="manual advisory YAML / JSON file")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """エントリポイント。終了コードを返す。"""
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return EXIT_OK
    try:
        config = load_and_validate(args.env, args.config_dir, os.environ)
    except ConfigValidationError as exc:
        print("config validation failed:", file=sys.stderr)
        for issue in exc.issues:
            print(f"  - {issue}", file=sys.stderr)
        return EXIT_CONFIG_INVALID
    except FileNotFoundError as exc:
        print(f"config not found: {exc}", file=sys.stderr)
        return EXIT_RUNTIME_ERROR
    effective_dry_run = config.app.dry_run if args.dry_run is None else args.dry_run
    return _dispatch(args, config, effective_dry_run)


def _dispatch(args: argparse.Namespace, config: Config, dry_run: bool) -> int:
    command = args.command
    if command == "validate-config":
        print(f"OK: config valid (environment={config.app.environment}, dry_run={dry_run})")
        return EXIT_OK
    if command == "show-config":
        dumped = yaml.safe_dump(
            redact_config(dict(config.raw)), allow_unicode=True, sort_keys=False
        )
        print(dumped, end="")
        return EXIT_OK
    if command == "migrate":
        return _run_migrate(config, dry_run)
    if command == "import-advisory":
        return _run_import_advisory(args.input_file, dry_run)
    if command == "preview-draft":
        return _run_preview_draft(args.input_file, config)
    print(f"unknown command: {command}", file=sys.stderr)  # pragma: no cover
    return EXIT_RUNTIME_ERROR  # pragma: no cover


def _run_import_advisory(input_file: Path, dry_run: bool) -> int:
    try:
        loaded = load_manual_advisory(input_file)
    except FileNotFoundError:
        print(f"advisory input not found: {input_file}", file=sys.stderr)
        return EXIT_RUNTIME_ERROR
    except OSError as exc:
        print(f"advisory input read failed: {exc}", file=sys.stderr)
        return EXIT_RUNTIME_ERROR
    except AdvisoryInputError as exc:
        print("advisory input validation failed:", file=sys.stderr)
        for issue in exc.issues:
            print(f"  - {issue}", file=sys.stderr)
        return EXIT_INPUT_INVALID

    print(json.dumps(_manual_advisory_preview(loaded, dry_run), ensure_ascii=False, indent=2))
    return EXIT_OK


def _manual_advisory_preview(loaded: ManualAdvisoryInput, dry_run: bool) -> dict[str, Any]:
    advisory = _json_ready(asdict(loaded.advisory))
    preview: dict[str, Any] = {"dry_run": dry_run, "advisory": advisory}
    if loaded.urgency is not None:
        preview["urgency"] = loaded.urgency
    return preview


def _json_ready(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    return value


def _run_preview_draft(input_file: Path, config: Config) -> int:
    """手動 advisory から原稿を生成し、投稿予定 payload と監査イベントを dry-run 表示する。

    実投稿・外部 API 呼び出し・Secret 解決・永続化は行わない。投稿先識別子は ``env:``
    参照のまま扱い、出力直前に redaction する。
    """
    try:
        loaded = load_manual_advisory(input_file)
    except FileNotFoundError:
        print(f"advisory input not found: {input_file}", file=sys.stderr)
        return EXIT_RUNTIME_ERROR
    except OSError as exc:
        print(f"advisory input read failed: {exc}", file=sys.stderr)
        return EXIT_RUNTIME_ERROR
    except AdvisoryInputError as exc:
        print("advisory input validation failed:", file=sys.stderr)
        for issue in exc.issues:
            print(f"  - {issue}", file=sys.stderr)
        return EXIT_INPUT_INVALID

    try:
        provider = build_llm_provider(config.llm)
    except LLMProviderConfigError as exc:
        print(f"llm provider unavailable: {exc}", file=sys.stderr)
        return EXIT_CONFIG_INVALID

    metadata = provider.get_provider_metadata()
    advisory = loaded.advisory
    urgency = loaded.urgency or DEFAULT_URGENCY
    correlation_id = uuid.uuid4().hex
    now = datetime.now(UTC)

    draft_input = DraftInput(
        advisory=_json_ready(asdict(advisory)),
        target_audience=PREVIEW_AUDIENCE,
        target_language=PREVIEW_LANGUAGE,
        urgency=urgency,
        template_id=PREVIEW_TEMPLATE_ID,
        prompt_version=config.llm.prompt_version or DEFAULT_PROMPT_VERSION,
        references=[dict(ref) for ref in advisory.references],
    )

    try:
        draft = provider.generate_draft(draft_input)
    except Exception as exc:  # noqa: BLE001 - 失敗は error 監査イベントとして追跡する
        error_event = build_error_audit_event(
            correlation_id=correlation_id,
            audit_event_id=uuid.uuid4().hex,
            now=now,
            error_code=GENERATION_FAILED,
            error_message=str(exc),
            provider=metadata,
        )
        _print_preview({"dry_run": True, "audit_event": audit_event_to_dict(error_event)})
        return EXIT_RUNTIME_ERROR

    payload = build_site_page_payload(
        draft,
        urgency=urgency,
        target_site_id=config.sharepoint.site_id,
        target_page_library_id=config.sharepoint.page_library_id,
        mode=config.sharepoint.mode,
    )
    audit_event = build_preview_audit_event(
        provider=metadata,
        draft=draft,
        correlation_id=correlation_id,
        audit_event_id=uuid.uuid4().hex,
        now=now,
        advisory_id=advisory.advisory_id,
        target_site_id=config.sharepoint.site_id,
        target_page_library_id=config.sharepoint.page_library_id,
    )
    _print_preview(
        {
            "dry_run": True,
            "payload": payload,
            "audit_event": audit_event_to_dict(audit_event),
        }
    )
    return EXIT_OK


def _print_preview(preview: dict[str, Any]) -> None:
    """preview を Secret / ``env:`` 参照を redaction して JSON 出力する。"""
    redacted = redact_config(preview)
    print(json.dumps(redacted, ensure_ascii=False, indent=2))


def _run_migrate(config: Config, dry_run: bool) -> int:
    """アクティブ provider の migration を適用する（dry-run は未適用一覧のみ）。

    Secret 値（database_url の認証情報）は出力しない。provider 名のみ表示する。
    """
    from .storage.errors import StorageError
    from .storage.factory import build_storage

    try:
        storage = build_storage(config.storage)
    except StorageError as exc:
        print(f"storage init failed: {exc}", file=sys.stderr)
        return EXIT_RUNTIME_ERROR
    try:
        provider = config.storage.provider
        if dry_run:
            pending = storage.pending_migrations()
            if pending:
                print(f"pending migrations ({provider}): {', '.join(pending)}")
            else:
                print(f"no pending migrations ({provider})")
            return EXIT_OK
        applied = _apply_migrations(storage)
        if applied:
            print(f"applied migrations ({provider}): {', '.join(applied)}")
        else:
            print(f"no pending migrations ({provider})")
        return EXIT_OK
    except StorageError as exc:
        print(f"migration failed: {exc}", file=sys.stderr)
        return EXIT_RUNTIME_ERROR
    finally:
        storage.close()


def _apply_migrations(storage: object) -> list[str]:
    """pending を確認してから migrate を適用し、適用した version を返す。"""
    pending = storage.pending_migrations()  # type: ignore[attr-defined]
    storage.migrate()  # type: ignore[attr-defined]
    return list(pending)
