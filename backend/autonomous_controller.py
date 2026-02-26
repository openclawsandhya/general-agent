"""
Autonomous agent controller - the central brain loop.

Orchestrates the observe → decide → act loop with true re-planning:
1. PageAnalyzer: Observe current page state
2. HybridPlanner or LLMPlanner: Decide next best action
   - HybridPlanner: Deterministic rules + LLM fallback
   - LLMPlanner: Pure LLM-based decisions
3. ActionExecutor: Execute the action

Runs until goal is achieved or max steps reached.

Uses failure tracking to enable intelligent re-planning.

Supports pluggable planner modes:
- mode="deterministic" → HybridPlanner (rules-first)
- mode="llm" → LLMPlanner (LLM-first)

Author: Agent System
Date: 2026-02-25
Version: 1.1.0
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from playwright.async_api import Page
from .page_analyzer import PageAnalyzer
from .planner import HybridPlanner, ActionDecision
from .llm_planner import LLMPlanner
from .action_executor import ActionExecutor
from .llm_client import LLMClient
from .utils.logger import get_logger


logger = get_logger(__name__)


# ============================================================================
# Constants
# ============================================================================

DEFAULT_MAX_STEPS = 20
STEP_DELAY = 1.0  # seconds between steps
LOOP_DETECTION_WINDOW = 5  # actions to check for loops


# ============================================================================
# AutonomousAgentController Class
# ============================================================================

class AutonomousAgentController:
    """
    Central orchestration brain for autonomous browser automation with true re-planning.
    
    Implements the observe → decide → act loop:
    1. PageAnalyzer observes current page state
    2. HybridPlanner decides next action using deterministic rules + LLM fallback
    3. ActionExecutor executes the action against the page
    4. Loop repeats until goal achieved or max steps reached
    
    True Re-Planning:
    - Maintains execution_history and failure_history
    - Passes full history to HybridPlanner on every step
    - HybridPlanner uses history to make intelligent decisions
    - Failure tracking enables loop detection and alternative actions
    
    Maintains:
    - Execution history for all actions taken
    - Failure history for failed actions (for re-planning)
    - Conversation context for planning
    - Step tracking and metrics
    
    Attributes:
        page: Playwright page instance
        analyzer: PageAnalyzer instance
        planner: HybridPlanner instance (true re-planner)
        executor: ActionExecutor instance
        llm_client: LLMClient for planning fallback
        _logger: Configured logger
        _execution_history: List of all executed actions with decisions
        _failure_history: List of failed actions
        _conversation_history: Conversation context
    """
    
    def __init__(
        self,
        page: Page,
        analyzer: Optional[PageAnalyzer] = None,
        planner: Optional[HybridPlanner] = None,
        executor: Optional[ActionExecutor] = None,
        llm_client: Optional[LLMClient] = None,
        mode: str = "deterministic",
    ):
        """
        Initialize autonomous agent controller with pluggable planner mode.
        
        Args:
            page: Playwright page instance (required)
            analyzer: Optional PageAnalyzer (will create if None)
            planner: Optional planner (will create based on mode if None)
            executor: Optional ActionExecutor (will create if None)
            llm_client: Optional LLMClient for planning fallback
            mode: "deterministic" (HybridPlanner) or "llm" (LLMPlanner)
        """
        # Validate page parameter
        if page is None:
            raise ValueError("AutonomousAgentController requires a valid Playwright Page instance")
        
        self.page = page
        self.analyzer = analyzer or PageAnalyzer(page)
        self.mode = mode
        
        # Initialize primary planner based on mode
        if planner:
            self.planner = planner
        elif mode == "llm":
            self.planner = LLMPlanner()
        else:  # Default to deterministic
            self.planner = HybridPlanner(llm_client=llm_client)
        
        # Always have HybridPlanner as fallback safety brain for arbitration
        self.fallback_planner = HybridPlanner(llm_client=llm_client)
        
        self.executor = executor or ActionExecutor()
        self.llm_client = llm_client
        
        self._logger = get_logger(f"autonomous_controller.{id(self)}")
        
        # Two separate histories for intelligent re-planning
        self._execution_history: List[Dict[str, Any]] = []  # All actions
        self._failure_history: List[Dict[str, Any]] = []  # Failed actions only
        self._conversation_history: List[Dict[str, str]] = []
        
        self._logger.debug(f"AutonomousAgentController initialized with mode={mode}, planner={self.planner.__class__.__name__}")
        self._logger.info(f"[Controller Setup] Mode: {mode}")
        self._logger.info(f"[Controller Setup] Primary Planner: {self.planner.__class__.__name__}")
        self._logger.info(f"[Controller Setup] Fallback Safety Brain: HybridPlanner")
        self._logger.info(f"[Controller Setup] PageAnalyzer: {self.analyzer.__class__.__name__}")
        self._logger.info(f"[Controller Setup] Page URL: {self.page.url}")
    
    async def run_goal(
        self,
        user_goal: str,
        max_steps: int = DEFAULT_MAX_STEPS
    ) -> Dict[str, Any]:
        """
        Run the autonomous agent loop to achieve user goal with true re-planning.
        
        Implements: observe → decide (with full history) → act → repeat
        
        On each step, passes complete execution_history and failure_history
        to HybridPlanner for intelligent decision making.
        
        Args:
            user_goal: Natural language goal description
            max_steps: Maximum steps before stopping (default 20)
            
        Returns:
            Structured result dict with:
            {
              "goal": user_goal,
              "steps_taken": N,
              "final_status": "completed|max_steps_reached|error|loop_detected",
              "execution_history": [...],
              "summary": "Human readable explanation"
            }
        """
        self._logger.info(f"Starting autonomous goal loop: {user_goal}")
        self._logger.info(f"Max steps: {max_steps}")
        
        # Initialize state
        self._execution_history = []
        self._failure_history = []
        self._conversation_history = []
        steps_taken = 0
        final_status = "completed"
        error_message = None
        
        try:
            # Add goal to conversation for context
            self._add_to_history("user", user_goal)
            
            # Main loop: observe → decide (with history) → act
            for step_num in range(max_steps):
                self._logger.info(f"Step {step_num + 1}/{max_steps}")
                
                try:
                    # 1. Observe page
                    observation = await self._observe_page()
                    
                    # 2. Ask primary planner (LLM or deterministic)
                    raw_decision = await self.planner.replan_next_action(
                        goal=user_goal,
                        page_state=observation,
                        history=self._execution_history,
                        failures=self._failure_history
                    )
                    decision: ActionDecision = raw_decision
                    
                    decision_dict = decision.to_dict() if hasattr(decision, 'to_dict') else vars(decision)
                    
                    # 3. Validate decision schema
                    if not self._is_valid_decision(decision_dict):
                        print("[Arbitration] Invalid LLM decision → falling back to HybridPlanner")
                        decision = await self.fallback_planner.replan_next_action(
                            goal=user_goal,
                            page_state=observation,
                            history=self._execution_history,
                            failures=self._failure_history
                        )
                        decision_dict = decision.to_dict() if hasattr(decision, 'to_dict') else vars(decision)
                    
                    # 4. Selector Safety Check
                    if decision_dict.get("action") in ["click", "type"]:
                        selector = decision_dict.get("target_selector") or decision_dict.get("selector")
                        if not selector:
                            print("[Safety] Missing selector → fallback")
                            decision = await self.fallback_planner.replan_next_action(
                                goal=user_goal,
                                page_state=observation,
                                history=self._execution_history,
                                failures=self._failure_history
                            )
                            decision_dict = decision.to_dict() if hasattr(decision, 'to_dict') else vars(decision)
                    
                    # 6. Loop Detection Reinforcement
                    recent_history = list(self._execution_history[-3:])
                    if len(self._execution_history) >= 3:
                        if all(
                            step.get("decision", {}).get("action") == decision_dict.get("action") and 
                            (step.get("decision", {}).get("target_selector") == decision_dict.get("target_selector"))
                            for step in recent_history
                        ):
                            decision = await self.fallback_planner.replan_next_action(
                                goal=user_goal,
                                page_state=observation,
                                history=self._execution_history,
                                failures=self._failure_history
                            )
                            decision_dict = decision.to_dict() if hasattr(decision, 'to_dict') else vars(decision)
                    
                    # 5. Logging (IMPORTANT)
                    print(f"[Planner] {self.planner.__class__.__name__}")
                    print(f"[Decision] Action={decision_dict.get('action')} Selector={decision_dict.get('target_selector') or decision_dict.get('selector')}")
                    print(f"[Reason] {decision_dict.get('explanation','N/A')}")
                    
                    # ====================================================
                    # ACT: Execute the action
                    # ====================================================
                    self._logger.debug(f"Executing action: {decision.action}...")
                    execution_result = await self.executor.execute(decision, self.page)
                    
                    # Update conversation history with action
                    action_summary = f"Executed: {decision.action}"
                    if decision.target_selector:
                        action_summary += f" on {decision.target_selector}"
                    self._add_to_history("assistant", action_summary)
                    
                    self._logger.info(
                        f"Execution result: {execution_result['status']}"
                    )
                    
                    # ====================================================
                    # RECORD: Store both execution and failures
                    # ====================================================
                    record = {
                        "timestamp": datetime.now().isoformat(),
                        "step": step_num + 1,
                        "decision": {
                            "action": decision.action,
                            "target_selector": decision.target_selector,
                            "input_text": decision.input_text,
                            "confidence": decision.confidence,
                            "explanation": decision.explanation,
                            "thought": decision.thought,
                        },
                        "execution": {
                            "status": execution_result.get("status"),
                            "action": execution_result.get("action"),
                            "selector": execution_result.get("selector"),
                            "details": execution_result.get("details", ""),
                        }
                    }
                    
                    self._execution_history.append(record)
                    
                    # Track failures separately for HybridPlanner's re-planning
                    if execution_result.get("status") == "failed":
                        self._failure_history.append(record)
                        self._logger.debug(
                            f"Failure recorded for selector: {execution_result.get('selector', 'unknown')}"
                        )
                    
                    steps_taken += 1
                    
                    # ====================================================
                    # EARLY EXIT: Last 2 actions failed (failure safety)
                    # ====================================================
                    if len(self._execution_history) >= 2:
                        last_two = list(self._execution_history[-2:])
                        if all(step.get("execution", {}).get("status") == "failed" 
                               for step in last_two):
                            self._logger.warning("Consecutive failures detected - stopping agent")
                            final_status = "error"
                            error_message = "Consecutive action failures - cannot proceed"
                            break
                    
                    # ====================================================
                    # CHECK: Has goal been achieved?
                    # ====================================================
                    if decision.action.lower() == "finish":
                        self._logger.info("Goal achieved (finish action)")
                        self._add_to_history(
                            "assistant",
                            f"Goal achieved: {user_goal}"
                        )
                        final_status = "completed"
                        break
                    
                    # ====================================================
                    # LOOP DETECTION: Prevent infinite loops
                    # ====================================================
                    if self.executor.detect_action_loop(LOOP_DETECTION_WINDOW):
                        self._logger.warning("Loop detected - stopping agent")
                        final_status = "loop_detected"
                        break
                    
                    # ====================================================
                    # DELAY: Brief pause before next step
                    # ====================================================
                    await asyncio.sleep(STEP_DELAY)
                
                except Exception as step_error:
                    self._logger.error(
                        f"Step {step_num + 1} error: {str(step_error)}",
                        exc_info=True
                    )
                    error_message = str(step_error)
                    final_status = "error"
                    break
            
            # ================================================================
            # MAX STEPS CHECK
            # ================================================================
            if steps_taken >= max_steps:
                self._logger.warning(f"Reached max steps: {max_steps}")
                final_status = "max_steps_reached"
            
        except Exception as e:
            self._logger.error(f"Goal execution failed: {str(e)}", exc_info=True)
            final_status = "error"
            error_message = str(e)
        
        # ====================================================================
        # GENERATE RESULT with full histories
        # ====================================================================
        result = await self._generate_result(
            user_goal=user_goal,
            steps_taken=steps_taken,
            final_status=final_status,
            error=error_message
        )
        
        self._logger.info(
            f"Goal loop completed: {final_status} ({steps_taken} steps, "
            f"{len(self._failure_history)} failures)"
        )
        
        return result
    
    # ========================================================================
    # Validation & Safety (Hybrid Arbitration)
    # ========================================================================
    
    def _is_valid_decision(self, decision: dict) -> bool:
        if not isinstance(decision, dict):
            return False
        if "action" not in decision:
            return False
        if decision["action"] not in ["click", "type", "scroll", "finish"]:
            return False
        return True
    
    def _is_selector_safe(self, decision: dict, page_state: Dict[str, Any]) -> bool:
        """
        Check if selector is valid for action that requires it.
        
        Args:
            decision: Decision dict or ActionDecision object
            page_state: Current page state from analyzer
            
        Returns:
            Boolean indicating if selector is safe
        """
        try:
            # Handle both dict and ActionDecision object
            if hasattr(decision, '__dict__'):
                decision_dict = decision.__dict__
                action = decision_dict.get("action", "").lower()
                selector = decision_dict.get("target_selector")
            else:
                decision_dict = decision
                action = decision_dict.get("action", "").lower()
                selector = decision_dict.get("selector")
            
            # Actions that require selector
            selector_required_actions = ["click", "type"]
            
            if action not in selector_required_actions:
                # scroll, read, wait, navigate, finish don't need selector validation
                return True
            
            # Validate selector exists for required actions
            if not selector:
                self._logger.warning(f"[Safety] {action} requires selector but got None")
                return False
            
            if isinstance(selector, str) and selector.strip() == "":
                self._logger.warning(f"[Safety] {action} has empty selector: '{selector}'")
                return False
            
            return True
        except Exception as e:
            self._logger.error(f"Error checking selector safety: {e}")
            return False
    
    # ========================================================================
    # Core Loop Steps
    # ========================================================================
    
    async def _observe_page(self) -> Dict[str, Any]:
        """
        Observe current page state using PageAnalyzer.
        
        Validates analyzer and page before attempting analysis.
        
        Returns:
            Structured page state dict or empty state on error
        """
        try:
            # Validate analyzer exists and has valid page
            if not self.analyzer or not self.analyzer.page:
                self._logger.error("[Observation Error] PageAnalyzer or page reference is None")
                return self._empty_page_state()
                
            page_state = await self.analyzer.analyze_page()
            self._logger.debug(
                f"Page observed: {page_state.get('url', 'unknown')} - "
                f"{len(page_state.get('links', []))} links, "
                f"{len(page_state.get('buttons', []))} buttons"
            )
            return page_state
        except Exception as e:
            self._logger.error(f"[Observation Error] Page analysis failed: {type(e).__name__}: {e}")
            return self._empty_page_state()
    
    # ========================================================================
    # History & Tracking
    # ========================================================================
    
    def _record_step(
        self,
        decision: ActionDecision,
        result: Dict[str, Any]
    ):
        """
        DEPRECATED: Use structured record building in run_goal instead.
        
        Record step in execution history (legacy method).
        
        Args:
            decision: ActionDecision made
            result: ActionExecutor result
        """
        step_record = {
            "timestamp": datetime.now().isoformat(),
            "decision": {
                "action": decision.action,
                "selector": decision.target_selector,
                "confidence": decision.confidence,
                "explanation": decision.explanation,
            },
            "execution": {
                "status": result.get("status"),
                "details": result.get("details", ""),
            }
        }
        
        self._execution_history.append(step_record)
        self._logger.debug(f"Step recorded: {len(self._execution_history)} total")
    
    def _add_to_history(self, role: str, content: str):
        """
        Add message to conversation history.
        
        Args:
            role: "user" or "assistant"
            content: Message text
        """
        self._conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
    
    # ========================================================================
    # Result Generation
    # ========================================================================
    
    async def _generate_result(
        self,
        user_goal: str,
        steps_taken: int,
        final_status: str,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate final result dict with summary.
        
        Args:
            user_goal: Original user goal
            steps_taken: Number of steps executed
            final_status: Terminal status
            error: Optional error message
            
        Returns:
            Structured result dict
        """
        # Generate summary
        summary = await self._generate_summary(
            user_goal=user_goal,
            steps_taken=steps_taken,
            final_status=final_status,
            error=error
        )
        
        result = {
            "goal": user_goal,
            "steps_taken": steps_taken,
            "final_status": final_status,
            "execution_history": self._execution_history,
            "summary": summary,
            "timestamp": datetime.now().isoformat(),
        }
        
        if error:
            result["error"] = error
        
        return result
    
    async def _generate_summary(
        self,
        user_goal: str,
        steps_taken: int,
        final_status: str,
        error: Optional[str] = None
    ) -> str:
        """
        Generate human-readable summary of execution.
        
        TODO: Use ChatResponder + LLM for more sophisticated summaries
        
        Args:
            user_goal: Original goal
            steps_taken: Number of steps
            final_status: Terminal status
            error: Optional error
            
        Returns:
            Summary string
        """
        # Simple template-based summary (placeholder for LLM later)
        if final_status == "completed":
            summary = f"✓ Successfully completed goal: {user_goal}"
        elif final_status == "max_steps_reached":
            summary = (
                f"Reached maximum steps ({steps_taken}) attempting: {user_goal}. "
                "Goal may not be fully achieved."
            )
        elif final_status == "loop_detected":
            summary = (
                f"Detected repetitive action loop after {steps_taken} steps. "
                "Stopped to prevent infinite loop while attempting: {user_goal}"
            )
        elif final_status == "error":
            summary = f"Error during execution: {error or 'Unknown error'}"
        else:
            summary = f"Execution completed with status: {final_status}"
        
        # TODO: Integrate ChatResponder for LLM-based summaries:
        # if self.llm_client:
        #     summary = await self._summarize_with_llm(
        #         goal=user_goal,
        #         history=self._execution_history,
        #         status=final_status
        #     )
        
        return summary
    
    # ========================================================================
    # Utilities
    # ========================================================================
    
    def _empty_page_state(self) -> Dict[str, Any]:
        """
        Return empty page state when analysis fails.
        
        Returns:
            Minimal page state dict
        """
        return {
            "url": "unknown",
            "title": "Page not available",
            "main_text_summary": "",
            "headings": [],
            "links": [],
            "buttons": [],
            "inputs": [],
            "analysis_timestamp": datetime.now().isoformat(),
        }
    
    def get_execution_history(self) -> List[Dict[str, Any]]:
        """
        Get full execution history.
        
        Returns:
            List of step records (all actions)
        """
        return self._execution_history.copy()
    
    def get_failure_history(self) -> List[Dict[str, Any]]:
        """
        Get failure history (for debugging and analysis).
        
        Returns:
            List of failed step records
        """
        return self._failure_history.copy()
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """
        Get conversation history.
        
        Returns:
            List of conversation messages
        """
        return self._conversation_history.copy()
    
    def clear_history(self):
        """Clear all history (execution, failures, and conversation)."""
        self._execution_history = []
        self._failure_history = []
        self._conversation_history = []
        self.executor.clear_history()
        self._logger.debug("Controller history cleared (execution, failures, conversation)")
    
    # ========================================================================
    # Future Hooks (TODO)
    # ========================================================================
    
    # TODO: Implement ChatResponder integration for conversational replies
    # async def _chat_respond(self, message: str) -> str:
    #     """Generate conversational response using LLM."""
    #     if not self.llm_client:
    #         return "No LLM client available"
    #     response = self.llm_client.generate_response(
    #         prompt=message,
    #         temperature=0.7
    #     )
    #     return response
    
    # TODO: Add human approval checkpoints
    # async def _request_approval(self, action: ActionDecision) -> bool:
    #     """Request human approval before executing action."""
    #     # This would pause execution and wait for user confirmation
    #     pass
    
    # TODO: Support mode switching (controlled vs autonomous)
    # async def run_with_approval(self, user_goal: str):
    #     """Run with human-in-the-loop approval."""
    #     # Each action would require approval before execution
    #     pass
