"""SharePoint Site Page を作成・publish する最小 Graph クライアント。

Graph リクエスト本文の組み立て（payload → sitePage リソース）と応答パース
（JSON → page ID）は network I/O から分離した純関数にし、単体テスト可能にする。
HTTP は stdlib ``urllib`` で行い、新規 HTTP クライアント依存は足さない。

参考: docs/specs/sharepoint-publishing.md（Site Page / News、最小権限、idempotency）。
"""

from __future__ import annotations

import html
import json
import re
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from .errors import GraphApiError

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
DEFAULT_TIMEOUT_SECONDS = 30
_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
_PAGE_NAME_MAX = 50
_UNSAFE_NAME = re.compile(r'[\\/:*?"<>|#%\s]+')


@dataclass(frozen=True)
class CreatedPage:
    """作成された Site Page の最小情報。"""

    page_id: str
    web_url: str | None = None


@runtime_checkable
class SharePointPagesClient(Protocol):
    """Site Page の作成・publish を抽象化する（実 Graph / テスト fake を差し替え可能）。"""

    def create_site_page(
        self, *, site_id: str, request_body: Mapping[str, Any], access_token: str
    ) -> CreatedPage: ...

    def publish_site_page(self, *, site_id: str, page_id: str, access_token: str) -> None: ...


def page_name_from_title(title: str) -> str:
    """title から SharePoint page 名（``*.aspx``）を作る（純関数）。"""
    slug = _UNSAFE_NAME.sub("-", title.strip()).strip("-")
    slug = slug[:_PAGE_NAME_MAX].strip("-")
    return f"{slug}.aspx" if slug else "spautopost-page.aspx"


def _sections_to_html(sections: Sequence[Mapping[str, Any]]) -> str:
    """dry-run の sections 構造を Site Page 本文 HTML に変換する（純関数）。"""
    blocks: list[str] = []
    for section in sections:
        if not isinstance(section, Mapping):
            continue
        heading = html.escape(str(section.get("heading", "")))
        blocks.append(f"<h2>{heading}</h2>")
        if "body" in section:
            blocks.append(f"<p>{html.escape(str(section['body']))}</p>")
        if "items" in section:
            items_seq = section["items"]
            if isinstance(items_seq, Sequence) and not isinstance(items_seq, str):
                items = "".join(f"<li>{html.escape(str(item))}</li>" for item in items_seq)
                blocks.append(f"<ul>{items}</ul>")
        if "references" in section:
            refs_seq = section["references"]
            if isinstance(refs_seq, Sequence) and not isinstance(refs_seq, str):
                refs = []
                for ref in refs_seq:
                    if not isinstance(ref, Mapping):
                        continue
                    label = html.escape(str(ref.get("label", ref.get("url", ""))))
                    url_str = str(ref.get("url", "")).strip()
                    # javascript: などの非 http(s) スキームを排除する（XSS 防止）。
                    if not url_str.lower().startswith(("https://", "http://")):
                        url_str = ""
                    url = html.escape(url_str)
                    refs.append(f'<li><a href="{url}">{label}</a></li>')
                blocks.append(f"<ul>{''.join(refs)}</ul>")
    return "".join(blocks)


def build_create_page_request(payload: Mapping[str, Any]) -> dict[str, Any]:
    """dry-run の Site Page payload から Graph sitePage 作成リクエスト本文を組み立てる。"""
    title = str(payload.get("title") or "(untitled)")
    sections = payload.get("sections", [])
    inner_html = _sections_to_html(sections if isinstance(sections, Sequence) else [])
    return {
        "@odata.type": "#microsoft.graph.sitePage",
        "name": page_name_from_title(title),
        "title": title,
        "pageLayout": "article",
        "canvasLayout": {
            "horizontalSections": [
                {
                    "layout": "oneColumn",
                    "columns": [
                        {
                            "width": 12,
                            "webparts": [
                                {
                                    "@odata.type": "#microsoft.graph.textWebPart",
                                    "innerHtml": inner_html,
                                }
                            ],
                        }
                    ],
                }
            ]
        },
    }


def parse_page_id(response: Mapping[str, Any]) -> str:
    """Graph の Site Page 作成応答から page ID を取り出す（純関数）。"""
    page_id = response.get("id")
    if not page_id:
        raise GraphApiError("graph response missing page id")
    return str(page_id)


class GraphSharePointPagesClient:
    """``urllib`` で Graph を叩く実クライアント（network 行は no-cover）。"""

    def __init__(
        self, *, base_url: str = GRAPH_BASE_URL, timeout: int = DEFAULT_TIMEOUT_SECONDS
    ) -> None:
        self._base_url = base_url
        self._timeout = timeout

    def create_site_page(  # pragma: no cover - network
        self, *, site_id: str, request_body: Mapping[str, Any], access_token: str
    ) -> CreatedPage:
        url = f"{self._base_url}/sites/{site_id}/pages"
        response = self._post(url, dict(request_body), access_token)
        return CreatedPage(page_id=parse_page_id(response), web_url=response.get("webUrl"))

    def publish_site_page(  # pragma: no cover - network
        self, *, site_id: str, page_id: str, access_token: str
    ) -> None:
        url = f"{self._base_url}/sites/{site_id}/pages/{page_id}/microsoft.graph.sitePage/publish"
        self._post(url, None, access_token)

    def _post(  # pragma: no cover - network
        self, url: str, body: Mapping[str, Any] | None, access_token: str
    ) -> dict[str, Any]:
        data = json.dumps(body).encode("utf-8") if body is not None else b""
        request = urllib.request.Request(  # noqa: S310 - 固定 https Graph endpoint
            url,
            data=data,
            method="POST",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as resp:  # noqa: S310
                raw = resp.read()
        except urllib.error.HTTPError as exc:
            # Secret 漏洩防止のため status のみ記録し、応答本文・token は載せない。
            raise GraphApiError(
                f"graph request failed: HTTP {exc.code}",
                status_code=exc.code,
                retryable=exc.code in _RETRYABLE_STATUS,
            ) from None
        except urllib.error.URLError:
            raise GraphApiError("graph request failed: network error", retryable=True) from None
        return json.loads(raw) if raw else {}
