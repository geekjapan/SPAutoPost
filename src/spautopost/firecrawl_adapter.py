"""Firecrawl source adapter — spike 評価実装。

Issue #34 の評価目的で作成。本番採用が確定した場合は別 Issue で正式実装する。
依存: firecrawl-py>=4.0 (pip install "spautopost[spike]")
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import TYPE_CHECKING

from .source_adapters import (
    AdapterStatus,
    SourceAdapterError,
    SourceDocument,
    SourceFetchQuery,
    _hash_json,
    _utc_now,
)
from .storage.models import Advisory, SourceRecord, SourceType

if TYPE_CHECKING:
    from collections.abc import Sequence

FIRECRAWL_SOURCE_NAME = "firecrawl"
FIRECRAWL_SOURCE_TYPE: SourceType = "web_scrape"
FIRECRAWL_PARSER_VERSION = "firecrawl-spike-v1"

_DEFAULT_MAX_CHARS = 5000
_DEFAULT_TIMEOUT_MS = 30_000


def _read_int_env(name: str, default: int) -> int:
    """環境変数を整数として読む。未設定時はデフォルト値、非整数値は SourceAdapterError。"""
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise SourceAdapterError(f"{name} must be an integer, got {raw!r}") from exc


class FirecrawlSourceAdapter:
    """Firecrawl API を使った URL → Markdown 取得の spike adapter。"""

    source_type = FIRECRAWL_SOURCE_TYPE
    source_name = FIRECRAWL_SOURCE_NAME

    def __init__(
        self,
        *,
        api_key: str | None = None,
        max_content_chars: int | None = None,
        timeout_ms: int | None = None,
    ) -> None:
        self._api_key = api_key if api_key is not None else os.environ.get("FIRECRAWL_API_KEY", "")
        self._max_content_chars = (
            max_content_chars
            if max_content_chars is not None
            else _read_int_env("FIRECRAWL_MAX_CONTENT_CHARS", _DEFAULT_MAX_CHARS)
        )
        self._timeout_ms = (
            timeout_ms
            if timeout_ms is not None
            else _read_int_env("FIRECRAWL_TIMEOUT_SECONDS", 30) * 1000
        )

    def validate_config(self) -> AdapterStatus:
        """FIRECRAWL_API_KEY の存在を検査し AdapterStatus を返す。"""
        if not self._api_key:
            return AdapterStatus(False, "missing_api_key", "FIRECRAWL_API_KEY is not set")
        return AdapterStatus(True)

    def fetch(
        self, query: SourceFetchQuery | None = None, *, now: datetime | None = None
    ) -> Sequence[SourceDocument]:
        """query.url を Firecrawl API でスクレイプし SourceDocument を返す。"""
        if query is None or not query.url:
            return ()

        status = self.validate_config()
        if not status.ok:
            raise SourceAdapterError(f"validate_config failed: {status.message}")

        try:
            from firecrawl import V1FirecrawlApp
        except ImportError as exc:
            raise SourceAdapterError(
                "firecrawl-py is not installed. Run: pip install 'spautopost[spike]'"
            ) from exc

        app = V1FirecrawlApp(api_key=self._api_key)
        try:
            result = app.scrape_url(query.url, formats=["markdown"], timeout=self._timeout_ms)
        except Exception as exc:
            raise SourceAdapterError(f"Firecrawl scrape_url failed: {exc}") from exc

        if result is None:
            raise SourceAdapterError("Firecrawl scrape_url returned None")

        raw_payload: dict[str, object] = {
            "url": query.url,
            "markdown": result.markdown or "",
            "metadata": result.metadata or {},
            "title": result.title or "",
        }
        raw_hash = _hash_json(raw_payload)
        timestamp = _utc_now(now)
        source_record = SourceRecord(
            source_record_id=f"{FIRECRAWL_SOURCE_NAME}-{raw_hash[:12]}",
            source_type=FIRECRAWL_SOURCE_TYPE,
            source_name=FIRECRAWL_SOURCE_NAME,
            source_url=query.url,
            retrieved_at=timestamp,
            raw_hash=raw_hash,
            parser_version=FIRECRAWL_PARSER_VERSION,
            created_at=timestamp,
            http_status=200,
        )
        return (SourceDocument(source_record=source_record, raw_payload=raw_payload),)

    def normalize(
        self, document: SourceDocument, *, now: datetime | None = None
    ) -> Sequence[Advisory]:
        """SourceDocument の Markdown / metadata を Advisory に写像する。"""
        raw = document.raw_payload
        timestamp = _utc_now(now)

        markdown = str(raw.get("markdown") or "")
        raw_metadata = raw.get("metadata")
        metadata: dict[str, object] = dict(raw_metadata) if isinstance(raw_metadata, dict) else {}
        source_url = str(raw.get("url") or metadata.get("sourceURL") or "")

        title = (
            str(raw.get("title") or "").strip()
            or str(metadata.get("title") or "").strip()
            or source_url
        )
        summary = markdown[: self._max_content_chars].strip() or title
        advisory_id = f"web-scrape-{document.source_record.raw_hash[:12]}"

        return (
            Advisory(
                advisory_id=advisory_id,
                title=title,
                summary=summary,
                source_record_id=document.source_record.source_record_id,
                created_at=timestamp,
                normalized_at=timestamp,
                severity="unknown",
                references=({"label": "Source", "url": source_url, "type": "web_scrape"},),
                tags=("firecrawl", "web_scrape"),
            ),
        )
