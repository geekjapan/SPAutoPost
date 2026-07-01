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
from .llm import DraftInput, MockLLMProvider, TargetAudience, Urgency
from .secrets import is_secret_ref, redact_config, secret_env_name

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
    publish_draft = sub.add_parser(
        "publish-draft",
        help=(
            "手動 advisory から原稿を生成し SharePoint Site Page へ投稿する"
            "（既定 dry-run。--no-dry-run で delegated 実投稿）"
        ),
    )
    publish_draft.add_argument("input_file", type=Path, help="manual advisory YAML / JSON file")
    publish_draft.add_argument(
        "--promote",
        action="store_true",
        help="作成した Site Page を News として publish する（live のみ）",
    )
    sub.add_parser(
        "run-sample-source-job",
        help="sample source から Advisory と DraftPost を生成して保存する",
    )
    sub.add_parser(
        "publish-approved",
        help="pending な publish_request AdminCommand を処理し、approved DraftPost を投稿する",
    )
    import_external = sub.add_parser(
        "import-external",
        help="外部 collector が生成した JSON/YAML ファイルから normalized advisory を import する",
    )
    import_external.add_argument(
        "input_file", type=Path, help="外部 collector の import ファイル（JSON または YAML）"
    )
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
    if command == "publish-draft":
        return _run_publish_draft(args.input_file, config, dry_run, promote=args.promote)
    if command == "run-sample-source-job":
        return _run_sample_source_job(config, dry_run)
    if command == "publish-approved":
        return _run_publish_approved(config, dry_run)
    if command == "import-external":
        return _run_import_external(args.input_file, config, dry_run)
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

    provider = MockLLMProvider(prompt_version=config.llm.prompt_version or DEFAULT_PROMPT_VERSION)
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


def _resolve_ref(value: str | None, environ: dict[str, str]) -> str | None:
    """``env:NAME`` 参照を実環境変数へ解決する（live 投稿で実 ID が必要なため）。"""
    if value is None:
        return None
    if is_secret_ref(value):
        return environ.get(secret_env_name(value))
    return value


def _run_publish_draft(input_file: Path, config: Config, dry_run: bool, *, promote: bool) -> int:
    """手動 advisory から原稿を生成し SharePoint Site Page へ投稿する。

    既定は dry-run（実認証・実投稿なし）。``--no-dry-run`` のときだけ delegated device code
    認証で実投稿する。投稿結果は ``Publication``、経過は ``AuditEvent`` として永続化する。
    """
    from .dry_run import audit_event_to_dict, build_site_page_payload
    from .graph import (
        DelegatedDeviceCodeAuth,
        GraphSharePointPagesClient,
        publish_site_page,
    )
    from .graph.auth import GraphTokenProvider
    from .graph.errors import GraphAuthError
    from .graph.sharepoint_client import SharePointPagesClient
    from .storage.errors import StorageError
    from .storage.factory import build_storage
    from .storage.models import DraftPost

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

    provider = MockLLMProvider(prompt_version=config.llm.prompt_version or DEFAULT_PROMPT_VERSION)
    metadata = provider.get_provider_metadata()
    advisory = loaded.advisory
    urgency = loaded.urgency or DEFAULT_URGENCY
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
    except Exception as exc:  # noqa: BLE001 - 生成失敗は投稿前なので runtime error として返す
        print(f"draft generation failed: {exc}", file=sys.stderr)
        return EXIT_RUNTIME_ERROR

    # live 投稿は実 ID が必要。dry-run は env 参照のまま扱い、出力境界で redaction する。
    if dry_run:
        target_site_id = config.sharepoint.site_id
        target_page_library_id = config.sharepoint.page_library_id
        token_provider: GraphTokenProvider | None = None
        client: SharePointPagesClient | None = None
        client_id = config.graph.client_id
    else:
        target_site_id = _resolve_ref(config.sharepoint.site_id, dict(os.environ))
        target_page_library_id = _resolve_ref(config.sharepoint.page_library_id, dict(os.environ))
        tenant_id = _resolve_ref(config.sharepoint.tenant_id, dict(os.environ))
        client_id = _resolve_ref(config.graph.client_id, dict(os.environ))
        missing = [
            name
            for name, value in (
                ("sharepoint.site_id", target_site_id),
                ("sharepoint.tenant_id", tenant_id),
                ("graph.client_id", client_id),
            )
            if not value
        ]
        if missing:
            print(
                "live publish requires resolved values for: " + ", ".join(missing),
                file=sys.stderr,
            )
            return EXIT_CONFIG_INVALID
        try:
            token_provider = DelegatedDeviceCodeAuth(
                tenant_id=tenant_id,  # type: ignore[arg-type]
                client_id=client_id,  # type: ignore[arg-type]
                scopes=config.graph.scopes,
            )
        except GraphAuthError as exc:
            print(f"graph auth setup failed: {exc}", file=sys.stderr)
            return EXIT_CONFIG_INVALID
        client = GraphSharePointPagesClient()

    if target_site_id is None:  # pragma: no cover - dry-run 経路は config 検証済み
        print("sharepoint.site_id is not configured", file=sys.stderr)
        return EXIT_CONFIG_INVALID

    payload = build_site_page_payload(
        draft,
        urgency=urgency,
        target_site_id=target_site_id,
        target_page_library_id=target_page_library_id,
        mode=config.sharepoint.mode,
    )

    try:
        storage = build_storage(config.storage)
    except StorageError as exc:
        print(f"storage init failed: {exc}", file=sys.stderr)
        return EXIT_RUNTIME_ERROR
    now = datetime.now(UTC)
    draft_id = f"draft-{advisory.advisory_id}"
    draft_post = DraftPost(
        draft_id=draft_id,
        title=draft.title,
        audience=PREVIEW_AUDIENCE,
        urgency=urgency,
        summary_for_users=draft.summary_for_users,
        impact=draft.impact,
        status="approved",
        created_at=now,
        updated_at=now,
        advisory_id=advisory.advisory_id,
        advisory_ids=[advisory.advisory_id],
        required_actions=list(draft.required_actions),
        admin_actions=list(draft.admin_actions),
        references=[dict(ref) for ref in draft.references],
        generated_by_provider=metadata.provider_name,
        prompt_version=metadata.prompt_version,
        generation_input_hash=draft.generation_input_hash,
    )
    try:
        storage.migrate()
        # Publication.draft_id は draft_posts への FK。先に Advisory / DraftPost を保存する。
        storage.advisories.upsert(advisory)
        storage.draft_posts.upsert(draft_post)
        result = publish_site_page(
            payload,
            dry_run=dry_run,
            store=storage,
            now=now,
            draft_id=draft_id,
            draft_status=draft_post.status,
            title=draft.title,
            target_site_id=target_site_id,
            target_page_library_id=target_page_library_id,
            advisory_ids=[advisory.advisory_id],
            advisory_id=advisory.advisory_id,
            provider=metadata,
            client_id=client_id,
            token_provider=token_provider,
            client=client,
            promote=promote,
        )
    except StorageError as exc:
        print(f"publish failed: {exc}", file=sys.stderr)
        return EXIT_RUNTIME_ERROR
    finally:
        storage.close()

    _print_preview(
        {
            "dry_run": result.dry_run,
            "created": result.created,
            "publication": _json_ready(asdict(result.publication)),
            "audit_events": [audit_event_to_dict(event) for event in result.audit_events],
        }
    )
    return EXIT_RUNTIME_ERROR if result.publication.publication_status == "failed" else EXIT_OK


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


