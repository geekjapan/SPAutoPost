"""Firecrawl source adapter spike script.

Usage:
    FIRECRAWL_API_KEY=fc-... python samples/firecrawl_spike.py <url>

Examples:
    python samples/firecrawl_spike.py https://nvd.nist.gov/vuln/detail/CVE-2024-0001
    python samples/firecrawl_spike.py https://jvn.jp/en/jp/JVN12345678/

This script evaluates Firecrawl as a source adapter for SPAutoPost.
It scrapes the given URL, displays the result, and maps it to an Advisory.
"""

from __future__ import annotations

import hashlib
import os
import sys
from datetime import UTC, datetime

MAX_CONTENT_CHARS = int(os.environ.get("FIRECRAWL_MAX_CONTENT_CHARS", "5000"))
TIMEOUT_MS = int(os.environ.get("FIRECRAWL_TIMEOUT_SECONDS", "30")) * 1000


def main() -> None:
    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if not api_key:
        print("[ERROR] FIRECRAWL_API_KEY is not set.", file=sys.stderr)
        print("  Set it: export FIRECRAWL_API_KEY=fc-your-key", file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <url>", file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1]
    print(f"[spike] Scraping: {url}")
    print(f"[spike] Timeout: {TIMEOUT_MS}ms, Max content: {MAX_CONTENT_CHARS} chars\n")

    try:
        from firecrawl import V1FirecrawlApp
    except ImportError:
        print("[ERROR] firecrawl-py is not installed.", file=sys.stderr)
        print("  Install: pip install 'firecrawl-py>=4.0'", file=sys.stderr)
        sys.exit(1)

    app = V1FirecrawlApp(api_key=api_key)

    # --- Fetch ---
    try:
        result = app.scrape_url(url, formats=["markdown"], timeout=TIMEOUT_MS)
    except Exception as exc:
        print(f"[ERROR] scrape_url failed: {exc}", file=sys.stderr)
        sys.exit(1)

    markdown: str = result.markdown or ""
    metadata: dict = result.metadata or {}
    title: str = result.title or metadata.get("title") or url
    source_url: str = metadata.get("sourceURL") or url
    status_code: int = metadata.get("statusCode") or 200

    print("=== Firecrawl Response ===")
    print(f"title      : {title}")
    print(f"source_url : {source_url}")
    print(f"status_code: {status_code}")
    print(f"markdown chars: {len(markdown)}")
    print(f"\n--- Markdown (first {MAX_CONTENT_CHARS} chars) ---")
    print(markdown[:MAX_CONTENT_CHARS])
    print()

    # --- Advisory mapping ---
    now = datetime.now(UTC)
    summary = markdown[:MAX_CONTENT_CHARS].strip() or title
    advisory = {
        "advisory_id": (
            f"web-scrape-{int(hashlib.sha256(source_url.encode()).hexdigest(), 16) % 10**8:08d}"
        ),
        "title": title,
        "summary": summary,
        "severity": "unknown",
        "source_url": source_url,
        "references": [{"label": "Source", "url": source_url, "type": "web_scrape"}],
        "tags": ("firecrawl", "web_scrape"),
        "normalized_at": now.isoformat(),
    }

    print("=== Advisory (mapped) ===")
    for k, v in advisory.items():
        display = v if not isinstance(v, str) or len(v) <= 80 else v[:80] + "..."
        print(f"  {k}: {display}")

    print("\n[spike] Done.")


if __name__ == "__main__":
    main()
