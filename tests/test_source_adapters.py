"""Source adapter interface and fixture normalization tests."""

from __future__ import annotations

from datetime import UTC, datetime

from spautopost.source_adapters import (
    SourceFetchQuery,
    build_feed_fixture_adapter,
    build_kev_fixture_adapter,
    build_vendor_advisory_fixture_adapter,
)

NOW = datetime(2026, 6, 24, 12, 0, tzinfo=UTC)


def test_kev_fixture_adapter_reflects_known_exploited_status_on_advisory() -> None:
    adapter = build_kev_fixture_adapter(
        (
            {
                "cveID": "CVE-2026-0001",
                "vendorProject": "Example Vendor",
                "product": "Example Product",
                "vulnerabilityName": "Example Product Command Injection Vulnerability",
                "dateAdded": "2026-06-20",
                "shortDescription": "Example Product contains a command injection issue.",
                "requiredAction": "Apply vendor mitigations.",
                "dueDate": "2026-07-10",
                "knownRansomwareCampaignUse": "Unknown",
                "source_url": "https://www.cisa.gov/known-exploited-vulnerabilities-catalog",
            },
        )
    )

    assert adapter.validate_config().ok
    document = adapter.fetch(SourceFetchQuery(cve_id="CVE-2026-0001"), now=NOW)[0]
    advisory = adapter.normalize(document, now=NOW)[0]

    assert document.source_record.source_type == "kev"
    assert document.source_record.source_name == "cisa-kev"
    assert document.source_record.raw_hash
    assert advisory.advisory_id == "kev-cve-2026-0001"
    assert advisory.cve_ids == ("CVE-2026-0001",)
    assert advisory.published_at == datetime(2026, 6, 20, 0, 0, tzinfo=UTC)
    assert advisory.references[0]["type"] == "kev"
    assert "known-exploited" in advisory.tags
    assert "vendor:Example Vendor" in advisory.tags
    assert "product:Example Product" in advisory.tags


def test_vendor_fixture_adapter_normalizes_vendor_advisory() -> None:
    adapter = build_vendor_advisory_fixture_adapter(
        (
            {
                "vendor_advisory_id": "EX-2026-001",
                "title": "Example Vendor Security Advisory",
                "summary": "A supported product requires an update.",
                "url": "https://example.com/security/EX-2026-001",
                "published_at": "2026-06-21T00:00:00Z",
                "updated_at": "2026-06-22T00:00:00Z",
                "severity": "high",
                "cve_ids": ["CVE-2026-0001"],
                "tags": ["example-product"],
            },
        )
    )

    document = adapter.fetch(now=NOW)[0]
    advisory = adapter.normalize(document, now=NOW)[0]

    assert document.source_record.source_type == "vendor"
    assert advisory.advisory_id == "vendor-EX-2026-001"
    assert advisory.vendor_advisory_ids == ("EX-2026-001",)
    assert advisory.severity == "high"
    assert advisory.references == (
        {
            "label": "Vendor advisory",
            "url": "https://example.com/security/EX-2026-001",
            "type": "vendor",
        },
    )
    assert advisory.tags == ("vendor-advisory", "example-product")


def test_feed_fixture_adapter_is_rss_skeleton() -> None:
    adapter = build_feed_fixture_adapter(
        (
            {
                "title": "Example RSS advisory",
                "summary": "Feed item summary.",
                "url": "https://example.com/feed/advisory",
                "published_at": "2026-06-23T03:00:00Z",
                "cve_ids": ["CVE-2026-0002"],
            },
        )
    )

    document = adapter.fetch(now=NOW)[0]
    advisory = adapter.normalize(document, now=NOW)[0]

    assert document.source_record.source_type == "rss"
    assert advisory.advisory_id.startswith("rss-")
    assert advisory.cve_ids == ("CVE-2026-0002",)
    assert advisory.references[0]["type"] == "rss"
    assert advisory.tags == ("feed",)


def test_fixture_adapter_filters_by_cve_id() -> None:
    adapter = build_feed_fixture_adapter(
        (
            {"title": "First", "url": "https://example.com/1", "cve_ids": ["CVE-2026-0001"]},
            {"title": "Second", "url": "https://example.com/2", "cve_ids": ["CVE-2026-0002"]},
        )
    )

    documents = adapter.fetch(SourceFetchQuery(cve_id="CVE-2026-0002"), now=NOW)

    assert len(documents) == 1
    assert documents[0].raw_payload["title"] == "Second"