def _run_sample_source_job(config: Config, dry_run: bool) -> int:
    """scheduled job skeleton: sample source を取得し DraftPost 生成まで実行する。"""
    from .llm import MockLLMProvider
    from .sample_source import run_sample_source_job
    from .storage.errors import StorageError
    from .storage.factory import build_storage

    try:
        storage = build_storage(config.storage)
        provider = MockLLMProvider(
            prompt_version=config.llm.prompt_version or DEFAULT_PROMPT_VERSION
        )
    except StorageError as exc:
        print(f"sample source job init failed: {exc}", file=sys.stderr)
        return EXIT_RUNTIME_ERROR

    try:
        storage.migrate()
        results = run_sample_source_job(storage, provider)
    except StorageError as exc:
        print(f"sample source job failed: {exc}", file=sys.stderr)
        return EXIT_RUNTIME_ERROR
    except Exception as exc:  # noqa: BLE001 - scheduled job reports runtime failure at boundary
        print(f"sample source job failed: {exc}", file=sys.stderr)
        return EXIT_RUNTIME_ERROR
    finally:
        storage.close()

    _print_preview(
        {
            "dry_run": dry_run,
            "generated_count": len(results),
            "draft_ids": [result.draft_post.draft_id for result in results],
            "advisory_ids": [result.advisory.advisory_id for result in results],
            "source_record_ids": [result.source_record.source_record_id for result in results],
        }
    )
    return EXIT_OK


