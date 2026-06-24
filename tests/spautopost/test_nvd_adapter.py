"""NVD adapter unit/fixture tests. No live network access."""

from __future__ import annotations

import io
import urllib.error
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

import pytest

from spautopost.nvd_adapter import (
    NvdAdapterError,
    NvdHttpResponse,
    NvdRateLimitPolicy,
    NvdSourceAdapter,
    urllib_transport,
)
from spautopost.source_adapters import SourceFetchQuery

NOW = datetime(2026, 6, 24, 12, 0, tzinfo=UTC)


def _cve_item(
    cve_id: str = "CVE-2026-0001",
    *,
    with_metrics: bool = True,
    with_kev: bool = False,
) -> dict[str, object]:
    cve: dict[str, object] = {
        "id": cve_id,
        "published": "2026-06-20T09:00:00.000",
        "lastModified": "2026-06-22T10:30:00.000",
        "descriptions": [
            {"lang": "es", "value": "Una vulnerabilidad."},
            {"lang": "en", "value": "Example Product allows privilege escalation."},
        ],
        "references": [
            {"url": "https://example.com/advisory", "source": "vendor@example.com"},
            {"url": "https://nvd.nist.gov/vuln/detail/" + cve_id},
        ],
        "configurations": [
            {
                "nodes": [
                    {
                        "cpeMatch": [
                            {
                                "vulnerable": True,
                                "criteria": "cpe:2.3:a:example_vendor:example_product:1.0:*:*:*:*:*:*:*",  # noqa: E501
                            }
                        ]
                    }
                ]
            }
        ],
    }
    if with_metrics:
        cve["metrics"] = {
            "cvssMetricV31": [
                {
                    "type": "Primary",
                    "cvssData": {
                        "version": "3.1",
                        "vectorString": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
                        "baseScore": 9.8,
                        "baseSeverity": "CRITICAL",
                    },
                }
            ]
        }
    if with_kev:
        cve["cisaExploitAdd"] = "2026-06-23"
        cve["cisaVulnerabilityName"] = "Example Product Privilege Escalation"
    return {"cve": cve}


def _page(items: Sequence[Mapping[str, object]], *, total: int, start: int = 0) -> NvdHttpResponse:
    return NvdHttpResponse(
        status=200,
        body={
            "totalResults": total,
            "resultsPerPage": len(items),
            "startIndex": start,
            "vulnerabilities": list(items),
        },
    )


class RecordingTransport:
    """Returns queued responses and records requested URLs + headers."""

    def __init__(self, responses: Sequence[NvdHttpResponse]) -> None:
        self._responses = list(responses)
        self.urls: list[str] = []
        self.headers: list[Mapping[str, str]] = []

    def __call__(self, url: str, headers: Mapping[str, str]) -> NvdHttpResponse:
        self.urls.append(url)
        self.headers.append(dict(headers))
        return self._responses[min(len(self.urls) - 1, len(self._responses) - 1)]


def _no_sleep_policy(sleeps: list[float] | None = None, **kwargs: object) -> NvdRateLimitPolicy:
    record = sleeps if sleeps is not None else []
    return NvdRateLimitPolicy(sleeper=record.append, **kwargs)  # type: ignore[arg-type]


def test_fetch_by_cve_id_builds_source_record_and_advisory() -> None:
    transport = RecordingTransport([_page([_cve_item()], total=1)])
    adapter = NvdSourceAdapter(transport=transport, rate_limit=_no_sleep_policy())

    assert adapter.validate_config().ok
    documents = adapter.fetch(SourceFetchQuery(cve_id="CVE-2026-0001"), now=NOW)
    advisory = adapter.normalize(documents[0], now=NOW)[0]

    assert len(documents) == 1
    assert "cveIds=CVE-2026-0001" in transport.urls[0]
    record = documents[0].source_record
    assert record.source_type == "nvd"
    assert record.source_url == "https://nvd.nist.gov/vuln/detail/CVE-2026-0001"
    assert record.retrieved_at == NOW
    assert record.raw_hash
    assert advisory.advisory_id == "nvd-cve-2026-0001"
    assert advisory.cve_ids == ("CVE-2026-0001",)
    assert advisory.summary == "Example Product allows privilege escalation."
    assert advisory.published_at == datetime(2026, 6, 20, 9, 0, tzinfo=UTC)
    assert advisory.cvss_version == "3.1"
    assert advisory.cvss_score == 9.8
    assert advisory.severity == "critical"
    assert "vendor:example_vendor" in advisory.tags
    assert "product:example_product" in advisory.tags
    assert advisory.references[0]["type"] == "nvd"


def test_no_api_key_sends_no_apikey_header() -> None:
    transport = RecordingTransport([_page([_cve_item()], total=1)])
    adapter = NvdSourceAdapter(transport=transport, rate_limit=_no_sleep_policy())

    adapter.fetch(SourceFetchQuery(cve_id="CVE-2026-0001"), now=NOW)

    assert "apiKey" not in transport.headers[0]


