"""
Browser automation tools for SANDHYA.AI.

Every tool calls `BrowserSingleton.get_page()` before each action.
This guarantees a live page on every call  the singleton transparently
heals itself if the browser, context, or page was closed or crashed.

No tool stores `page` as instance state. No tool assumes the browser
is already running. Universal reliability for ANY website.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from ..session_manager import get_session, BrowserSessionManager
# Re-export BrowserSingleton name so api_server.py import stays unchanged
BrowserSingleton = BrowserSessionManager
from ..utils.logger import get_logger

logger = get_logger(__name__)


__all__ = [
    "BrowserSessionManager",
    "BrowserSingleton",   # backward-compat alias
    "make_browser_tools",
    "open_url",
    "click",
    "type",
    "scroll",
    "wait",
    "extract_content",
    "screenshot",
    "press_key",
    "get_page_info",
    "success",
    "failure",
]


# ============================================================================
# Standardised result helpers
# ============================================================================

def success(data: Any = None) -> Dict[str, Any]:
    return {"status": "success", "data": data, "error": None}


def failure(msg: str) -> Dict[str, Any]:
    return {"status": "error", "data": None, "error": str(msg)}


# -- shorthand: always resolves through BrowserSessionManager ----------------
_singleton = get_session


# ============================================================================
# Tool implementations
# ============================================================================

async def open_url(url: str) -> Dict[str, Any]:
    """Navigate to *url* and wait for DOM content to be ready."""
    logger.info(f"[Tool:open_url] -> {url}")
    try:
        page = await _singleton().get_page()  # guaranteed live page
        await page.goto(url, timeout=60_000, wait_until="domcontentloaded")
        title = await page.title()
        current_url = page.url
        logger.info(f"[Tool:open_url] OK | title={title!r}")
        return success({"url": current_url, "title": title})
    except Exception as e:
        logger.error(f"[Tool:open_url] FAILED | url={url} | error={e}")
        return failure(str(e))


async def click(selector: str) -> Dict[str, Any]:
    """
    Click the element matching *selector*.
    Falls back to visible-text lookup when CSS selector fails.
    """
    logger.info(f"[Tool:click] selector={selector!r}")
    try:
        page = await _singleton().get_page()
        try:
            await page.click(selector, timeout=15_000)
        except Exception:
            # Fallback: treat selector as visible text
            await page.get_by_text(selector).first.click(timeout=15_000)
        logger.info(f"[Tool:click] OK | selector={selector!r}")
        return success({"selector": selector})
    except Exception as e:
        logger.error(f"[Tool:click] FAILED | selector={selector!r} | error={e}")
        return failure(str(e))


async def type(selector: str, text: str) -> Dict[str, Any]:
    """
    Fill *text* into the element matching *selector*.
    Clears existing content first; tries fill() then type() as fallback.
    """
    logger.info(f"[Tool:type] selector={selector!r} text={text[:40]!r}")
    try:
        page = await _singleton().get_page()
        try:
            await page.fill(selector, text, timeout=15_000)
        except Exception:
            await page.focus(selector, timeout=15_000)
            await page.keyboard.type(text)
        logger.info(f"[Tool:type] OK | selector={selector!r}")
        return success({"selector": selector, "text": text})
    except Exception as e:
        logger.error(f"[Tool:type] FAILED | selector={selector!r} | error={e}")
        return failure(str(e))


async def press_key(key: str) -> Dict[str, Any]:
    """
    Press a keyboard key (e.g. 'Enter', 'Escape', 'Tab').
    Useful for submitting search boxes after typing.
    """
    logger.info(f"[Tool:press_key] key={key!r}")
    try:
        page = await _singleton().get_page()
        await page.keyboard.press(key)
        logger.info(f"[Tool:press_key] OK | key={key!r}")
        return success({"key": key})
    except Exception as e:
        logger.error(f"[Tool:press_key] FAILED | key={key!r} | error={e}")
        return failure(str(e))


async def scroll(direction: str = "down", amount: int = 3) -> Dict[str, Any]:
    """Scroll the page *amount* viewport-heights in *direction* ('up'/'down')."""
    logger.info(f"[Tool:scroll] direction={direction} amount={amount}")
    try:
        page = await _singleton().get_page()
        px = amount * 600
        delta = px if direction == "down" else -px
        await page.evaluate(f"window.scrollBy(0, {delta})")
        logger.info(f"[Tool:scroll] OK | delta_px={delta}")
        return success({"direction": direction, "pixels": delta})
    except Exception as e:
        logger.error(f"[Tool:scroll] FAILED | error={e}")
        return failure(str(e))


async def wait(ms: int = 1000) -> Dict[str, Any]:
    """Pause execution for *ms* milliseconds."""
    logger.info(f"[Tool:wait] ms={ms}")
    try:
        page = await _singleton().get_page()
        await page.wait_for_timeout(ms)
        return success({"waited_ms": ms})
    except Exception as e:
        logger.error(f"[Tool:wait] FAILED | error={e}")
        return failure(str(e))


async def extract_content(url: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract visible text from the current page.
    Navigates to *url* first when provided.
    """
    if url:
        nav = await open_url(url)
        if nav["status"] == "error":
            return nav

    logger.info("[Tool:extract_content] Extracting page text")
    try:
        page = await _singleton().get_page()
        text = await page.inner_text("body")
        trimmed = text.strip()[:4000]
        logger.info(f"[Tool:extract_content] OK | chars={len(trimmed)}")
        return success({"text": trimmed, "chars": len(trimmed)})
    except Exception as e:
        logger.error(f"[Tool:extract_content] FAILED | error={e}")
        return failure(str(e))


async def get_page_info() -> Dict[str, Any]:
    """Return current page URL and title -- useful for validation steps."""
    logger.info("[Tool:get_page_info]")
    try:
        page = await _singleton().get_page()
        return success({"url": page.url, "title": await page.title()})
    except Exception as e:
        logger.error(f"[Tool:get_page_info] FAILED | error={e}")
        return failure(str(e))


async def screenshot(path: str = "output/screenshot.png") -> Dict[str, Any]:
    """Capture a full-page screenshot and save to *path*."""
    logger.info(f"[Tool:screenshot] path={path!r}")
    try:
        page = await _singleton().get_page()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        await page.screenshot(path=path, full_page=True)
        logger.info(f"[Tool:screenshot] OK | path={path!r}")
        return success({"path": path})
    except Exception as e:
        logger.error(f"[Tool:screenshot] FAILED | error={e}")
        return failure(str(e))


# ============================================================================
# Registry helper
# ============================================================================

def make_browser_tools(browser=None) -> dict:
    """
    Return all browser tool functions for ToolRegistry registration.
    The legacy *browser* parameter is accepted but ignored.
    """
    return {
        "open_url":        open_url,
        "click":           click,
        "type":            type,
        "press_key":       press_key,
        "scroll":          scroll,
        "wait":            wait,
        "extract_content": extract_content,
        "get_page_info":   get_page_info,
        "screenshot":      screenshot,
    }