def _run_publish_approved(config: Config, dry_run: bool) -> int:
    """pending な publish_request AdminCommand を処理し、approved DraftPost を投稿する。

    dry_run=True または config.sharepoint.allow_publish=False の場合は実投稿しない。
    投稿操作は人間が Admin UI/API で publish_request コマンドを発行した後にのみ実行される。
    """
    from .errors import GraphAuthError, PublishError
    from .secrets import is_secret_ref, secret_env_name
    from .sharepoint_publisher import (
        MicrosoftGraphClient,
        NoopGraphClient,
        publish_approved_draft,
    )
    from .storage.errors import StorageError
    from .storage.factory import build_storage

    effective_dry_run = dry_run or not config.sharepoint.allow_publish

    # Resolve env: references for SharePoint target identifiers at the publish boundary.
    def _resolve(value: str | None) -> str:
        if value and is_secret_ref(value):
            return os.environ.get(secret_env_name(value), "")
        return value or ""

    target_site_id = _resolve(config.sharepoint.site_id)
    target_page_library_id = _resolve(config.sharepoint.page_library_id)

    # Validate Graph auth before claiming commands so that a missing token
    # does not leave publish_request rows stuck in processing state.
    if effective_dry_run:
        graph: object = NoopGraphClient()
    else:
        try:
            graph = MicrosoftGraphClient.from_env()
        except GraphAuthError as exc:
            print(f"Graph auth error: {exc}", file=sys.stderr)
            return EXIT_RUNTIME_ERROR

    try:
        storage = build_storage(config.storage)
    except StorageError as exc:
        print(f"storage init failed: {exc}", file=sys.stderr)
        return EXIT_RUNTIME_ERROR

    try:
        storage.migrate()
        # Claim only publish_request commands so other command types are never blocked.
        publish_commands = storage.admin_commands.claim_pending(command_type="publish_request")

        if not publish_commands:
            print(
                json.dumps(
                    {
                        "dry_run": effective_dry_run,
                        "processed": 0,
                        "reason": "no pending publish_request commands",
                    },
                    ensure_ascii=False,
                )
            )
            return EXIT_OK

        results: list[dict[str, Any]] = []
        for cmd in publish_commands:
            draft_id = cmd.target_draft_id
            if not draft_id:
                storage.admin_commands.fail(
                    cmd.command_id,
                    error_code="missing_target_draft_id",
                    error_message="publish_request command has no target_draft_id",
                )
                results.append(
                    {
                        "command_id": cmd.command_id,
                        "status": "failed",
                        "reason": "missing_target_draft_id",
                    }
                )
                continue

            draft = storage.draft_posts.get(draft_id)
            if draft is None:
                storage.admin_commands.fail(
                    cmd.command_id,
                    error_code="draft_not_found",
                    error_message=f"DraftPost {draft_id!r} not found",
                )
                results.append(
                    {
                        "command_id": cmd.command_id,
                        "draft_id": draft_id,
                        "status": "failed",
                        "reason": "draft_not_found",
                    }
                )
                continue

            try:
                result = publish_approved_draft(
                    draft=draft,
                    storage=storage,
                    graph=graph,  # type: ignore[arg-type]
                    target_site_id=target_site_id,
                    target_page_library_id=target_page_library_id,
                    actor=cmd.requested_by or "system",
                    dry_run=effective_dry_run,
                    correlation_id=cmd.correlation_id or uuid.uuid4().hex,
                )
                storage.admin_commands.complete(cmd.command_id)
                results.append(
                    {
                        "command_id": cmd.command_id,
                        "draft_id": draft_id,
                        "status": "published" if not effective_dry_run else "dry_run",
                        "publication_id": result.publication.publication_id,
                        "created": result.created,
                    }
                )
            except Exception as exc:
                error_code = "publish_error" if isinstance(exc, PublishError) else "system_error"
                storage.admin_commands.fail(
                    cmd.command_id,
                    error_code=error_code,
                    error_message=str(exc)[:500],
                )
                results.append(
                    {
                        "command_id": cmd.command_id,
                        "draft_id": draft_id,
                        "status": "failed",
                        "reason": str(exc)[:200],
                    }
                )

        _print_preview(
            {"dry_run": effective_dry_run, "processed": len(results), "results": results}
        )
        return EXIT_OK

    except StorageError as exc:
        print(f"publish-approved failed: {exc}", file=sys.stderr)
        return EXIT_RUNTIME_ERROR
    finally:
        storage.close()


def _run_import_external(input_file: Path, config: Config, dry_run: bool) -> int:
    """外部 collector の import ファイルを schema 検証して storage に保存する。"""
    from .external_collector_import import ExternalCollectorImportError, import_from_file
    from .storage.errors import StorageError
    from .storage.factory import build_storage

    try:
        storage = build_storage(config.storage)
    except StorageError as exc:
        print(f"storage init failed: {exc}", file=sys.stderr)
        return EXIT_RUNTIME_ERROR

    try:
        storage.migrate()
        result = import_from_file(input_file, storage, dry_run=dry_run)
    except FileNotFoundError:
        print(f"import file not found: {input_file}", file=sys.stderr)
        return EXIT_RUNTIME_ERROR
    except OSError as exc:
        print(f"import file read failed: {exc}", file=sys.stderr)
        return EXIT_RUNTIME_ERROR
    except ExternalCollectorImportError as exc:
        print(f"import validation failed: {exc}", file=sys.stderr)
        return EXIT_INPUT_INVALID
    except StorageError as exc:
        print(f"import storage failed: {exc}", file=sys.stderr)
        return EXIT_RUNTIME_ERROR
    finally:
        storage.close()

    summary: dict[str, object] = {
        "dry_run": dry_run,
        "accepted_count": result.accepted_count,
        "rejected_count": result.rejected_count,
        "advisory_ids": [adv.advisory_id for adv in result.advisories],
    }
    if result.rejected_records:
        summary["rejected_reasons"] = [
            {"index": r.index, "reason": r.reason} for r in result.rejected_records
        ]
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return EXIT_OK


def _apply_migrations(storage: object) -> list[str]:
    """pending を確認してから migrate を適用し、適用した version を返す。"""
    pending = storage.pending_migrations()  # type: ignore[attr-defined]
    storage.migrate()  # type: ignore[attr-defined]
    return list(pending)
