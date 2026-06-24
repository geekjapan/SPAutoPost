"""Manual advisory input tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from spautopost.advisory_input import AdvisoryInputError, load_manual_advisory


def test_load_manual_advisory_from_yaml(tmp_path: Path) -> None:
    path = tmp_path / "advisory.yaml"
    path.write_text(
        """
title: Microsoft Exchange Server の脆弱性
summary: 認証済み攻撃者により権限昇格される可能性があります。
cve_ids:
  - CVE-2026-12345
jvn_ids:
  - JVNDB-2026-000123
severity: high
urgency: high
references:
  - label: Vendor advisory
    url: https://example.com/security/update
    type: vendor
tags:
  - exchange
published_at: "2026-06-01T00:00:00Z"
""",
        encoding="utf-8",
    )

    loaded = load_manual_advisory(path, now=datetime(2026, 6, 24, 0, 0, tzinfo=UTC))

    assert loaded.urgency == "high"
    assert loaded.advisory.title == "Microsoft Exchange Server の脆弱性"
    assert loaded.advisory.severity == "high"
    assert loaded.advisory.cve_ids == ("CVE-2026-12345",)
    assert loaded.advisory.jvn_ids == ("JVNDB-2026-000123",)
    assert loaded.advisory.references[0]["url"] == "https://example.com/security/update"


def test_load_manual_advisory_from_json(tmp_path: Path) -> None:
    path = tmp_path / "advisory.json"
    path.write_text(
        """
{
  "title": "Apache Struts advisory",
  "summary": "Remote code execution risk.",
  "severity": "critical",
  "references": [
    {
      "label": "NVD",
      "url": "https://nvd.nist.gov/vuln/detail/CVE-2026-9999",
      "type": "nvd"
    }
  ]
}
""",
        encoding="utf-8",
    )

    loaded = load_manual_advisory(path)

    assert loaded.advisory.title == "Apache Struts advisory"
    assert loaded.advisory.severity == "critical"
    assert loaded.advisory.advisory_id.startswith("manual-")


def test_invalid_manual_advisory_reports_all_basic_issues(tmp_path: Path) -> None:
    path = tmp_path / "invalid.yaml"
    path.write_text(
        """
summary: ""
cve_ids:
  - CVE-26-1
jvn_ids:
  - JVN-123
severity: severe
urgency: now
references:
  - label: bad
    url: ftp://example.com/file
    type: unknown
""",
        encoding="utf-8",
    )

    with pytest.raises(AdvisoryInputError) as excinfo:
        load_manual_advisory(path)

    issues = excinfo.value.issues
    assert "title is required" in issues
    assert "summary is required" in issues
    assert "cve_ids contains invalid CVE ID: CVE-26-1" in issues
    assert "jvn_ids contains invalid JVN ID: JVN-123" in issues
    assert "severity is invalid" in issues
    assert "urgency is invalid" in issues
    assert "references[0].url must be an http(s) URL" in issues
    assert "references[0].type is invalid" in issues
