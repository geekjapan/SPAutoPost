"""Graph リクエストビルダ・応答パースの純関数テスト（network 非依存）。"""

from __future__ import annotations

from typing import Any

import pytest

from spautopost.graph.errors import GraphApiError
from spautopost.graph.sharepoint_client import (
    build_create_page_request,
    page_name_from_title,
    parse_page_id,
)


def _inner_html(request: dict[str, Any]) -> str:
    section = request["canvasLayout"]["horizontalSections"][0]
    return section["columns"][0]["webparts"][0]["innerHtml"]


def test_build_create_page_request_maps_title_and_sections() -> None:
    payload = {
        "title": "件名タイトル",
        "sections": [
            {"heading": "概要", "body": "本文サマリ"},
            {"heading": "利用者が行う対応", "items": ["A を実施", "B を実施"]},
            {"heading": "参考情報", "references": [{"label": "Vendor", "url": "https://e.com"}]},
        ],
    }

    request = build_create_page_request(payload)

    assert request["@odata.type"] == "#microsoft.graph.sitePage"
    assert request["title"] == "件名タイトル"
    assert request["name"].endswith(".aspx")
    html = _inner_html(request)
    assert "<h2>概要</h2>" in html
    assert "本文サマリ" in html
    assert "<li>A を実施</li>" in html
    assert 'href="https://e.com"' in html


def test_build_create_page_request_escapes_html() -> None:
    payload = {"title": "t", "sections": [{"heading": "h", "body": "<script>x</script>"}]}

    html = _inner_html(build_create_page_request(payload))

    assert "<script>x</script>" not in html
    assert "&lt;script&gt;" in html


def test_build_create_page_request_defaults_untitled() -> None:
    request = build_create_page_request({"sections": []})
    assert request["title"] == "(untitled)"
    assert request["name"] == "(untitled).aspx"


@pytest.mark.parametrize(
    "title,expected",
    [
        ("Simple Title", "Simple-Title.aspx"),
        ("a/b:c*?", "a-b-c.aspx"),
        ("   ", "spautopost-page.aspx"),
    ],
)
def test_page_name_from_title(title: str, expected: str) -> None:
    assert page_name_from_title(title) == expected


def test_parse_page_id_returns_id() -> None:
    assert parse_page_id({"id": "page-7", "webUrl": "https://x"}) == "page-7"


def test_parse_page_id_raises_when_missing() -> None:
    with pytest.raises(GraphApiError):
        parse_page_id({"webUrl": "https://x"})


def test_build_create_page_request_strips_javascript_url() -> None:
    payload = {
        "title": "t",
        "sections": [
            {
                "heading": "refs",
                "references": [{"label": "XSS", "url": "javascript:alert(1)"}],
            }
        ],
    }

    html = _inner_html(build_create_page_request(payload))

    assert "javascript:" not in html
    assert 'href=""' in html
