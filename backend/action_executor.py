"""
Action execution layer for autonomous browser automation.

This module provides ActionExecutor which executes structured ActionDecision
objects against a live Playwright page instance.

Responsibilities:
- Click, type, read, scroll, wait, navigate actions
- Retry logic and safety timeouts
- Structured execution results
- Safe error handling and logging

No LLM calls. Pure deterministic browser control.

Author: Agent System
Date: 2026-02-25
Version: 1.0.0
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from playwright.async_api import Page
from .planner import ActionDecision
from .utils.logger import get_logger


logger = get_logger(__name__)


# ============================================================================
# Constants
# ============================================================================

ACTION_TIMEOUT = 5.0  # seconds per action
CLICK_RETRY_ATTEMPTS = 2
SCROLL_AMOUNT = 3  # page heights


# ============================================================================
# ActionExecutor Class
# ============================================================================

class ActionExecutor:
    """
    Executes structured action decisions against a Playwright page.
    
    Takes ActionDecision objects from planner and safely executes them
    using Playwright, returning structured results.
    
    Supports actions: click, type, read, scroll, wait, navigate, finish
    
    Attributes:
        _logger: Configured logger instance
        _execution_history: List of executed actions for loop detection
        _max_history: Maximum history items to track
    """
    
    _max_history = 50
    
    def __init__(self):
        """Initialize action executor."""
        self._logger = get_logger(f"action_executor.{id(self)}")
        self._execution_history: List[Dict[str, Any]] = []
        self._logger.debug("ActionExecutor initialized")
    
    async def execute(
        self,
        decision: ActionDecision,
        page: Page
    ) -> Dict[str, Any]:
        """
        Execute a single action decision against the page.
        
        Args:
            decision: ActionDecision object with action details
            page: Playwright page instance
            
        Returns:
            Structured execution result dict with:
            {
              "status": "success|failed|completed",
              "action": str,
              "selector": str or None,
              "details": str,
              "timestamp": ISO timestamp,
              "duration_ms": float
            }
        """
        start_time = datetime.now()
        
        self._logger.info(f"Executing action: {decision.action}")
        
        try:
            # Validate page is available
            if not page:
                return self._error_result(
                    decision, "Page not available", start_time
                )
            
            # Route to action handler
            action = decision.action.lower()
            
            if action == "click":
                result = await self._execute_click(decision, page, start_time)
            elif action == "type":
                result = await self._execute_type(decision, page, start_time)
            elif action == "read":
                result = await self._execute_read(decision, page, start_time)
            elif action == "scroll":
                result = await self._execute_scroll(decision, page, start_time)
            elif action == "wait":
                result = await self._execute_wait(decision, page, start_time)
            elif action == "navigate":
                result = await self._execute_navigate(decision, page, start_time)
            elif action == "finish":
                result = await self._execute_finish(decision, page, start_time)
            else:
                result = self._error_result(
                    decision, f"Unknown action: {action}", start_time
                )
            
            # Record to history
            self._record_execution(action, result)
            
            self._logger.info(f"Action result: {result['status']}")
            return result
        
        except Exception as e:
            self._logger.error(f"Action execution failed: {str(e)}")
            return self._error_result(decision, str(e), start_time)
    
    # ========================================================================
    # Action Handlers
    # ========================================================================
    
    async def _execute_click(
        self,
        decision: ActionDecision,
        page: Page,
        start_time: datetime
    ) -> Dict[str, Any]:
        """
        Execute click action.
        
        Args:
            decision: ActionDecision with target selector
            page: Playwright page
            start_time: Execution start time
            
        Returns:
            Execution result
        """
        selector = decision.target_selector
        
        # Validate selector
        if not selector:
            return self._error_result(
                decision, "Click requires target_selector", start_time
            )
        
        self._logger.debug(f"Clicking selector: {selector}")
        
        # Add delay before click to avoid race conditions
        await asyncio.sleep(0.5)
        
        # Try to click with retries
        last_error = None
        for attempt in range(CLICK_RETRY_ATTEMPTS):
            try:
                await asyncio.wait_for(
                    page.click(selector),
                    timeout=ACTION_TIMEOUT
                )
                
                self._logger.info(f"Click succeeded: {selector}")
                return {
                    "status": "success",
                    "action": "click",
                    "selector": selector,
                    "details": f"Clicked element: {selector}",
                    "timestamp": datetime.now().isoformat(),
                    "duration_ms": (datetime.now() - start_time).total_seconds() * 1000,
                }
            
            except asyncio.TimeoutError:
                last_error = "Click action timeout"
                self._logger.warning(f"Click timeout on attempt {attempt + 1}")
            
            except Exception as e:
                last_error = str(e)
                self._logger.warning(f"Click attempt {attempt + 1} failed: {e}")
            
            # Brief delay before retry
            if attempt < CLICK_RETRY_ATTEMPTS - 1:
                await asyncio.sleep(0.2)
        
        return self._error_result(
            decision, f"Click failed: {last_error}", start_time
        )
    
    async def _execute_type(
        self,
        decision: ActionDecision,
        page: Page,
        start_time: datetime
    ) -> Dict[str, Any]:
        """
        Execute type action (fill input field).
        
        Args:
            decision: ActionDecision with selector and input_text
            page: Playwright page
            start_time: Execution start time
            
        Returns:
            Execution result
        """
        selector = decision.target_selector
        text = decision.input_text
        
        # Validate inputs
        if not selector:
            return self._error_result(
                decision, "Type requires target_selector", start_time
            )
        
        if not text:
            return self._error_result(
                decision, "Type requires input_text", start_time
            )
        
        self._logger.debug(f"Typing into {selector}: {text[:50]}...")
        
        # Add delay before typing to avoid race conditions
        await asyncio.sleep(0.5)
        
        try:
            await asyncio.wait_for(
                page.fill(selector, text),
                timeout=ACTION_TIMEOUT
            )
            
            self._logger.info(f"Type succeeded: {selector}")
            return {
                "status": "success",
                "action": "type",
                "selector": selector,
                "details": f"Typed '{text[:50]}...' into {selector}",
                "timestamp": datetime.now().isoformat(),
                "duration_ms": (datetime.now() - start_time).total_seconds() * 1000,
            }
        
        except asyncio.TimeoutError:
            return self._error_result(
                decision, f"Type timeout on {selector}", start_time
            )
        except Exception as e:
            return self._error_result(
                decision, f"Type failed: {str(e)}", start_time
            )
    
    async def _execute_read(
        self,
        decision: ActionDecision,
        page: Page,
        start_time: datetime
    ) -> Dict[str, Any]:
        """
        Execute read action (extract text content).
        
        Args:
            decision: ActionDecision (selector optional)
            page: Playwright page
            start_time: Execution start time
            
        Returns:
            Execution result with text content
        """
        selector = decision.target_selector or "body"
        
        self._logger.debug(f"Reading text from {selector}")
        
        try:
            text = await asyncio.wait_for(
                page.inner_text(selector),
                timeout=ACTION_TIMEOUT
            )
            
            # Limit text length
            text_summary = text[:1000] if len(text) > 1000 else text
            
            self._logger.info(f"Read succeeded: {len(text)} chars")
            return {
                "status": "success",
                "action": "read",
                "selector": selector,
                "text_content": text_summary,
                "full_length": len(text),
                "details": f"Read {len(text)} characters",
                "timestamp": datetime.now().isoformat(),
                "duration_ms": (datetime.now() - start_time).total_seconds() * 1000,
            }
        
        except asyncio.TimeoutError:
            return self._error_result(
                decision, f"Read timeout on {selector}", start_time
            )
        except Exception as e:
            return self._error_result(
                decision, f"Read failed: {str(e)}", start_time
            )
    
    async def _execute_scroll(
        self,
        decision: ActionDecision,
        page: Page,
        start_time: datetime
    ) -> Dict[str, Any]:
        """
        Execute scroll action.
        
        Args:
            decision: ActionDecision (direction in input_text: "up" or "down")
            page: Playwright page
            start_time: Execution start time
            
        Returns:
            Execution result
        """
        direction = (decision.input_text or "down").lower()
        amount = SCROLL_AMOUNT
        
        # Determine scroll direction
        if direction == "up":
            scroll_amount = -amount * 500
        else:
            scroll_amount = amount * 500
        
        self._logger.debug(f"Scrolling {direction} ({scroll_amount}px)")
        
        try:
            await asyncio.wait_for(
                page.evaluate(f"window.scrollBy(0, {scroll_amount})"),
                timeout=ACTION_TIMEOUT
            )
            
            # Wait a bit for content to load
            await asyncio.wait_for(
                page.wait_for_timeout(200),
                timeout=1.0
            )
            
            self._logger.info(f"Scroll succeeded: {direction}")
            return {
                "status": "success",
                "action": "scroll",
                "selector": None,
                "details": f"Scrolled {direction} by {abs(scroll_amount)}px",
                "timestamp": datetime.now().isoformat(),
                "duration_ms": (datetime.now() - start_time).total_seconds() * 1000,
            }
        
        except asyncio.TimeoutError:
            return self._error_result(
                decision, "Scroll timeout", start_time
            )
        except Exception as e:
            return self._error_result(
                decision, f"Scroll failed: {str(e)}", start_time
            )
    
    async def _execute_wait(
        self,
        decision: ActionDecision,
        page: Page,
        start_time: datetime
    ) -> Dict[str, Any]:
        """
        Execute wait action (pause execution).
        
        Args:
            decision: ActionDecision (duration in input_text or default 2s)
            page: Playwright page
            start_time: Execution start time
            
        Returns:
            Execution result
        """
        try:
            # Parse duration (default 2000ms)
            duration = 2000
            if decision.input_text:
                try:
                    duration = int(decision.input_text)
                except ValueError:
                    duration = 2000
            
            self._logger.debug(f"Waiting {duration}ms")
            
            await asyncio.wait_for(
                page.wait_for_timeout(duration),
                timeout=ACTION_TIMEOUT
            )
            
            self._logger.info(f"Wait completed: {duration}ms")
            return {
                "status": "success",
                "action": "wait",
                "selector": None,
                "details": f"Waited {duration}ms",
                "timestamp": datetime.now().isoformat(),
                "duration_ms": (datetime.now() - start_time).total_seconds() * 1000,
            }
        
        except asyncio.TimeoutError:
            return self._error_result(
                decision, "Wait timeout", start_time
            )
        except Exception as e:
            return self._error_result(
                decision, f"Wait failed: {str(e)}", start_time
            )
    
    async def _execute_navigate(
        self,
        decision: ActionDecision,
        page: Page,
        start_time: datetime
    ) -> Dict[str, Any]:
        """
        Execute navigate action (goto URL or back).
        
        Args:
            decision: ActionDecision (URL in input_text or "back")
            page: Playwright page
            start_time: Execution start time
            
        Returns:
            Execution result
        """
        target = decision.input_text or "back"
        
        self._logger.debug(f"Navigating to: {target}")
        
        try:
            if target.lower() == "back":
                await asyncio.wait_for(
                    page.go_back(),
                    timeout=ACTION_TIMEOUT
                )
                # Wait for page to load after navigation
                await asyncio.wait_for(
                    page.wait_for_load_state("domcontentloaded"),
                    timeout=ACTION_TIMEOUT
                )
                details = "Navigated back"
            else:
                # Treat as URL
                await asyncio.wait_for(
                    page.goto(target),
                    timeout=ACTION_TIMEOUT
                )
                # Wait for page to load after navigation
                await asyncio.wait_for(
                    page.wait_for_load_state("domcontentloaded"),
                    timeout=ACTION_TIMEOUT
                )
                details = f"Navigated to {target}"
            
            self._logger.info(f"Navigate succeeded: {target}")
            return {
                "status": "success",
                "action": "navigate",
                "selector": None,
                "details": details,
                "timestamp": datetime.now().isoformat(),
                "duration_ms": (datetime.now() - start_time).total_seconds() * 1000,
            }
        
        except asyncio.TimeoutError:
            return self._error_result(
                decision, f"Navigate timeout to {target}", start_time
            )
        except Exception as e:
            return self._error_result(
                decision, f"Navigate failed: {str(e)}", start_time
            )
    
    async def _execute_finish(
        self,
        decision: ActionDecision,
        page: Page,
        start_time: datetime
    ) -> Dict[str, Any]:
        """
        Execute finish action (task complete).
        
        Args:
            decision: ActionDecision
            page: Playwright page (unused for finish)
            start_time: Execution start time
            
        Returns:
            Completion result
        """
        self._logger.info("Task marked as completed")
        return {
            "status": "completed",
            "action": "finish",
            "selector": None,
            "details": "Task completed",
            "timestamp": datetime.now().isoformat(),
            "duration_ms": (datetime.now() - start_time).total_seconds() * 1000,
        }
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def _error_result(
        self,
        decision: ActionDecision,
        error_message: str,
        start_time: datetime
    ) -> Dict[str, Any]:
        """
        Create structured error result.
        
        Args:
            decision: ActionDecision that failed
            error_message: Error description
            start_time: Execution start time
            
        Returns:
            Error result dict
        """
        return {
            "status": "failed",
            "action": decision.action,
            "selector": decision.target_selector,
            "error": error_message,
            "details": f"Action failed: {error_message}",
            "timestamp": datetime.now().isoformat(),
            "duration_ms": (datetime.now() - start_time).total_seconds() * 1000,
        }
    
    def _record_execution(self, action: str, result: Dict[str, Any]):
        """
        Record executed action for history tracking.
        
        Used for loop detection.
        
        Args:
            action: Action type
            result: Execution result
        """
        record = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "status": result.get("status"),
            "selector": result.get("selector"),
        }
        
        self._execution_history.append(record)
        
        # Trim history if too large
        if len(self._execution_history) > self._max_history:
            self._execution_history = self._execution_history[-self._max_history:]
        
        self._logger.debug(f"Recorded execution: {len(self._execution_history)} in history")
    
    def get_execution_history(self) -> List[Dict[str, Any]]:
        """
        Get execution history (for loop detection).
        
        Returns:
            List of execution records
        """
        return self._execution_history.copy()
    
    def clear_history(self):
        """Clear execution history."""
        self._execution_history = []
        self._logger.debug("Execution history cleared")
    
    def detect_action_loop(self, window_size: int = 5) -> bool:
        """
        Detect if same action is being repeated or same selector is being clicked repeatedly.
        
        Checks for:
        1. Same action repeated in window
        2. Same selector clicked more than 2 times in window
        
        Args:
            window_size: Number of recent actions to check
            
        Returns:
            True if loop detected (same action repeated or same selector stuck)
        """
        if len(self._execution_history) < window_size:
            return False
        
        recent = self._execution_history[-window_size:]
        actions = [r.get("action") for r in recent]
        selectors = [r.get("selector") for r in recent]
        
        # Check if all recent actions are the same
        if len(set(actions)) == 1:
            self._logger.warning(f"Action loop detected: {actions[0]} repeated {window_size} times")
            return True
        
        # Check if same selector is being clicked multiple times (likely stuck)
        click_actions = [r for r in recent if r.get("action") == "click"]
        if len(click_actions) >= 3:
            click_selectors = [r.get("selector") for r in click_actions]
            # Count most common selector
            if click_selectors:
                from collections import Counter
                selector_counts = Counter(click_selectors)
                most_common_selector, count = selector_counts.most_common(1)[0]
                if count >= 2 and most_common_selector:
                    self._logger.warning(
                        f"Selector loop detected: clicking {most_common_selector} "
                        f"{count} times in recent actions"
                    )
                    return True
        
        return False
