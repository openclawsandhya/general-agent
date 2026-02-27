"""
Browser controller using Playwright for automation.
"""

from typing import Optional, List, Callable, Any
from pathlib import Path
import asyncio

from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    TimeoutError as PlaywrightTimeoutError,
)

from .utils.logger import get_logger


logger = get_logger(__name__)


class BrowserController:
    """Controls browser automation using Playwright."""
    
    def __init__(
        self,
        headless: bool = True,
        timeout_ms: int = 30000,
    ):
        """
        Initialize browser controller.
        
        Args:
            headless: Run browser in headless mode
            timeout_ms: Default timeout for operations in milliseconds
        """
        self.headless = headless
        self.timeout_ms = timeout_ms
        self.page: Optional[Page] = None
        self.context: Optional[BrowserContext] = None
        self.browser: Optional[Browser] = None
        self._playwright = None

        logger.info(f"BrowserController initialized (headless={headless})")
    
    async def start(self) -> None:
        """Start the browser."""
        try:
            self._playwright = await async_playwright().start()
            self.browser = await self._playwright.chromium.launch(
                headless=self.headless,
                args=["--start-maximized"],
            )
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()
            self.page.set_default_timeout(self.timeout_ms)

            logger.info(f"Browser started (headless={self.headless})")
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the browser."""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self._playwright:
                await self._playwright.stop()
                self._playwright = None
            self.page = None
            self.context = None
            self.browser = None

            logger.info("Browser stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping browser: {e}")
    
    async def ensure_started(self) -> None:
        """Lazily start browser on first use — singleton, reused across all requests."""
        if self.page is None:
            logger.info("[BrowserController] Auto-starting browser (lazy init)...")
            await self.start()

    async def open_url(self, url: str) -> str:
        """
        Open a URL in the browser.
        
        Args:
            url: URL to open
            
        Returns:
            Success message
        """
        await self.ensure_started()
        
        try:
            if not url.startswith(("http://", "https://")):
                url = f"https://{url}"
            
            logger.info(f"Opening URL: {url}")
            await self.page.goto(url, wait_until="domcontentloaded")
            
            return f"Successfully opened {url}"
        except PlaywrightTimeoutError:
            logger.error(f"Timeout opening URL: {url}")
            raise
        except Exception as e:
            logger.error(f"Failed to open URL: {e}")
            raise
    
    async def search(self, query: str, search_engine: str = "google") -> str:
        """
        Perform a search on a search engine.
        
        Args:
            query: Search query
            search_engine: Search engine to use (default: google)
            
        Returns:
            Success message
        """
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")
        
        try:
            logger.info(f"Searching for: {query}")
            
            # Navigate to search engine
            if search_engine.lower() == "google":
                await self.open_url("https://www.google.com")
                search_box_selector = 'input[aria-label="Search"]'
            elif search_engine.lower() == "bing":
                await self.open_url("https://www.bing.com")
                search_box_selector = 'input[aria-label="Enter your search here"]'
            else:
                raise ValueError(f"Unsupported search engine: {search_engine}")
            
            # Fill search box
            await self.page.fill(search_box_selector, query)
            
            # Press enter
            await self.page.press(search_box_selector, "Enter")
            
            # Wait for results
            await self.page.wait_for_load_state("networkidle")
            
            return f"Successfully searched for '{query}' on {search_engine}"
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    async def click(self, selector: str) -> str:
        """
        Click an element.
        
        Args:
            selector: CSS selector for the element
            
        Returns:
            Success message
        """
        await self.ensure_started()
        
        try:
            logger.info(f"Clicking element: {selector}")
            
            # Wait for element to be visible
            await self.page.wait_for_selector(selector, state="visible")
            await self.page.click(selector)
            
            # Wait for navigation/load
            await self.page.wait_for_load_state("networkidle")
            
            return f"Successfully clicked element: {selector}"
        except PlaywrightTimeoutError:
            logger.error(f"Element not found or timeout: {selector}")
            raise
        except Exception as e:
            logger.error(f"Click failed: {e}")
            raise
    
    async def click_first_result(self) -> str:
        """Click the first search result."""
        try:
            # Common selectors for first result
            selectors = [
                "div[data-sokoban-container] a.YmvwI",  # Google search result
                "a[data-rank='1']",  # Generic result link
                "a.result",  # Bing result
            ]
            
            for selector in selectors:
                try:
                    await self.page.wait_for_selector(selector, state="visible", timeout=2000)
                    await self.click(selector)
                    return "Successfully clicked first result"
                except:
                    continue
            
            raise RuntimeError("Could not find first result link")
        except Exception as e:
            logger.error(f"Failed to click first result: {e}")
            raise
    
    async def scroll(self, direction: str = "down", amount: int = 3) -> str:
        """
        Scroll the page.
        
        Args:
            direction: "up" or "down"
            amount: Number of times to scroll
            
        Returns:
            Success message
        """
        await self.ensure_started()
        
        try:
            logger.info(f"Scrolling {direction} {amount} times")
            
            for _ in range(amount):
                if direction.lower() == "down":
                    await self.page.evaluate(
                        "window.scrollBy(0, window.innerHeight)"
                    )
                else:
                    await self.page.evaluate(
                        "window.scrollBy(0, -window.innerHeight)"
                    )
                await asyncio.sleep(0.5)
            
            return f"Successfully scrolled {direction}"
        except Exception as e:
            logger.error(f"Scroll failed: {e}")
            raise
    
    async def extract_text(self, selector: Optional[str] = None) -> str:
        """
        Extract text content from the page or a specific element.
        
        Args:
            selector: Optional CSS selector to extract from specific element
            
        Returns:
            Extracted text
        """
        await self.ensure_started()
        
        try:
            if selector:
                logger.info(f"Extracting text from: {selector}")
                await self.page.wait_for_selector(selector)
                text = await self.page.text_content(selector)
            else:
                logger.info("Extracting all visible text")
                text = await self.page.evaluate(
                    "() => document.body.innerText"
                )
            
            return text.strip() if text else ""
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            raise
    
    async def fill_input(self, selector: str, value: str) -> str:
        """
        Fill an input field.
        
        Args:
            selector: CSS selector for input field
            value: Value to fill
            
        Returns:
            Success message
        """
        await self.ensure_started()
        
        try:
            logger.info(f"Filling input {selector} with value: {value}")
            
            await self.page.wait_for_selector(selector)
            await self.page.fill(selector, value)
            
            return f"Successfully filled input: {selector}"
        except Exception as e:
            logger.error(f"Fill input failed: {e}")
            raise
    
    async def wait(self, duration_ms: int) -> str:
        """
        Wait for a duration.
        
        Args:
            duration_ms: Duration to wait in milliseconds
            
        Returns:
            Success message
        """
        logger.info(f"Waiting for {duration_ms}ms")
        await asyncio.sleep(duration_ms / 1000)
        return f"Waited for {duration_ms}ms"
    
    async def navigate_back(self) -> str:
        """Navigate back in browser history."""
        await self.ensure_started()
        
        try:
            logger.info("Navigating back")
            await self.page.go_back()
            await self.page.wait_for_load_state("networkidle")
            return "Successfully navigated back"
        except Exception as e:
            logger.error(f"Navigate back failed: {e}")
            raise
    
    async def get_current_url(self) -> str:
        """Get current page URL."""
        await self.ensure_started()
        return self.page.url
    
    async def get_title(self) -> str:
        """Get current page title."""
        await self.ensure_started()
        return await self.page.title()
