"""
Web research tools for SANDHYA.AI.

Provides:
  search_web(query)       — DuckDuckGo Lite search (no API key)
  extract_content(url)    — Fetch and extract readable text from any URL

Uses httpx for HTTP and simple text extraction. BeautifulSoup is used
if available; otherwise falls back to regex stripping.
"""

import asyncio
import re
import urllib.parse
from typing import Optional

import httpx

from ..utils.logger import get_logger

logger = get_logger(__name__)

# HTTP settings
_TIMEOUT = 20          # seconds
_MAX_CONTENT = 5000    # chars returned to memory
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/121.0.0.0 Safari/537.36"
)


# ============================================================================
# HTML → plain text helpers
# ============================================================================

def _strip_html(html: str) -> str:
    """
    Convert HTML to readable plain text.
    Uses BeautifulSoup when available, otherwise regex fallback.
    """
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        # Remove scripts, styles, nav
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n")
    except ImportError:
        # Regex fallback
        text = re.sub(r"<[^>]+>", " ", html)

    # Normalise whitespace
    lines = [line.strip() for line in text.splitlines()]
    lines = [l for l in lines if l]
    return "\n".join(lines)


# ============================================================================
# search_web — DuckDuckGo Lite
# ============================================================================

async def search_web(query: str, max_results: int = 8) -> str:
    """
    Search DuckDuckGo Lite and return a list of result titles + URLs.

    No API key required. Uses the public /lite endpoint.

    Returns:
        Newline-separated list of "Title | URL" strings.
    """
    logger.info(f"[Tool:search_web] query={query!r}")

    encoded = urllib.parse.quote_plus(query)
    url = f"https://duckduckgo.com/lite/?q={encoded}&kl=en-us"

    try:
        async with httpx.AsyncClient(
            timeout=_TIMEOUT,
            headers={"User-Agent": _USER_AGENT},
            follow_redirects=True,
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            html = resp.text

        # Parse result links from DuckDuckGo Lite HTML
        results = _parse_ddg_lite(html)

        if not results:
            # Fallback: simple regex extraction of links
            results = _regex_extract_links(html)

        if not results:
            return f"No results found for query: {query!r}"

        lines = [f"{i+1}. {r['title']} | {r['url']}" for i, r in enumerate(results[:max_results])]
        output = f"Search results for '{query}':\n" + "\n".join(lines)
        logger.info(f"[Tool:search_web] Found {len(results)} results")
        return output[:_MAX_CONTENT]

    except httpx.TimeoutException:
        return f"Search timed out for query: {query!r}"
    except Exception as e:
        logger.error(f"[Tool:search_web] Error: {e}")
        return f"Search failed: {e}"


def _parse_ddg_lite(html: str) -> list:
    """Parse DuckDuckGo Lite result rows."""
    results = []
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        # DDG Lite uses class "result-link" for result anchors
        for a in soup.select("a.result-link"):
            title = a.get_text(strip=True)
            href = a.get("href", "")
            if href and title:
                results.append({"title": title, "url": href})
        if not results:
            # Try alternate structure
            for row in soup.select("tr"):
                a_tags = row.select("a[href]")
                for a in a_tags:
                    href = a.get("href", "")
                    title = a.get_text(strip=True)
                    if (
                        href.startswith("http")
                        and title
                        and "duckduckgo" not in href
                        and len(title) > 5
                    ):
                        results.append({"title": title, "url": href})
                        break
    except ImportError:
        pass
    return results


def _regex_extract_links(html: str) -> list:
    """Fallback regex-based link extraction."""
    results = []
    pattern = r'href="(https?://[^"]+)"[^>]*>([^<]{5,80})<'
    for m in re.finditer(pattern, html):
        href, title = m.group(1), m.group(2).strip()
        if "duckduckgo" not in href and title:
            results.append({"title": title, "url": href})
    return results[:10]


# ============================================================================
# extract_content — Fetch and extract text from any URL
# ============================================================================

async def extract_content(url: str) -> str:
    """
    Fetch a URL and extract its readable text content.

    Returns up to _MAX_CONTENT characters of clean text.
    """
    logger.info(f"[Tool:extract_content] url={url!r}")

    if not url.startswith("http"):
        url = "https://" + url

    try:
        async with httpx.AsyncClient(
            timeout=_TIMEOUT,
            headers={"User-Agent": _USER_AGENT},
            follow_redirects=True,
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")

        if "text/html" in content_type or not content_type:
            text = _strip_html(resp.text)
        elif "text/" in content_type:
            text = resp.text
        else:
            return f"Cannot extract content from {url!r}: unsupported type {content_type!r}"

        text = text.strip()
        if not text:
            return f"No readable content found at {url!r}"

        trimmed = text[:_MAX_CONTENT]
        suffix = f"\n[...content continues, {len(text)} total chars]" if len(text) > _MAX_CONTENT else ""
        logger.info(f"[Tool:extract_content] Extracted {len(text)} chars from {url!r}")
        return trimmed + suffix

    except httpx.TimeoutException:
        return f"Request timed out for URL: {url!r}"
    except httpx.HTTPStatusError as e:
        return f"HTTP {e.response.status_code} for URL: {url!r}"
    except Exception as e:
        logger.error(f"[Tool:extract_content] Error: {e}")
        return f"Content extraction failed for {url!r}: {e}"


# ============================================================================
# Registry helper
# ============================================================================

def make_web_tools() -> dict:
    """Return dict of web research tool async functions for ToolRegistry."""
    return {
        "search_web": search_web,
        "extract_content": extract_content,
    }
