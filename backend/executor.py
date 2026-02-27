"""
Executor that runs automation plans sequentially.

Contains:
  Executor              — original browser-only executor (ActionPlan / ActionStep)
  AutonomousGoalExecutor — full autonomous executor using ToolRegistry (GoalPlan / GoalStep)
"""

import asyncio
import time
from typing import Callable, List, Optional
from .models.schemas import ActionPlan, ActionType, GoalPlan, GoalStep
from .browser_controller import BrowserController
from .session_manager import _is_stale_error, get_session as _get_browser_session
# BrowserSingleton alias kept for any remaining direct uses
from .tools.browser_singleton import BrowserSingleton
from .utils.logger import get_logger


logger = get_logger(__name__)


# ============================================================================
# Helpers
# ============================================================================

def extract_steps(plan_json: dict) -> list:
    """
    Extract executable steps from a plan dict, supporting both formats:

    New format (deliberative output from SANDHYA_SYSTEM_PROMPT):
        { "final_plan": { "steps": [ {"step":1, "action":"...", "parameters":{}} ] } }

    Legacy format:
        { "plan": [ {"step":1, "action":"...", "parameters":{}} ] }

    Args:
        plan_json: Raw plan dictionary (e.g. from GoalPlan.model_dump() or raw LLM JSON).

    Returns:
        List of step dicts, or [] if neither key is present.
    """
    if "final_plan" in plan_json:
        return plan_json["final_plan"].get("steps", []) or []
    return plan_json.get("plan", []) or []


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
                logger.info(f"Executing step {idx}: {step.action}")
                
                # Send status update
                if step.description:
                    await self._send_status(f"Step {idx}: {step.description}...")
                else:
                    await self._send_status(f"Executing {step.action}...")
                
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
            t0 = time.monotonic()
            try:
                result = await self._execute_step(step)
                duration_ms = int((time.monotonic() - t0) * 1000)
                logger.info(
                    f"[Executor] action={step.action} | "
                    f"status=success | duration_ms={duration_ms} | "
                    f"result={str(result)[:80]!r}"
                )
                return result
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


# ============================================================================
# AutonomousGoalExecutor — dispatches GoalPlan steps through ToolRegistry
# ============================================================================

