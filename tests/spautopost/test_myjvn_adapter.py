"""MyJVN adapter unit/fixture tests. No live network access."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta, timezone

import pytest

from spautopost.myjvn_adapter import (
    MyjvnAdapterError,
    MyjvnHttpResponse,
    MyjvnSourceAdapter,
    urllib_transport,
)
from spautopost.source_adapters import SourceFetchQuery

NOW = datetime(2026, 6, 24, 12, 0, tzinfo=UTC)
JST = timezone(timedelta(hours=9))


OVERVIEW_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rdf:RDF
  xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:dcterms="http://purl.org/dc/terms/"
  xmlns:sec="http://jvn.jp/rss/mod_sec/"
  xmlns:status="http://jvndb.jvn.jp/myjvn/Status">
  <item rdf:about="https://jvndb.jvn.jp/ja/contents/2026/JVNDB-2026-000001.html">
    <title>サンプル製品における権限昇格の脆弱性</title>
    <link>https://jvndb.jvn.jp/ja/contents/2026/JVNDB-2026-000001.html</link>
    <description>サンプル製品には権限昇格の脆弱性があります。</description>
    <dcterms:issued>2026-06-20T09:00:00+09:00</dcterms:issued>
    <dc:date>2026-06-22T10:30:00+09:00</dc:date>
    <sec:identifier>JVNDB-2026-000001</sec:identifier>
    <sec:references source="CVE" id="CVE-2026-0001" title="CVE-2026-0001">
      https://www.cve.org/CVERecord?id=CVE-2026-0001
    </sec:references>
    <sec:cvss version="3.1" score="8.8" severity="High"
      vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H" />
    <sec:cpe vendor="Example Vendor" product="Example Product" />
  </item>
  <status:Status retCd="0" totalRes="1" firstItem="1" maxCount="50" />
</rdf:RDF>
"""

DETAIL_XML = """<?xml version="1.0" encoding="UTF-8"?>
<VULDEF-Document>
  <Vulinfo>
    <VulinfoID>JVNDB-2026-000001</VulinfoID>
    <Title>サンプル製品における権限昇格の脆弱性</Title>
    <Overview>
      <OverviewItem>
        <Description>サンプル製品には権限昇格の脆弱性があります。</Description>
      </OverviewItem>
    </Overview>
    <Solution>
      <SolutionItem>
        <Description>最新版へアップデートしてください。</Description>
      </SolutionItem>
    </Solution>
    <Related>
      <RelatedItem type="CVE" id="CVE-2026-0001" title="CVE-2026-0001">
        <URL>https://www.cve.org/CVERecord?id=CVE-2026-0001</URL>
      </RelatedItem>
    </Related>
    <Cvss>
      <CvssItem version="3.1" score="8.8" severity="High"
        vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H" />
    </Cvss>
    <DateFirstPublished>2026-06-20T09:00:00+09:00</DateFirstPublished>
    <DateLastUpdated>2026-06-22T10:30:00+09:00</DateLastUpdated>
  </Vulinfo>
  <Status retCd="0" totalRes="1" firstItem="1" maxCount="10" />
</VULDEF-Document>
"""


class RecordingTransport:
    def __init__(self, responses: Sequence[MyjvnHttpResponse]) -> None:
        self._responses = list(responses)
        self.urls: list[str] = []
        self.headers: list[Mapping[str, str]] = []

    def __call__(self, url: str, headers: Mapping[str, str]) -> MyjvnHttpResponse:
        self.urls.append(url)
        self.headers.append(dict(headers))
        return self._responses[min(len(self.urls) - 1, len(self._responses) - 1)]


def test_overview_fetch_builds_source_record_and_advisory() -> None:
    transport = RecordingTransport([MyjvnHttpResponse(status=200, body=OVERVIEW_XML)])
    adapter = MyjvnSourceAdapter(transport=transport)

    documents = adapter.fetch(
        SourceFetchQuery(
            modified_from=datetime(2026, 6, 1, tzinfo=UTC),
            modified_to=datetime(2026, 6, 24, tzinfo=UTC),
        ),
        now=NOW,
    )
    advisory = adapter.normalize(documents[0], now=NOW)[0]

    assert adapter.validate_config().ok
    assert "method=getVulnOverviewList" in transport.urls[0]
    assert "datePublishedStartY=2026" in transport.urls[0]
    assert transport.headers[0] == {}
    record = documents[0].source_record
    assert record.source_type == "myjvn"
    assert record.source_url == "https://jvndb.jvn.jp/ja/contents/2026/JVNDB-2026-000001.html"
    assert record.retrieved_at == NOW
    assert record.raw_hash
    assert advisory.advisory_id == "myjvn-jvndb-2026-000001"
    assert advisory.jvn_ids == ("JVNDB-2026-000001",)
    assert advisory.cve_ids == ("CVE-2026-0001",)
    assert advisory.title == "サンプル製品における権限昇格の脆弱性"
    assert advisory.summary == "サンプル製品には権限昇格の脆弱性があります。"
    assert advisory.published_at == datetime(2026, 6, 20, 9, 0, tzinfo=JST).astimezone(UTC)
    assert advisory.updated_at == datetime(2026, 6, 22, 10, 30, tzinfo=JST).astimezone(UTC)
    assert advisory.cvss_version == "3.1"
    assert advisory.cvss_score == 8.8
    assert advisory.severity == "high"
    assert "vendor:Example Vendor" in advisory.tags
    assert "product:Example Product" in advisory.tags
    assert advisory.references[0]["type"] == "jvn"


def test_detail_fetch_preserves_japanese_mitigation() -> None:
    transport = RecordingTransport([MyjvnHttpResponse(status=200, body=DETAIL_XML)])
    adapter = MyjvnSourceAdapter(transport=transport)

    document = adapter.fetch_detail(["JVNDB-2026-000001"], now=NOW)[0]
    advisory = adapter.normalize(document, now=NOW)[0]

    assert "method=getVulnDetailInfo" in transport.urls[0]
    assert "vulnId=JVNDB-2026-000001" in transport.urls[0]
    assert advisory.jvn_ids == ("JVNDB-2026-000001",)
    assert advisory.cve_ids == ("CVE-2026-0001",)
    assert "サンプル製品には権限昇格の脆弱性があります。" in advisory.summary
    assert "対策: 最新版へアップデートしてください。" in advisory.summary


def test_myjvn_status_error_raises() -> None:
    xml = (
        '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" '
        'xmlns:status="http://jvndb.jvn.jp/myjvn/Status">'
        '<status:Status retCd="1" errCd="ERR" errMsg="bad request" /></rdf:RDF>'
    )
    transport = RecordingTransport([MyjvnHttpResponse(status=200, body=xml)])
    adapter = MyjvnSourceAdapter(transport=transport)

    with pytest.raises(MyjvnAdapterError, match="bad request"):
        adapter.fetch(now=NOW)


def test_empty_detail_request_is_rejected_without_transport_call() -> None:
    transport = RecordingTransport([MyjvnHttpResponse(status=200, body=DETAIL_XML)])
    adapter = MyjvnSourceAdapter(transport=transport)

    with pytest.raises(MyjvnAdapterError, match="at least one JVN ID"):
        adapter.fetch_detail([], now=NOW)
    assert transport.urls == []


def test_urllib_transport_rejects_non_https_url() -> None:
    with pytest.raises(MyjvnAdapterError, match="https"):
        urllib_transport("http://jvndb.jvn.jp/myjvn", {})
