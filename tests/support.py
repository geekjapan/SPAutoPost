"""テスト用の storage fixture とサンプル entity。"""

from __future__ import annotations

import os

from spautopost.storage.serialization import now_iso
from spautopost.storage import PostgresStorage, SqliteStorage


def make_sqlite() -> SqliteStorage:
    """migration 適用済みの in-memory SQLite storage を返す。"""
    storage = SqliteStorage(":memory:")
    storage.migrate()
    return storage


def make_postgres():
    """DATABASE_URL と psycopg がある時だけ migration 適用済み PG storage を返す。無ければ None。"""
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        return None
    try:
        import psycopg  # noqa: F401
    except ImportError:
        return None
    storage = PostgresStorage(dsn)
    storage.migrate()
    return storage


def sample_draft(draft_id: str = "draft-1", status: str = "created") -> dict:
    ts = now_iso()
    return {
        "draft_id": draft_id,
        "title": "緊急: 重大な脆弱性",
        "audience": "general_users",
        "urgency": "high",
        "summary_for_users": "影響と対処を確認してください。",
        "impact": "情報漏えいの恐れ",
        "status": status,
        "created_at": ts,
        "updated_at": ts,
        "advisory_ids": ["adv-1", "adv-2"],
        "required_actions": ["パッチ適用", "再起動"],
        "references": [{"label": "NVD", "url": "https://nvd.example/CVE", "type": "nvd"}],
    }


def sample_publication(pub_id: str, draft_id: str, idem: str) -> dict:
    ts = now_iso()
    return {
        "publication_id": pub_id,
        "draft_id": draft_id,
        "target_type": "list-item",
        "target_site_id": "site-1",
        "publication_status": "pending",
        "idempotency_key": idem,
        "created_at": ts,
        "updated_at": ts,
    }


def sample_command(command_id: str, idem: str, draft_id: str = "draft-1",
                   command_type: str = "approve") -> dict:
    return {
        "command_id": command_id,
        "command_type": command_type,
        "target_draft_id": draft_id,
        "requested_by": "alice",
        "idempotency_key": idem,
        "correlation_id": "corr-1",
        "payload": {"comment": "ok"},
    }