class AutonomousGoalExecutor:
    """
    Executes a GoalPlan by dispatching each step through the ToolRegistry.

    Unlike the original Executor (which is tied to browser ActionPlans),
    this executor handles every tool category:
      - Browser automation
      - File system operations
      - Code execution
      - Web research

    Each step result is stored in MemoryManager for use in validation + re-planning.
    """

    def __init__(self, tool_registry, memory_manager=None):
        """
        Args:
            tool_registry:  backend.tools.ToolRegistry instance
            memory_manager: Optional MemoryManager instance for recording steps
        """
        from .tools import ToolRegistry  # avoid circular import at module level
        self.registry = tool_registry
        self.memory = memory_manager
        self.status_callback: Optional[Callable[[str], None]] = None
        logger.info("[AutonomousGoalExecutor] Initialized")

    def set_status_callback(self, callback: Callable[[str], None]) -> None:
        self.status_callback = callback

    async def execute_plan(self, plan: GoalPlan) -> List[dict]:
        """
        Execute all steps in a GoalPlan sequentially.

        Supports both new deliberative format (final_plan.steps) and legacy
        format (plan). Step extraction is performed via the module-level
        ``extract_steps`` helper for uniform dual-format handling.

        Args:
            plan: GoalPlan produced by GoalPlanner

        Returns:
            List of step result dicts:
            [{"step": 1, "action": "...", "success": bool, "result": "...", "duration_ms": N}, ...]
        """
        results = []

        # ── Universal step extraction (handles final_plan.steps OR plan) ────
        plan_dict  = plan.model_dump()
        raw_steps  = extract_steps(plan_dict)
        goal_steps = [
            GoalStep(**s) if isinstance(s, dict) else s
            for s in raw_steps
        ]

        logger.info(
            f"[AutonomousGoalExecutor] Executing plan: {len(goal_steps)} steps | "
            f"mode={plan.mode} | goal={plan.goal[:60]!r}"
        )

        for step in goal_steps:
            step_result = await self._execute_step(step)
            results.append(step_result)

            # Record in memory if available
            if self.memory:
                self.memory.add_step(
                    step_number=step.step,
                    action=step.action,
                    parameters=step.parameters,
                    result=step_result["result"],
                    success=step_result["success"],
                    duration_ms=step_result["duration_ms"],
                    error=step_result.get("error"),
                )

        return results

    async def _execute_step(self, step: GoalStep) -> dict:
        """
        Execute a single GoalStep with automatic stale-browser recovery.

        Flow:
          1. Call ToolRegistry.execute() — never raises, always returns {status,data,error}
          2. If result is error AND the error string matches a stale-browser pattern:
               a. Call BrowserSingleton.reset_browser()
               b. Retry the step ONCE
          3. Return structured result dict.
        """
        action = step.action
        params = step.parameters or {}

        await self._send_status(f"Step {step.step}: {step.description or action}...")
        logger.info(f"[TOOL] Executing: {action} | params={params}")

        async def _run_once() -> dict:
            t0 = time.monotonic()
            tool_result = await self.registry.execute(action, params)
            duration_ms = int((time.monotonic() - t0) * 1000)
            logger.info(f"[TOOL RESULT] step={step.step} action={action} | {tool_result}")
            return tool_result, duration_ms

        tool_result, duration_ms = await _run_once()

        # ── self-healing: detect stale browser, reset, retry once ──────────
        if (
            isinstance(tool_result, dict)
            and tool_result.get("status") == "error"
            and tool_result.get("error")
            and _is_stale_error(Exception(tool_result["error"]))
        ):
            logger.warning(
                f"[AutonomousGoalExecutor] Stale browser detected on step={step.step} "
                f"action={action} — resetting browser and retrying..."
            )
            try:
                await _get_browser_session().reset()   # session_manager.reset()
                logger.info(f"[AutonomousGoalExecutor] Browser reset OK, retrying step={step.step}")
                tool_result, duration_ms = await _run_once()
            except Exception as reset_err:
                logger.error(f"[AutonomousGoalExecutor] Browser reset failed: {reset_err}")
                # Keep original error result — don't mask the reset failure
        # ───────────────────────────────────────────────────────────────────

        succeeded = isinstance(tool_result, dict) and tool_result.get("status") == "success"

        if succeeded:
            data = tool_result.get("data")
            if isinstance(data, dict):
                result_str = " | ".join(f"{k}={v}" for k, v in data.items())
            elif data is not None:
                result_str = str(data)[:300]
            else:
                result_str = f"{action} completed successfully"

            logger.info(
                f"[AutonomousGoalExecutor] step={step.step} action={action} | "
                f"status=SUCCESS | duration_ms={duration_ms} | result={result_str[:80]!r}"
            )
            return {
                "step": step.step,
                "action": action,
                "parameters": params,
                "success": True,
                "result": result_str,
                "tool_result": tool_result,
                "duration_ms": duration_ms,
            }
        else:
            error_msg = (
                tool_result.get("error", "unknown error")
                if isinstance(tool_result, dict)
                else str(tool_result)
            )
            logger.error(
                f"[AutonomousGoalExecutor] step={step.step} action={action} | "
                f"status=FAILED | duration_ms={duration_ms} | error={error_msg}"
            )
            return {
                "step": step.step,
                "action": action,
                "parameters": params,
                "success": False,
                "result": f"Step failed: {error_msg}",
                "tool_result": tool_result,
                "duration_ms": duration_ms,
                "error": error_msg,
            }

    async def _send_status(self, message: str) -> None:
        """Send status update via callback."""
        if self.status_callback:
            self.status_callback(message)
        else:
            logger.info(f"[AutonomousGoalExecutor] Status: {message}")
