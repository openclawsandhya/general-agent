"""
BrowserSessionManager — Universal Persistent Browser Session for SANDHYA.AI
============================================================================

This module is the canonical entry point for all browser session operations
across the entire SANDHYA.AI execution core.

Architecture
------------
  session_manager.py          ← this file (integration façade)
      └── tools/browser_singleton.py  (core Playwright lifecycle)
              └── Playwright Chromium / Chrome

Why a separate module
---------------------
  - tools/browser_singleton.py owns the raw Playwright lifecycle
  - session_manager.py owns the *session* abstraction:
      • health statistics (calls made, errors seen, resets triggered)
      • convenience helpers used by orchestrator / executor
      • single import point so nothing else needs to know about the
        internal tools/ package layout

Execution guarantees enforced here
-----------------------------------
  1. get_page()        → ALWAYS returns a live Playwright Page
  2. ensure()         → Lightweight pre-action guard (idempotent)
  3. reset()          → Full teardown + cold restart on crash
  4. Stale-error APIs → _is_stale_error() and STALE_BROWSER_ERRORS
                        re-exported so callers need only one import
"""

from __future__ import annotations

import logging
from typing import Optional

from playwright.async_api import Page

# Re-export stale-error helpers so other modules (executor, tools) can
# do `from .session_manager import _is_stale_error` and nothing else.
from .tools.browser_singleton import (
    BrowserSingleton as _CoreSingleton,
    _is_stale_error,
    STALE_BROWSER_ERRORS,
)

logger = logging.getLogger(__name__)

__all__ = [
    "BrowserSessionManager",
    "get_session",
    "_is_stale_error",
    "STALE_BROWSER_ERRORS",
]


# ============================================================================
# BrowserSessionManager
# ============================================================================

class BrowserSessionManager:
    """
    Universal, self-healing browser session.

    Wraps BrowserSingleton (raw Playwright lifecycle) and adds:
      - Session-level health statistics
      - Structured logging with session context
      - Convenience API used by orchestrator / executor / tools

    Usage::

        session = BrowserSessionManager.get()
        page = await session.get_page()
        await page.goto("https://example.com")

    All browser tools should call ``get_page()`` at the start of every
    action — NEVER store the returned Page in instance/module state.
    """

    _instance: Optional["BrowserSessionManager"] = None

    # ── construction ─────────────────────────────────────────────────────

    def __init__(self) -> None:
        self._core = _CoreSingleton.get()
        self._stats: dict = {
            "total_calls": 0,
            "errors": 0,
            "resets": 0,
        }

    # ── singleton accessor ────────────────────────────────────────────────

    @classmethod
    def get(cls) -> "BrowserSessionManager":
        """Return the process-level singleton (lazy construction)."""
        if cls._instance is None:
            cls._instance = BrowserSessionManager()
        return cls._instance

    # ── primary API (used by browser tools) ──────────────────────────────

    async def get_page(self) -> Page:
        """
        Return a guaranteed live Playwright Page.

        Transparently recreates any dead layer (browser / context / page)
        before returning.  Thread-safe, idempotent.
        """
        self._stats["total_calls"] += 1
        try:
            page = await self._core.get_page()
            logger.debug(
                f"[BrowserSession] get_page() → alive "
                f"(total_calls={self._stats['total_calls']})"
            )
            return page
        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"[BrowserSession] get_page() failed: {e}")
            raise

    async def ensure(self) -> None:
        """
        Pre-action guard: verify browser is live.

        Lighter than get_page() — only ensures the session exists,
        does not return the page object.  Call this in tools that
        need an early-exit check before performing multi-step actions.
        """
        await self._core.get_page()

    async def reset(self) -> None:
        """
        Full teardown + cold restart of the browser.

        Call this after catching a stale-browser error so the next
        get_page() starts with a completely fresh Playwright session.
        """
        self._stats["resets"] += 1
        logger.warning(
            f"[BrowserSession] Resetting session "
            f"(resets={self._stats['resets']})"
        )
        await self._core.reset_browser()
        logger.info("[BrowserSession] Session reset complete — browser ready")

    async def stop(self) -> None:
        """Gracefully close the browser at server shutdown."""
        logger.info("[BrowserSession] Stopping browser (server shutdown)")
        await self._core.stop()

    # ── health ────────────────────────────────────────────────────────────

    @property
    def is_ready(self) -> bool:
        """True when a live browser + page are available."""
        return self._core.is_ready

    @property
    def stats(self) -> dict:
        """Session health statistics (read-only snapshot)."""
        return dict(self._stats)

    # ── context manager support ───────────────────────────────────────────

    async def __aenter__(self) -> "BrowserSessionManager":
        await self.ensure()
        return self

    async def __aexit__(self, *_) -> None:
        # Session is persistent — do NOT close here; only stop() closes it.
        pass


# ============================================================================
# Module-level convenience accessor
# ============================================================================

def get_session() -> BrowserSessionManager:
    """
    Module-level shorthand for ``BrowserSessionManager.get()``.

    Preferred import for browser tools::

        from ..session_manager import get_session

        async def open_url(url: str):
            page = await get_session().get_page()
            await page.goto(url, ...)
    """
    return BrowserSessionManager.get()
