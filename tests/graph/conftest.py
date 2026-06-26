"""graph delegated PoC テストの共有フィクスチャと fake（network 非依存）。"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from spautopost.config import StorageConfig
from spautopost.dry_run import build_site_page_payload
from spautopost.graph.auth import AuthResult, Identity
from spautopost.graph.sharepoint_client import CreatedPage
from spautopost.llm import DraftOutput, MockLLMProvider, ProviderMetadata
from spautopost.storage.factory import build_storage
from spautopost.storage.models import DraftPost
from spautopost.storage.port import StoragePort

NOW = datetime(2026, 6, 26, 12, 0, tzinfo=UTC)
SECRET_TOKEN = "secret-access-token-should-never-persist"  # noqa: S105 - テスト用ダミー


class FakeTokenProvider:
    """device code 認証の fake。network なしで AuthResult を返す（または例外）。"""

    def __init__(self, *, identity: Identity | None = None, error: Exception | None = None) -> None:
        self.identity = identity or Identity(
            user_principal_name="poc.user@example.com",
            display_name="PoC User",
            object_id="oid-123",
        )
        self.error = error
        self.calls = 0

    def acquire(self) -> AuthResult:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return AuthResult(access_token=SECRET_TOKEN, identity=self.identity)


class FakePagesClient:
    """SharePoint pages クライアントの fake。呼び出しを記録し、任意で例外を投げる。"""

    def __init__(self, *, page_id: str = "page-abc", create_error: Exception | None = None) -> None:
        self.page_id = page_id
        self.create_error = create_error
        self.create_calls: list[dict[str, Any]] = []
        self.publish_calls: list[dict[str, Any]] = []

    def create_site_page(
        self, *, site_id: str, request_body: Mapping[str, Any], access_token: str
    ) -> CreatedPage:
        self.create_calls.append(
            {"site_id": site_id, "request_body": dict(request_body), "access_token": access_token}
        )
        if self.create_error is not None:
            raise self.create_error
        return CreatedPage(page_id=self.page_id, web_url=f"https://sharepoint/{self.page_id}")

    def publish_site_page(self, *, site_id: str, page_id: str, access_token: str) -> None:
        self.publish_calls.append({"site_id": site_id, "page_id": page_id})


@pytest.fixture
def store(tmp_path: Path) -> Iterator[StoragePort]:
    port = build_storage(
        StorageConfig(provider="sqlite", database_url=None, sqlite_path=str(tmp_path / "g.sqlite3"))
    )
    port.migrate()
    # publications.draft_id は draft_posts への FK。テスト対象の draft_id を seed する。
    port.draft_posts.upsert(
        DraftPost(
            draft_id="draft-1",
            title="seed",
            audience="mixed",
            urgency="normal",
            summary_for_users="seed summary",
            impact="seed impact",
            status="approved",
            created_at=NOW,
            updated_at=NOW,
        )
    )
    yield port
    port.close()


@pytest.fixture
def metadata() -> ProviderMetadata:
    return MockLLMProvider(prompt_version="v1").get_provider_metadata()


@pytest.fixture
def draft() -> DraftOutput:
    return DraftOutput(
        title="Example の脆弱性",
        summary_for_users="権限昇格の可能性があります。",
        impact="影響を受ける環境があります。",
        required_actions=["更新プログラムを適用する"],
        references=[{"label": "Vendor", "url": "https://example.com/advisory", "type": "vendor"}],
        warnings=["要確認"],
        admin_actions=["配布計画を立てる"],
        deadline="2026-07-01",
        uncertainty_notes=["影響範囲は精査中"],
        generation_input_hash="hash-abc",
    )


@pytest.fixture
def payload(draft: DraftOutput) -> dict[str, Any]:
    return build_site_page_payload(
        draft,
        urgency="high",
        target_site_id="site-1",
        target_page_library_id="lib-1",
        mode="site-page",
    )
