"""
Self-healing browser singleton for SANDHYA.AI autonomous execution.

Design contract
---------------
* `BrowserSingleton.get_page()` ALWAYS returns a live Playwright `Page`.
* If any layer (browser / context / page) is missing or closed it is
  transparently recreated before the caller receives control.
* `reset_browser()` performs a full teardown + cold restart — useful after
  crash errors like "Target page, context or browser has been closed".
* All state is protected by `asyncio.Lock` so concurrent tool calls are safe.

Stale-error strings that trigger automatic recovery in the executor are
exported as `STALE_BROWSER_ERRORS`.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    Playwright,
)

logger = logging.getLogger(__name__)

# ── error substrings that indicate a dead browser session ──────────────────
STALE_BROWSER_ERRORS: tuple[str, ...] = (
    "target page, context or browser has been closed",
    "execution context was destroyed",
    "browser has been closed",
    "context or browser has been closed",
    "page has been closed",
    "target closed",
    "connection is closed",
    "session closed",
)


def _is_stale_error(exc: BaseException) -> bool:
    """Return True when *exc* signals a dead Playwright session."""
    msg = str(exc).lower()
    return any(pattern in msg for pattern in STALE_BROWSER_ERRORS)


class BrowserSingleton:
    """
    Universal, self-healing Playwright browser singleton.

    Usage::

        page = await BrowserSingleton.get_page()
        await page.goto("https://example.com")
    """

    _instance: Optional["BrowserSingleton"] = None

    # ── construction ──────────────────────────────────────────────────────

    def __init__(self) -> None:
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._lock = asyncio.Lock()

    # ── singleton accessor ────────────────────────────────────────────────

    @classmethod
    def get(cls) -> "BrowserSingleton":
        """Return the process-level singleton (creates it if needed)."""
        if cls._instance is None:
            cls._instance = BrowserSingleton()
        return cls._instance

    # ── public API ────────────────────────────────────────────────────────

    async def get_page(self) -> Page:
        """
        Return a guaranteed live Page.

        Transparent healing order:
          1. If browser is missing/closed  → cold-start Playwright + browser
          2. If context is missing/closed  → create a new BrowserContext
          3. If page is missing/closed     → open a new Page

        Thread-safe: protected by asyncio.Lock.
        """
        async with self._lock:
            await self._ensure_browser()
            await self._ensure_context()
            await self._ensure_page()
            return self._page  # type: ignore[return-value]

    async def reset_browser(self) -> None:
        """
        Forcefully tear down everything and perform a cold restart.

        Call this after catching a stale-browser error so the next
        `get_page()` starts with a completely fresh session.
        """
        async with self._lock:
            logger.warning("[BrowserSingleton] Resetting browser (full teardown)...")
            await self._teardown_unsafe()
            await self._cold_start()
            logger.info("[BrowserSingleton] Browser successfully reset")

    async def stop(self) -> None:
        """Gracefully close the browser at server shutdown."""
        async with self._lock:
            await self._teardown_unsafe()
            logger.info("[BrowserSingleton] Browser stopped (server shutdown)")

    @property
    def is_ready(self) -> bool:
        """True when a live browser + page exist (no page.is_closed check)."""
        return (
            self._browser is not None
            and self._page is not None
            and not self._page.is_closed()
        )

    # ── private helpers ───────────────────────────────────────────────────

    async def _ensure_browser(self) -> None:
        """Launch Playwright + browser if not alive."""
        browser_alive = (
            self._browser is not None
            and self._playwright is not None
        )
        if browser_alive:
            return

        logger.info("[BrowserSingleton] Launching browser...")
        await self._cold_start()

    async def _ensure_context(self) -> None:
        """Create a new BrowserContext if the current one is gone."""
        if self._context is not None:
            try:
                # accessing .pages is cheap and raises if context is dead
                _ = self._context.pages
                return
            except Exception:
                logger.warning("[BrowserSingleton] Context stale — recreating")
                self._context = None
                self._page = None

        self._context = await self._browser.new_context(  # type: ignore[union-attr]
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/121.0.0.0 Safari/537.36"
            ),
        )
        logger.info("[BrowserSingleton] New BrowserContext created")

    async def _ensure_page(self) -> None:
        """Open a new Page if the current one is closed or missing."""
        if self._page is not None and not self._page.is_closed():
            return

        logger.info("[BrowserSingleton] Opening new page...")
        self._page = await self._context.new_page()  # type: ignore[union-attr]
        logger.info("[BrowserSingleton] New Page created and ready")

    async def _cold_start(self) -> None:
        """
        Start Playwright, launch browser, create context + page.
        MUST be called while holding self._lock.
        """
        self._playwright = await async_playwright().start()

        # Try real Chrome first; fall back to bundled Chromium
        try:
            self._browser = await self._playwright.chromium.launch(
                channel="chrome",
                headless=False,
                args=["--start-maximized"],
            )
            logger.info("[BrowserSingleton] Launched real Chrome (channel=chrome)")
        except Exception as chrome_err:
            logger.warning(
                f"[BrowserSingleton] Real Chrome unavailable ({chrome_err}), "
                "falling back to bundled Chromium"
            )
            self._browser = await self._playwright.chromium.launch(
                headless=False,
                args=["--start-maximized"],
            )
            logger.info("[BrowserSingleton] Launched bundled Chromium (fallback)")

        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/121.0.0.0 Safari/537.36"
            ),
        )
        self._page = await self._context.new_page()
        logger.info("[BrowserSingleton] Cold start complete — browser ready")

    async def _teardown_unsafe(self) -> None:
        """
        Best-effort teardown with NO lock (caller must hold the lock).
        Swallows all errors so reset/stop never raises.
        """
        for obj, name in [
            (self._page, "page"),
            (self._context, "context"),
            (self._browser, "browser"),
            (self._playwright, "playwright"),
        ]:
            if obj is not None:
                try:
                    await obj.close()
                except Exception as exc:
                    logger.debug(f"[BrowserSingleton] {name} close error (ignored): {exc}")

        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None
