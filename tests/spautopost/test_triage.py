"""Tests for normalization merge, priority scoring, and duplicate-post guard (Issue #14)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from spautopost.storage.models import Advisory
from spautopost.triage import (
    TriageSignals,
    duplicate_post_key,
    merge_advisories,
    priority_score,
    severity_from_cvss,
    triage,
    urgency_for_score,
)

NOW = datetime(2026, 6, 24, 12, 0, tzinfo=UTC)


def _advisory(advisory_id: str, **overrides: object) -> Advisory:
    base: dict[str, object] = {
        "advisory_id": advisory_id,
        "title": "Example advisory",
        "summary": "Example summary.",
        "created_at": NOW,
        "normalized_at": NOW,
    }
    base.update(overrides)
    return Advisory(**base)  # type: ignore[arg-type]


# --- severity mapping ------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (9.8, "critical"),
        (9.0, "critical"),
        (7.5, "high"),
        (4.0, "medium"),
        (0.1, "low"),
        (0.0, "unknown"),
        (None, "unknown"),
    ],
)
def test_severity_from_cvss_maps_score_to_label(score: float | None, expected: str) -> None:
    assert severity_from_cvss(score) == expected


# --- priority score and urgency --------------------------------------------


@pytest.mark.unit
def test_priority_score_sums_documented_weights() -> None:
    advisory = _advisory("a", severity="critical")
    signals = TriageSignals(
        exploit_status="confirmed",
        kev_status="listed",
        patch_available=True,
        internal_relevance="confirmed",
        internet_facing=True,
    )

    # 40 + 40 + 30 + 10 + 30 + 15 = 165
    assert priority_score(advisory, signals) == 165


@pytest.mark.unit
def test_priority_score_derives_kev_from_tags() -> None:
    advisory = _advisory("a", severity="high", tags=("kev", "known-exploited"))

    assert priority_score(advisory, TriageSignals()) == 70  # 30 high + 40 kev tag


@pytest.mark.unit
def test_priority_score_applies_low_confidence_penalty() -> None:
    advisory = _advisory("a", severity="medium")

    assert priority_score(advisory, TriageSignals(source_confidence="low")) == 5  # 15 - 10


@pytest.mark.unit
@pytest.mark.parametrize(
    ("score", "expected"),
    [(80, "emergency"), (79, "high"), (60, "high"), (30, "normal"), (29, "low"), (0, "low")],
)
def test_urgency_for_score_uses_documented_thresholds(score: int, expected: str) -> None:
    assert urgency_for_score(score) == expected


@pytest.mark.unit
def test_triage_combines_score_urgency_and_duplicate_key() -> None:
    advisory = _advisory("a", severity="critical", cve_ids=("CVE-2026-0001",))

    result = triage(advisory, TriageSignals(kev_status="listed"), audience="administrators")

    assert result.priority_score == 80
    assert result.urgency == "emergency"
    assert result.duplicate_key.startswith("dup-")
    assert len(result.duplicate_key) == 68


# --- duplicate post guard --------------------------------------------------


@pytest.mark.unit
def test_duplicate_post_key_is_stable_for_same_identity() -> None:
    first = _advisory("a", cve_ids=("CVE-2026-0001", "CVE-2026-0001"), title="Example Advisory")
    second = _advisory("b", cve_ids=("cve-2026-0001",), title="example   advisory")

    assert duplicate_post_key(first) == duplicate_post_key(second)


@pytest.mark.unit
def test_duplicate_post_key_uses_advisory_id_for_identifier_less_advisories() -> None:
    first = _advisory("a", title="Security Update")
    second = _advisory("b", title="Security Update")

    assert duplicate_post_key(first) != duplicate_post_key(second)


@pytest.mark.unit
def test_duplicate_post_key_changes_with_audience() -> None:
    advisory = _advisory("a", cve_ids=("CVE-2026-0001",))

    assert duplicate_post_key(advisory, audience="general_users") != duplicate_post_key(
        advisory, audience="administrators"
    )


# --- merge / dedup ---------------------------------------------------------


@pytest.mark.unit
def test_merge_advisories_merges_same_cve_from_multiple_sources() -> None:
    kev = _advisory(
        "kev-cve-2026-0001",
        title="KEV entry",
        severity="unknown",
        cve_ids=("CVE-2026-0001",),
        tags=("kev", "known-exploited"),
        references=({"label": "KEV", "url": "https://kev.example/1", "type": "kev"},),
        published_at=datetime(2026, 6, 20, tzinfo=UTC),
    )
    vendor = _advisory(
        "vendor-EX-2026-001",
        title="Vendor advisory",
        severity="high",
        cve_ids=("CVE-2026-0001",),
        vendor_advisory_ids=("EX-2026-001",),
        cvss_score=8.1,
        references=({"label": "Vendor", "url": "https://vendor.example/1", "type": "vendor"},),
        published_at=datetime(2026, 6, 21, tzinfo=UTC),
    )

    merged = merge_advisories([kev, vendor], now=NOW)

    assert len(merged) == 1
    advisory = merged[0]
    assert advisory.advisory_id == "merged-cve-cve-2026-0001"
    assert advisory.severity == "high"  # max severity wins
    assert advisory.cve_ids == ("CVE-2026-0001",)
    assert advisory.vendor_advisory_ids == ("EX-2026-001",)
    assert advisory.title == "Vendor advisory"  # higher-severity primary
    assert advisory.cvss_score == 8.1
    assert {ref["url"] for ref in advisory.references} == {
        "https://kev.example/1",
        "https://vendor.example/1",
    }
    assert "kev" in advisory.tags
    assert advisory.published_at == datetime(2026, 6, 20, tzinfo=UTC)  # earliest
    assert advisory.source_record_id is None  # multiple sources


@pytest.mark.unit
def test_merge_advisories_derives_severity_from_max_cvss_score() -> None:
    vendor = _advisory("vendor", cve_ids=("CVE-2026-0005",), severity="medium")
    nvd = _advisory(
        "nvd",
        cve_ids=("CVE-2026-0005",),
        severity="unknown",
        cvss_score=9.8,
    )

    merged = merge_advisories([vendor, nvd], now=NOW)

    assert len(merged) == 1
    assert merged[0].severity == "critical"
    assert merged[0].cvss_score == 9.8


@pytest.mark.unit
def test_merge_advisories_links_transitively_across_id_types() -> None:
    a = _advisory("a", cve_ids=("CVE-2026-0002",))
    b = _advisory("b", cve_ids=("CVE-2026-0002",), jvn_ids=("JVNVU-99",))
    c = _advisory("c", jvn_ids=("JVNVU-99",), vendor_advisory_ids=("EX-9",))

    merged = merge_advisories([a, b, c], now=NOW)

    assert len(merged) == 1
    assert merged[0].cve_ids == ("CVE-2026-0002",)
    assert merged[0].jvn_ids == ("JVNVU-99",)
    assert merged[0].vendor_advisory_ids == ("EX-9",)


@pytest.mark.unit
def test_merge_advisories_normalizes_identifier_case_in_merged_output() -> None:
    a = _advisory("a", cve_ids=("cve-2026-0004",), vendor_advisory_ids=("ex-4",))
    b = _advisory("b", cve_ids=("CVE-2026-0004",), vendor_advisory_ids=("EX-4",))

    merged = merge_advisories([a, b], now=NOW)

    assert len(merged) == 1
    assert merged[0].cve_ids == ("CVE-2026-0004",)
    assert merged[0].vendor_advisory_ids == ("EX-4",)
    assert merged[0].advisory_id == "merged-cve-cve-2026-0004"


@pytest.mark.unit
def test_merge_advisories_preserves_references_without_url() -> None:
    a = _advisory(
        "a",
        cve_ids=("CVE-2026-0006",),
        references=({"label": "Vendor text", "type": "vendor"},),
    )
    b = _advisory(
        "b",
        cve_ids=("CVE-2026-0006",),
        references=({"label": "RSS text", "type": "rss"},),
    )

    merged = merge_advisories([a, b], now=NOW)

    assert len(merged) == 1
    assert merged[0].references == (
        {"label": "Vendor text", "type": "vendor"},
        {"label": "RSS text", "type": "rss"},
    )


@pytest.mark.unit
def test_merge_advisories_keeps_identity_less_advisories_separate() -> None:
    a = _advisory("a", title="No identifiers one")
    b = _advisory("b", title="No identifiers two")

    merged = merge_advisories([a, b], now=NOW)

    assert {adv.advisory_id for adv in merged} == {"a", "b"}


@pytest.mark.unit
def test_merge_advisories_derives_severity_from_cvss_when_unknown() -> None:
    a = _advisory("a", cve_ids=("CVE-2026-0003",), severity="unknown", cvss_score=9.3)
    b = _advisory("b", cve_ids=("CVE-2026-0003",), severity="unknown")

    merged = merge_advisories([a, b], now=NOW)

    assert len(merged) == 1
    assert merged[0].cve_ids == ("CVE-2026-0003",)
    assert merged[0].severity == "critical"
