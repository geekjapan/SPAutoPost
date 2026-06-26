"""Firecrawl source adapter unit/integration tests (spike)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from spautopost.firecrawl_adapter import FirecrawlSourceAdapter
from spautopost.source_adapters import SourceAdapterError, SourceDocument, SourceFetchQuery

NOW = datetime(2026, 6, 26, 12, 0, tzinfo=UTC)
SAMPLE_URL = "https://example.com/security-advisory"
SAMPLE_MARKDOWN = "# Example Advisory\n\nThis is a test advisory."
SAMPLE_METADATA = {"title": "Example Advisory", "sourceURL": SAMPLE_URL, "statusCode": 200}


@pytest.fixture()
def adapter_with_key() -> FirecrawlSourceAdapter:
    return FirecrawlSourceAdapter(api_key="fc-test-key")


@pytest.fixture()
def adapter_no_key() -> FirecrawlSourceAdapter:
    return FirecrawlSourceAdapter(api_key="")


# --- validate_config ---


def test_validate_config_ok_when_api_key_set(adapter_with_key: FirecrawlSourceAdapter) -> None:
    status = adapter_with_key.validate_config()
    assert status.ok


def test_validate_config_fails_when_api_key_missing(
    adapter_no_key: FirecrawlSourceAdapter,
) -> None:
    status = adapter_no_key.validate_config()
    assert not status.ok
    assert status.code == "missing_api_key"


def test_validate_config_reads_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-env-key")
    adapter = FirecrawlSourceAdapter()
    assert adapter.validate_config().ok


# --- normalize ---


def _make_document(
    adapter: FirecrawlSourceAdapter,
    *,
    markdown: str = SAMPLE_MARKDOWN,
    metadata: dict | None = None,
    url: str = SAMPLE_URL,
) -> SourceDocument:
    raw_payload: dict[str, object] = {
        "url": url,
        "markdown": markdown,
        "metadata": metadata if metadata is not None else SAMPLE_METADATA,
        "title": (metadata or SAMPLE_METADATA).get("title", ""),
    }
    from spautopost.source_adapters import _hash_json
    from spautopost.storage.models import SourceRecord

    raw_hash = _hash_json(raw_payload)
    record = SourceRecord(
        source_record_id=f"firecrawl-{raw_hash[:12]}",
        source_type="web_scrape",
        source_name="firecrawl",
        source_url=url,
        retrieved_at=NOW,
        raw_hash=raw_hash,
        parser_version="firecrawl-spike-v1",
        created_at=NOW,
        http_status=200,
    )
    return SourceDocument(source_record=record, raw_payload=raw_payload)


def test_normalize_maps_title_and_summary(adapter_with_key: FirecrawlSourceAdapter) -> None:
    document = _make_document(adapter_with_key)
    advisories = adapter_with_key.normalize(document, now=NOW)

    assert len(advisories) == 1
    advisory = advisories[0]
    assert advisory.title == "Example Advisory"
    assert SAMPLE_MARKDOWN[:5000] in advisory.summary
    assert advisory.severity == "unknown"
    assert "firecrawl" in advisory.tags
    assert "web_scrape" in advisory.tags
    assert advisory.references[0]["type"] == "web_scrape"
    assert advisory.references[0]["url"] == SAMPLE_URL


def test_normalize_uses_url_as_title_when_no_title(
    adapter_with_key: FirecrawlSourceAdapter,
) -> None:
    document = _make_document(
        adapter_with_key,
        metadata={"sourceURL": SAMPLE_URL, "statusCode": 200},
    )
    advisories = adapter_with_key.normalize(document, now=NOW)

    assert advisories[0].title == SAMPLE_URL


def test_normalize_truncates_long_markdown(adapter_with_key: FirecrawlSourceAdapter) -> None:
    long_md = "x" * 10_000
    adapter = FirecrawlSourceAdapter(api_key="fc-test", max_content_chars=100)
    document = _make_document(adapter, markdown=long_md)
    advisories = adapter.normalize(document, now=NOW)

    assert len(advisories[0].summary) == 100


# --- fetch (mocked) ---


def _make_mock_result(
    markdown: str = SAMPLE_MARKDOWN,
    title: str = "Example Advisory",
    metadata: dict | None = None,
) -> MagicMock:
    result = MagicMock()
    result.markdown = markdown
    result.title = title
    result.metadata = metadata if metadata is not None else SAMPLE_METADATA
    return result


def test_fetch_returns_source_document(adapter_with_key: FirecrawlSourceAdapter) -> None:
    mock_result = _make_mock_result()
    mock_firecrawl = MagicMock()
    mock_firecrawl.V1FirecrawlApp.return_value.scrape_url.return_value = mock_result

    with patch.dict("sys.modules", {"firecrawl": mock_firecrawl}):
        query = SourceFetchQuery(url=SAMPLE_URL)
        documents = adapter_with_key.fetch(query, now=NOW)

    assert len(documents) == 1
    doc = documents[0]
    assert doc.source_record.source_type == "web_scrape"
    assert doc.source_record.source_url == SAMPLE_URL
    assert doc.raw_payload["markdown"] == SAMPLE_MARKDOWN
    assert doc.raw_payload["metadata"] == SAMPLE_METADATA


def test_fetch_returns_empty_when_no_url(adapter_with_key: FirecrawlSourceAdapter) -> None:
    result = adapter_with_key.fetch(SourceFetchQuery(), now=NOW)
    assert list(result) == []


def test_fetch_raises_on_api_error(adapter_with_key: FirecrawlSourceAdapter) -> None:
    mock_firecrawl = MagicMock()
    mock_firecrawl.V1FirecrawlApp.return_value.scrape_url.side_effect = RuntimeError("API error")

    with patch.dict("sys.modules", {"firecrawl": mock_firecrawl}):
        with pytest.raises(SourceAdapterError, match="scrape_url failed"):
            adapter_with_key.fetch(SourceFetchQuery(url=SAMPLE_URL), now=NOW)
