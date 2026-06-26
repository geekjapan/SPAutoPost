"""共有テストフィクスチャ。"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pytest

VALID_DEFAULT = """
app:
  environment: development
  dry_run: true
  log_level: info

storage:
  provider: sqlite
  sqlite_path: ./data/spautopost.dev.sqlite3

llm:
  provider: test_mock
  prompt_version: v1

sharepoint:
  mode: site-page
  default_draft: true
  allow_publish: false
  tenant_id: env:SPAUTOPOST_TENANT_ID
  site_id: env:SPAUTOPOST_SHAREPOINT_SITE_ID
  page_library_id: env:SPAUTOPOST_SHAREPOINT_PAGE_LIBRARY_ID
  dedicated_site: true
  news_promote: false
  idempotency_scope: site-and-page-library

security:
  block_auto_publish: true
  require_approval: true
  redact_secrets_in_logs: true
"""

VALID_ENVIRON: Mapping[str, str] = {
    "SPAUTOPOST_TENANT_ID": "tenant-xyz",
    "SPAUTOPOST_SHAREPOINT_SITE_ID": "site-xyz",
    "SPAUTOPOST_SHAREPOINT_PAGE_LIBRARY_ID": "lib-xyz",
}


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    """有効な default.yml を持つ config ディレクトリを返す。"""
    (tmp_path / "default.yml").write_text(VALID_DEFAULT, encoding="utf-8")
    return tmp_path


@pytest.fixture
def valid_environ() -> dict[str, str]:
    return dict(VALID_ENVIRON)
