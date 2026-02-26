"""
Executor that runs automation plans sequentially.
"""

import asyncio
from typing import Callable, List, Optional
from models.schemas import ActionPlan, ActionType
from .browser_controller import BrowserController
from .utils.logger import get_logger


logger = get_logger(__name__)


class Executor:
    """Executes action plans using browser controller."""
    
    def __init__(self, browser_controller: BrowserController):
        """
        Initialize executor.
        
        Args:
            browser_controller: Browser controller instance
        """
        self.browser = browser_controller
        self.status_callback: Optional[Callable[[str], None]] = None
        
        logger.info("Executor initialized")
    
    def set_status_callback(self, callback: Callable[[str], None]) -> None:
        """
        Set callback for status updates.
        
        Args:
            callback: Function to call with status messages
        """
        self.status_callback = callback
    
    async def execute(self, plan: ActionPlan) -> str:
        """
        Execute action plan sequentially.
        
        Args:
            plan: ActionPlan to execute
            
        Returns:
            Final status message
        """
        logger.info(f"Starting execution of plan with {len(plan.steps)} steps")
        
        results = []
        
        for idx, step in enumerate(plan.steps, 1):
            try:
                logger.info(f"Executing step {idx}: {step.action.value}")
                
                # Send status update
                if step.description:
                    await self._send_status(f"Step {idx}: {step.description}...")
                else:
                    await self._send_status(f"Executing {step.action.value}...")
                
                # Execute action with retry
                result = await self._execute_step_with_retry(step)
                results.append(result)
                
                logger.info(f"Step {idx} completed: {result}")
                
            except Exception as e:
                logger.error(f"Step {idx} failed: {e}")
                error_msg = f"Step {idx} failed: {str(e)}"
                await self._send_status(error_msg)
                results.append(error_msg)
        
        final_message = self._build_final_message(results)
        logger.info(f"Execution complete. Message: {final_message}")
        
        return final_message
    
    async def _execute_step_with_retry(self, step, max_retries: int = 1):
        """
        Execute a step with retry logic.
        
        Args:
            step: ActionStep to execute
            max_retries: Number of retries on failure
            
        Returns:
            Result message
        """
        for attempt in range(max_retries + 1):
            try:
                return await self._execute_step(step)
            except asyncio.TimeoutError:
                if attempt < max_retries:
                    logger.warning(f"Timeout, retrying step (attempt {attempt + 2})")
                    await self._send_status(f"Retrying action...")
                    await asyncio.sleep(2)
                else:
                    raise
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"Step failed: {e}, retrying (attempt {attempt + 2})")
                    await self._send_status(f"Retrying action...")
                    await asyncio.sleep(1)
                else:
                    raise
    
    async def _execute_step(self, step) -> str:
        """
        Execute a single action step.
        
        Args:
            step: ActionStep to execute
            
        Returns:
            Result message
        """
        action = step.action
        
        if action == ActionType.OPEN_URL:
            return await self.browser.open_url(step.value)
        
        elif action == ActionType.SEARCH:
            return await self.browser.search(step.value)
        
        elif action == ActionType.CLICK:
            # Special case for click_first_result
            if step.value == "click_first_result":
                return await self.browser.click_first_result()
            else:
                return await self.browser.click(step.selector or step.value)
        
        elif action == ActionType.SCROLL:
            direction = step.value or "down"
            amount = step.duration_ms or 3 if step.duration_ms else 3
            return await self.browser.scroll(direction, amount)
        
        elif action == ActionType.EXTRACT_TEXT:
            text = await self.browser.extract_text(step.selector)
            return f"Extracted text: {text[:200]}..." if len(text) > 200 else f"Extracted text: {text}"
        
        elif action == ActionType.FILL_INPUT:
            return await self.browser.fill_input(step.selector, step.value)
        
        elif action == ActionType.WAIT:
            return await self.browser.wait(step.duration_ms or 1000)
        
        elif action == ActionType.NAVIGATE_BACK:
            return await self.browser.navigate_back()
        
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def _send_status(self, message: str) -> None:
        """
        Send status update via callback.
        
        Args:
            message: Status message
        """
        if self.status_callback:
            self.status_callback(message)
        else:
            logger.info(f"Status: {message}")
    
    def _build_final_message(self, results: List[str]) -> str:
        """
        Build final completion message from results.
        
        Args:
            results: List of action results
            
        Returns:
            Final message
        """
        # Count successes and failures
        successes = sum(1 for r in results if not r.startswith("Step") or "failed" not in r)
        failures = len(results) - successes
        
        if failures == 0:
            return f"✓ All {len(results)} steps completed successfully!"
        elif failures < len(results):
            return f"⚠ Completed {successes}/{len(results)} steps. {failures} step(s) encountered issues."
        else:
            return f"✗ All steps failed. Please check the execution logs."
