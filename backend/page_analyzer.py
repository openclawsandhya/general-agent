"""
Page analyzer module for intelligent webpage perception.

This module provides PageAnalyzer which analyzes the active Playwright page
and returns structured information about:
- Page metadata (URL, title)
- Text content summary
- Interactive elements (links, buttons, inputs)
- Headings and hierarchy

This data feeds the autonomous reasoning loop and planner for better decisions.

Author: Agent System
Date: 2026-02-25
Version: 1.0.0
"""

import logging
import re
from typing import Dict, List, Any, Optional
from datetime import datetime

from playwright.async_api import Page
from .utils.logger import get_logger


logger = get_logger(__name__)


class PageAnalyzer:
    """
    Analyzes the current Playwright page and extracts structured information.
    
    Provides perception of webpage state for autonomous reasoning:
    - Metadata (URL, title)
    - Text content summary
    - Interactive elements (links, buttons, inputs)
    - Headings
    
    Used by AutonomousAgentController._observe_state() and Planner for
    better decision making.
    
    Attributes:
        browser_controller: BrowserController instance managing Playwright page
        _logger: Configured logger instance
    """
    
    # Result limits to prevent data bloat
    MAX_LINKS = 20
    MAX_BUTTONS = 10
    MAX_INPUTS = 10
    MAX_TEXT_LENGTH = 2000
    TEXT_SUMMARY_LENGTH = 800
    
    # Selectors for noisy elements to potentially ignore
    NOISE_SELECTORS = [
        "nav", "footer", "header", ".navbar", ".navigation",
        ".cookiebanner", ".popup", ".modal", ".ad", ".advertisement"
    ]
    
    def __init__(self, page):
        """
        Initialize page analyzer.
        
        Args:
            page: Playwright async Page instance (required, never None)
            
        Raises:
            ValueError: If page is None or invalid
        """
        if page is None:
            raise ValueError("PageAnalyzer requires a valid Playwright Page instance (cannot be None)")
        
        self.page = page
        self._logger = get_logger(f"page_analyzer.{id(self)}")
        self._logger.debug(f"PageAnalyzer initialized with page: {page.url if page else 'unknown'}")
    
    async def analyze_page(self) -> Dict[str, Any]:
        """
        Analyze current page and extract structured information.
        
        Returns comprehensive page state including:
        - url: Current page URL
        - title: Page title
        - main_text_summary: Summarized visible text
        - headings: List of heading texts
        - links: List of link dicts with text and selector
        - buttons: List of button dicts with text and selector
        - inputs: List of input dicts with properties and selector
        - analysis_timestamp: ISO timestamp of analysis
        
        Returns:
            Structured page analysis dictionary
        """
        self._logger.debug("Starting page analysis")
        
        try:
            page = self.page
            
            # Check if page is valid
            if not page:
                self._logger.error("Page reference is None, cannot analyze")
                return self._minimal_state()
            
            # Extract metadata
            url = page.url
            title = await page.title()
            
            self._logger.debug(f"Analyzing page: {url}")
            
            # Extract text content
            main_text = await self._extract_text_content(page)
            main_text_summary = self._summarize_text(main_text)
            
            # Extract headings
            headings = await self._extract_headings(page)
            
            # Extract interactive elements
            links = await self._extract_links(page)
            buttons = await self._extract_buttons(page)
            inputs = await self._extract_inputs(page)
            
            # Compose result
            result = {
                "url": url,
                "title": title,
                "main_text_summary": main_text_summary,
                "headings": headings,
                "links": links,
                "buttons": buttons,
                "inputs": inputs,
                "analysis_timestamp": self._get_timestamp(),
            }
            
            self._logger.debug(
                f"Page analysis complete: {len(links)} links, "
                f"{len(buttons)} buttons, {len(inputs)} inputs"
            )
            
            return result
        
        except Exception as e:
            self._logger.error(f"Error analyzing page: {str(e)}")
            return self._minimal_state()
    
    # ========================================================================
    # Element Extraction Methods
    # ========================================================================
    
    async def _extract_text_content(self, page) -> str:
        """
        Extract visible text content from page body.
        
        Excludes scripts and styles, preserves natural spacing.
        
        Args:
            page: Playwright page object
            
        Returns:
            Visible text content (limited length)
        """
        try:
            # Get all text from body, excluding scripts and styles
            text = await page.evaluate(
                """
                () => {
                    let text = '';
                    const walk = document.createTreeWalker(
                        document.body,
                        NodeFilter.SHOW_TEXT,
                        null,
                        false
                    );
                    
                    let node;
                    while (node = walk.nextNode()) {
                        const parent = node.parentElement;
                        if (parent && !['script', 'style'].includes(parent.tagName.toLowerCase())) {
                            const content = node.textContent;
                            if (content && content.trim()) {
                                text += content + ' ';
                            }
                        }
                    }
                    return text;
                }
                """
            )
            
            # Limit length
            if len(text) > self.MAX_TEXT_LENGTH:
                text = text[:self.MAX_TEXT_LENGTH]
            
            return text.strip()
        
        except Exception as e:
            self._logger.warning(f"Error extracting text: {e}")
            return ""
    
    async def _extract_headings(self, page) -> List[str]:
        """
        Extract heading texts (h1, h2, h3).
        
        Args:
            page: Playwright page object
            
        Returns:
            List of heading texts
        """
        try:
            headings = await page.query_selector_all("h1, h2, h3")
            heading_texts = []
            
            for heading in headings:
                try:
                    # Check visibility
                    if not await self._is_visible(heading):
                        continue
                    
                    text = await heading.text_content()
                    if text and text.strip():
                        heading_texts.append(text.strip())
                
                except Exception as e:
                    self._logger.debug(f"Error extracting heading: {e}")
                    continue
            
            return heading_texts[:10]  # Limit to 10 headings
        
        except Exception as e:
            self._logger.warning(f"Error extracting headings: {e}")
            return []
    
    async def _extract_links(self, page) -> List[Dict[str, str]]:
        """
        Extract clickable links with text and selectors.
        
        Only includes visible links with meaningful text (>2 chars).
        
        Args:
            page: Playwright page object
            
        Returns:
            List of link dicts with 'text' and 'selector'
        """
        try:
            links_data = []
            links = await page.query_selector_all("a")
            
            for idx, link in enumerate(links):
                try:
                    # Check if visible
                    if not await self._is_visible(link):
                        continue
                    
                    # Get text
                    text = await link.text_content()
                    if not text or len(text.strip()) < 2:
                        continue
                    
                    text = text.strip()[:80]  # Limit text length
                    
                    # Generate selector
                    selector = await self._generate_selector(link)
                    
                    links_data.append({
                        "text": text,
                        "selector": selector,
                    })
                    
                    if len(links_data) >= self.MAX_LINKS:
                        break
                
                except Exception as e:
                    self._logger.debug(f"Error processing link {idx}: {e}")
                    continue
            
            return links_data
        
        except Exception as e:
            self._logger.warning(f"Error extracting links: {e}")
            return []
    
    async def _extract_buttons(self, page) -> List[Dict[str, str]]:
        """
        Extract clickable buttons with text and selectors.
        
        Includes button elements and submit/button type inputs.
        
        Args:
            page: Playwright page object
            
        Returns:
            List of button dicts with 'text' and 'selector'
        """
        try:
            buttons_data = []
            buttons = await page.query_selector_all(
                "button, input[type='button'], input[type='submit']"
            )
            
            for idx, button in enumerate(buttons):
                try:
                    # Check if visible
                    if not await self._is_visible(button):
                        continue
                    
                    # Get text or value attribute
                    text = await button.text_content()
                    if not text or len(text.strip()) == 0:
                        text = await button.get_attribute("value")
                    
                    if not text or len(text.strip()) < 1:
                        continue
                    
                    text = text.strip()[:80]
                    
                    # Generate selector
                    selector = await self._generate_selector(button)
                    
                    buttons_data.append({
                        "text": text,
                        "selector": selector,
                    })
                    
                    if len(buttons_data) >= self.MAX_BUTTONS:
                        break
                
                except Exception as e:
                    self._logger.debug(f"Error processing button {idx}: {e}")
                    continue
            
            return buttons_data
        
        except Exception as e:
            self._logger.warning(f"Error extracting buttons: {e}")
            return []
    
    async def _extract_inputs(self, page) -> List[Dict[str, Any]]:
        """
        Extract form inputs (text, search, etc.) with metadata.
        
        Includes input and textarea elements with placeholder/name properties.
        
        Args:
            page: Playwright page object
            
        Returns:
            List of input dicts with 'placeholder', 'name', 'type', 'selector'
        """
        try:
            inputs_data = []
            inputs = await page.query_selector_all("input, textarea")
            
            for idx, input_elem in enumerate(inputs):
                try:
                    # Check if visible
                    if not await self._is_visible(input_elem):
                        continue
                    
                    # Get properties
                    placeholder = await input_elem.get_attribute("placeholder") or ""
                    name = await input_elem.get_attribute("name") or ""
                    input_type = await input_elem.get_attribute("type") or "text"
                    
                    # Skip if no identifying feature
                    if not placeholder and not name and input_type == "hidden":
                        continue
                    
                    # Generate selector
                    selector = await self._generate_selector(input_elem)
                    
                    inputs_data.append({
                        "placeholder": placeholder[:50] if placeholder else "",
                        "name": name[:50] if name else "",
                        "type": input_type,
                        "selector": selector,
                    })
                    
                    if len(inputs_data) >= self.MAX_INPUTS:
                        break
                
                except Exception as e:
                    self._logger.debug(f"Error processing input {idx}: {e}")
                    continue
            
            return inputs_data
        
        except Exception as e:
            self._logger.warning(f"Error extracting inputs: {e}")
            return []
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    async def _is_visible(self, element) -> bool:
        """
        Check if element is visible on page.
        
        Checks:
        1. Element's is_visible() status
        2. Element's computed visibility style
        3. Element's computed display style
        4. Parent elements for hidden containers
        
        Args:
            element: Playwright element handle
            
        Returns:
            True if element is visible, False otherwise
        """
        try:
            # First check is_visible()
            if not await element.is_visible():
                return False
            
            # Check computed styles using JavaScript
            visibility_check = await element.evaluate(
                """
                el => {
                    // Check element's own computed style
                    const style = window.getComputedStyle(el);
                    
                    // Check display property
                    if (style.display === 'none') {
                        return false;
                    }
                    
                    // Check visibility property
                    if (style.visibility === 'hidden') {
                        return false;
                    }
                    
                    // Check opacity
                    if (style.opacity === '0') {
                        return false;
                    }
                    
                    // Check all parent elements for hidden containers
                    let parent = el.parentElement;
                    while (parent) {
                        const parentStyle = window.getComputedStyle(parent);
                        
                        if (parentStyle.display === 'none') {
                            return false;
                        }
                        
                        if (parentStyle.visibility === 'hidden') {
                            return false;
                        }
                        
                        parent = parent.parentElement;
                    }
                    
                    return true;
                }
                """
            )
            
            return visibility_check
        
        except Exception as e:
            self._logger.debug(f"Error checking visibility: {e}")
            return False
    
    async def _generate_selector(self, element) -> str:
        """
        Generate stable CSS selector for element.
        
        Priority:
        1. Element ID (#id_value)
        2. Class-based (tag.class1.class2)
        3. Tag with position (div:nth-of-type(3))
        
        Args:
            element: Playwright element handle
            
        Returns:
            CSS selector string
        """
        try:
            # Try ID first (most stable)
            elem_id = await element.get_attribute("id")
            if elem_id and elem_id.strip():
                return f"#{elem_id}"
            
            # Try class
            classes = await element.get_attribute("class")
            if classes and classes.strip():
                # Use first 1-2 classes
                class_list = classes.split()[:2]
                if class_list:
                    tag = await element.evaluate("el => el.tagName.toLowerCase()")
                    class_str = ".".join(class_list)
                    return f"{tag}.{class_str}"
            
            # Fallback: tag + nth-of-type
            tag = await element.evaluate("el => el.tagName.toLowerCase()")
            index = await element.evaluate(
                """el => {
                    let count = 0;
                    let sibling = el;
                    while (sibling = sibling.previousElementSibling) {
                        if (sibling.tagName === el.tagName) count++;
                    }
                    return count + 1;
                }"""
            )
            
            return f"{tag}:nth-of-type({index})"
        
        except Exception as e:
            self._logger.debug(f"Error generating selector: {e}")
            return "unknown"
    
    def _summarize_text(self, text: str) -> str:
        """
        Summarize text by collapsing whitespace and limiting length.
        
        Rules:
        - Collapse multiple whitespace into single space
        - Limit to TEXT_SUMMARY_LENGTH (800 chars)
        - Add ellipsis if truncated
        
        Args:
            text: Raw text to summarize
            
        Returns:
            Summarized text (limited length, cleaned whitespace)
        """
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = " ".join(text.split())
        
        # Limit length
        if len(text) > self.TEXT_SUMMARY_LENGTH:
            text = text[:self.TEXT_SUMMARY_LENGTH - 3] + "..."
        
        return text
    
    def _minimal_state(self) -> Dict[str, Any]:
        """
        Return minimal page state when page not fully loaded or error occurs.
        
        Returns:
            Minimal state dictionary with empty/placeholder values
        """
        return {
            "url": "unknown",
            "title": "Page not loaded",
            "main_text_summary": "",
            "headings": [],
            "links": [],
            "buttons": [],
            "inputs": [],
            "analysis_timestamp": self._get_timestamp(),
        }
    
    @staticmethod
    def _get_timestamp() -> str:
        """
        Get current ISO timestamp.
        
        Returns:
            ISO format timestamp string
        """
        return datetime.now().isoformat()