def test_api_key_is_sent_as_header_only() -> None:
    transport = RecordingTransport([_page([_cve_item()], total=1)])
    adapter = NvdSourceAdapter(
        transport=transport, api_key="dummy-key", rate_limit=_no_sleep_policy()
    )

    adapter.fetch(SourceFetchQuery(cve_id="CVE-2026-0001"), now=NOW)

    assert transport.headers[0]["apiKey"] == "dummy-key"
    assert "dummy-key" not in transport.urls[0]


def test_kev_status_is_preserved() -> None:
    transport = RecordingTransport([_page([_cve_item(with_kev=True)], total=1)])
    adapter = NvdSourceAdapter(transport=transport, rate_limit=_no_sleep_policy())

    document = adapter.fetch(SourceFetchQuery(cve_id="CVE-2026-0001"), now=NOW)[0]
    advisory = adapter.normalize(document, now=NOW)[0]

    assert "kev" in advisory.tags
    assert "known-exploited" in advisory.tags
    assert advisory.title == "Example Product Privilege Escalation"
    assert any(ref["type"] == "kev" for ref in advisory.references)


def test_nested_cpe_and_escaped_colons_are_normalized() -> None:
    item = _cve_item()
    cve = item["cve"]
    assert isinstance(cve, dict)
    cve["configurations"] = [
        {
            "nodes": [
                {
                    "children": [
                        {
                            "cpeMatch": [
                                {
                                    "vulnerable": True,
                                    "criteria": (
                                        r"cpe:2.3:a:example\:vendor:product\:name"
                                        r":1.0:*:*:*:*:*:*:*"
                                    ),
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    ]
    transport = RecordingTransport([_page([item], total=1)])
    adapter = NvdSourceAdapter(transport=transport, rate_limit=_no_sleep_policy())

    document = adapter.fetch(SourceFetchQuery(cve_id="CVE-2026-0001"), now=NOW)[0]
    advisory = adapter.normalize(document, now=NOW)[0]

    assert "vendor:example:vendor" in advisory.tags
    assert "product:product:name" in advisory.tags


def test_missing_metrics_fall_back_to_unknown_severity() -> None:
    transport = RecordingTransport([_page([_cve_item(with_metrics=False)], total=1)])
    adapter = NvdSourceAdapter(transport=transport, rate_limit=_no_sleep_policy())

    document = adapter.fetch(SourceFetchQuery(cve_id="CVE-2026-0001"), now=NOW)[0]
    advisory = adapter.normalize(document, now=NOW)[0]

    assert advisory.severity == "unknown"
    assert advisory.cvss_version is None
    assert advisory.cvss_score is None


def test_date_range_fetch_sends_lastmod_params() -> None:
    transport = RecordingTransport([_page([_cve_item()], total=1)])
    adapter = NvdSourceAdapter(transport=transport, rate_limit=_no_sleep_policy())

    adapter.fetch(
        SourceFetchQuery(
            modified_from=datetime(2026, 6, 1, tzinfo=UTC),
            modified_to=datetime(2026, 6, 24, tzinfo=UTC),
        ),
        now=NOW,
    )

    assert "lastModStartDate=2026-06-01T00:00:00.000" in transport.urls[0]
    assert "lastModEndDate=2026-06-24T00:00:00.000" in transport.urls[0]


def test_date_range_over_120_days_is_rejected_without_transport_call() -> None:
    transport = RecordingTransport([_page([], total=0)])
    adapter = NvdSourceAdapter(transport=transport, rate_limit=_no_sleep_policy())

    with pytest.raises(NvdAdapterError):
        adapter.fetch(
            SourceFetchQuery(
                published_from=datetime(2026, 1, 1, tzinfo=UTC),
                published_to=datetime(2026, 6, 1, tzinfo=UTC),
            ),
            now=NOW,
        )
    assert transport.urls == []


def test_fetch_without_query_is_rejected() -> None:
    transport = RecordingTransport([_page([], total=0)])
    adapter = NvdSourceAdapter(transport=transport, rate_limit=_no_sleep_policy())

    with pytest.raises(NvdAdapterError):
        adapter.fetch(now=NOW)
    assert transport.urls == []


def test_more_than_100_cve_ids_is_rejected() -> None:
    transport = RecordingTransport([_page([], total=0)])
    adapter = NvdSourceAdapter(transport=transport, rate_limit=_no_sleep_policy())

    with pytest.raises(NvdAdapterError):
        adapter.fetch_cve_ids([f"CVE-2026-{n:04d}" for n in range(101)], now=NOW)
    assert transport.urls == []


def test_pagination_collects_all_pages_with_interval_sleep() -> None:
    page_one = _page([_cve_item("CVE-2026-0001"), _cve_item("CVE-2026-0002")], total=3, start=0)
    page_two = _page([_cve_item("CVE-2026-0003")], total=3, start=2)
    transport = RecordingTransport([page_one, page_two])
    sleeps: list[float] = []
    adapter = NvdSourceAdapter(
        transport=transport,
        results_per_page=2,
        rate_limit=_no_sleep_policy(sleeps, min_interval_seconds=6.0),
    )

    documents = adapter.fetch(SourceFetchQuery(cve_id="CVE-2026-0001"), now=NOW)

    assert len(documents) == 3
    assert "startIndex=0" in transport.urls[0]
    assert "startIndex=2" in transport.urls[1]
    assert sleeps == [6.0]  # one inter-page interval, no sleep before first request


def test_retry_after_is_honored_on_429() -> None:
    throttled = NvdHttpResponse(status=429, body={}, headers={"Retry-After": "2"})
    success = _page([_cve_item()], total=1)
    transport = RecordingTransport([throttled, success])
    sleeps: list[float] = []
    adapter = NvdSourceAdapter(transport=transport, rate_limit=_no_sleep_policy(sleeps))

    documents = adapter.fetch(SourceFetchQuery(cve_id="CVE-2026-0001"), now=NOW)

    assert len(documents) == 1
    assert sleeps == [2.0]


def test_negative_retry_after_is_clamped() -> None:
    throttled = NvdHttpResponse(status=429, body={}, headers={"Retry-After": "-2"})
    success = _page([_cve_item()], total=1)
    transport = RecordingTransport([throttled, success])
    sleeps: list[float] = []
    adapter = NvdSourceAdapter(transport=transport, rate_limit=_no_sleep_policy(sleeps))

    adapter.fetch(SourceFetchQuery(cve_id="CVE-2026-0001"), now=NOW)

    assert sleeps == [0.0]


def test_retries_are_bounded() -> None:
    throttled = NvdHttpResponse(status=503, body={}, headers={})
    transport = RecordingTransport([throttled])
    adapter = NvdSourceAdapter(transport=transport, rate_limit=_no_sleep_policy(max_retries=2))

    with pytest.raises(NvdAdapterError):
        adapter.fetch(SourceFetchQuery(cve_id="CVE-2026-0001"), now=NOW)
    assert len(transport.urls) == 3  # initial + 2 retries


def test_urllib_transport_preserves_retry_status_for_non_json_http_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_http_error(*_args: object, **_kwargs: object) -> object:
        raise urllib.error.HTTPError(
            url="https://services.nvd.nist.gov/rest/json/cves/2.0",
            code=429,
            msg="Too Many Requests",
            hdrs={"Retry-After": "1"},
            fp=io.BytesIO(b"<html>not json</html>"),
        )

    monkeypatch.setattr("urllib.request.urlopen", raise_http_error)

    response = urllib_transport("https://services.nvd.nist.gov/rest/json/cves/2.0", {})

    assert response.status == 429
    assert response.body == {}
    assert response.headers["Retry-After"] == "1"


def test_non_retryable_status_raises() -> None:
    transport = RecordingTransport([NvdHttpResponse(status=404, body={})])
    adapter = NvdSourceAdapter(transport=transport, rate_limit=_no_sleep_policy())

    with pytest.raises(NvdAdapterError):
        adapter.fetch(SourceFetchQuery(cve_id="CVE-2026-0404"), now=NOW)


def test_cvss_v2_severity_derived_from_score_when_baseseverity_absent() -> None:
    item = {
        "cve": {
            "id": "CVE-2026-0009",
            "descriptions": [{"lang": "en", "value": "Older CVE with only CVSS v2."}],
            "metrics": {
                "cvssMetricV2": [
                    {
                        "type": "Primary",
                        "cvssData": {
                            "version": "2.0",
                            "vectorString": "AV:N/AC:L/Au:N/C:P/I:P/A:P",
                            "baseScore": 7.5,
                        },
                    }
                ]
            },
        }
    }
    transport = RecordingTransport([_page([item], total=1)])
    adapter = NvdSourceAdapter(transport=transport, rate_limit=_no_sleep_policy())

    advisory = adapter.normalize(
        adapter.fetch(SourceFetchQuery(cve_id="CVE-2026-0009"), now=NOW)[0], now=NOW
    )[0]

    assert advisory.cvss_version == "2.0"
    assert advisory.cvss_score == 7.5
    assert advisory.severity == "high"  # derived from score band, no baseSeverity present


def test_non_english_description_falls_back_to_first_value() -> None:
    item = {
        "cve": {
            "id": "CVE-2026-0010",
            "descriptions": [{"lang": "fr", "value": "Une description."}],
        }
    }
    transport = RecordingTransport([_page([item], total=1)])
    adapter = NvdSourceAdapter(transport=transport, rate_limit=_no_sleep_policy())

    advisory = adapter.normalize(
        adapter.fetch(SourceFetchQuery(cve_id="CVE-2026-0010"), now=NOW)[0], now=NOW
    )[0]

    assert advisory.summary == "Une description."
    assert advisory.tags == ("nvd",)  # no metrics, no CPE, no KEV
    assert advisory.references == ()
