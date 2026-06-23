"""SPAutoPost CLI / batch entrypoint。

最終運用形ではなく、Azure Container Apps Jobs の command entrypoint を想定する。
起動シーケンス: config load -> validation -> command dispatch。
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

import yaml

from . import __version__
from .config import Config, load_and_validate
from .errors import ConfigValidationError
from .secrets import redact_config

DEFAULT_CONFIG_DIR = Path("config")
DEFAULT_ENV = "development"

EXIT_OK = 0
EXIT_RUNTIME_ERROR = 1
EXIT_CONFIG_INVALID = 2


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
    return _dispatch(args.command, config, effective_dry_run)


def _dispatch(command: str, config: Config, dry_run: bool) -> int:
    if command == "validate-config":
        print(f"OK: config valid (environment={config.app.environment}, dry_run={dry_run})")
        return EXIT_OK
    if command == "show-config":
        dumped = yaml.safe_dump(
            redact_config(dict(config.raw)), allow_unicode=True, sort_keys=False
        )
        print(dumped, end="")
        return EXIT_OK
    print(f"unknown command: {command}", file=sys.stderr)  # pragma: no cover
    return EXIT_RUNTIME_ERROR  # pragma: no cover
