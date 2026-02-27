"""
Production-grade orchestration layer for unified agent operation.

This module provides the central control engine (AgentOrchestrator) that routes
user messages into three execution modes:
  1. Chat - Conversational responses via LLM
  2. Controlled Automation - Human-approved deterministic browser automation
  3. Autonomous Goal - LLM-driven reasoning loop with safety constraints

Key responsibilities:
  - Intent detection and routing
  - Conversation context management
  - Approval workflow coordination
  - Safety enforcement (loop detection, drift detection, deduplication)
  - Conversational status updates during execution
  - Structured execution reporting

Author: Agent System
Date: 2026-02-25
Version: 1.0.0
"""

import json
import logging
import traceback
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

from .models.schemas import ActionPlan, ExecutionReport, StreamingMessage
from .llm_client import LLMClient
from .planner import Planner, GoalPlanner
from .executor import Executor, AutonomousGoalExecutor
from .agent_controller import AutonomousAgentController
from .validation_agent import ValidationAgent
from .memory import MemoryManager
from .tools import registry as tool_registry


# ============================================================================
# Constants & Configuration
# ============================================================================

# Safety constraints
MAX_ITERATIONS = 10
MAX_DUPLICATE_ACTIONS = 2
NAVIGATION_DRIFT_THRESHOLD = 3  # Number of navigation attempts before abort
MEMORY_WINDOW_SIZE = 20  # Number of recent steps to track for loop detection

# Intent keywords
AUTOMATION_KEYWORDS = {
    "open", "search", "click", "navigate", "read", "extract",
    "find", "list", "download", "upload", "fill", "select",
    "scroll", "wait", "submit", "enter", "go to", "visit",
    "browse", "access", "type", "press", "check", "uncheck",
    "verify", "screenshot", "refresh"
}

AUTONOMOUS_KEYWORDS = {
    "find best", "research", "explore", "compare", "analyze",
    "keep trying", "investigate", "discover", "summarize",
    "evaluate", "rank", "recommend", "find all", "collect"
}

# Conversational status messages
STATUS_MESSAGES = {
    "open_url": "Opening the website...",
    "search": "Searching for information...",
    "click": "Clicking on the element...",
    "extract": "Analyzing the current page...",
    "scroll": "Scrolling to view more content...",
    "fill_input": "Entering information...",
    "wait": "Waiting for the page to load...",
    "navigate_back": "Going back to the previous page...",
    "observing": "Analyzing the current page to understand context...",
    "deciding": "Thinking about the next best action...",
    "retrying": "Retrying the action once more...",
    "evaluating": "Checking if the goal is achieved...",
}


# ============================================================================
# Enums
# ============================================================================

class IntentMode(Enum):
    """Intent classification modes."""
    CHAT = "chat"
    CONTROLLED_AUTOMATION = "controlled_automation"
    AUTONOMOUS_GOAL = "autonomous_goal"


# ============================================================================
# AgentOrchestrator Class
# ============================================================================

class AgentOrchestrator:
    """
    Central orchestration engine for unified agent operation.
    
    This class acts as the decision-making layer that routes user messages
    into appropriate execution modes while maintaining safety constraints,
    conversation context, and execution reliability.
    
    Attributes:
        planner: Planner instance for generating action plans
        executor: Executor instance for running actions
        llm_client: LLMClient instance for language model interactions
        autonomous_controller: AutonomousAgentController for goal-driven loops
        conversation_history: List of conversation turns with metadata
        pending_plan: Current plan awaiting user approval
        last_observation: Last captured browser/page state
        executed_steps_memory: Recent executed steps for loop detection
        current_mode: Active operation mode
        _session_id: Unique session identifier for logging
        _logger: Configured logger instance
    """

    def __init__(
        self,
        planner: Planner,
        executor: Executor,
        llm_client: LLMClient,
        autonomous_controller: AutonomousAgentController,
        session_id: str = None,
        goal_planner: Optional[GoalPlanner] = None,
    ):
        """
        Initialize the orchestrator with required components.

        Args:
            planner: Planner instance for action plan generation
            executor: Executor instance for step execution
            llm_client: LLMClient instance for LLM interactions
            autonomous_controller: AutonomousAgentController for autonomous mode
            session_id: Optional session identifier for logging/tracking
            goal_planner: GoalPlanner for SANDHYA.AI full-tool autonomous mode
        """
        self.planner = planner
        self.executor = executor
        self.llm_client = llm_client
        self.autonomous_controller = autonomous_controller

        # SANDHYA.AI full-tool autonomous components
        self.goal_planner: GoalPlanner = goal_planner or GoalPlanner(llm_client)
        self.validation_agent: ValidationAgent = ValidationAgent(llm_client)

        # Conversation state
        self.conversation_history: List[Dict[str, Any]] = []
        self.pending_plan: Optional[ActionPlan] = None
        self.pending_goal_plan = None          # GoalPlan for new ToolRegistry path
        self.last_observation: Optional[Dict[str, Any]] = None
        self.executed_steps_memory: List[str] = []

        # Mode tracking
        self.current_mode: IntentMode = IntentMode.CHAT
        self._approval_pending = False

        # Session management
        self._session_id = session_id or self._generate_session_id()
        self._logger = self._setup_logger()

        self._logger.info(f"AgentOrchestrator initialized (session: {self._session_id})")

    # ========================================================================
    # Logging & Session Setup
    # ========================================================================

    @staticmethod
    def _generate_session_id() -> str:
        """Generate unique session identifier."""
        from time import time
        return f"session_{int(time() * 1000)}"

    def _setup_logger(self) -> logging.Logger:
        """Configure logger with session context."""
        logger = logging.getLogger(f"orchestrator.{self._session_id}")
        return logger

    def _log(self, level: str, message: str, **kwargs):
        """Log with session context."""
        log_func = getattr(self._logger, level.lower(), self._logger.info)
        context = f"[{self._session_id}] {message}"
        log_func(context, extra=kwargs)

    # ========================================================================
    # Intent Detection
    # ========================================================================

    def detect_intent(self, message: str) -> IntentMode:
        """
        Classify user message intent using rule-based heuristics.
        
        This is a fast, deterministic classification that avoids LLM calls
        for performance. It checks for keyword presence and patterns.
        
        Routing rules:
          1. If message contains autonomous keywords → autonomous_goal
          2. If message contains automation keywords → controlled_automation
          3. Otherwise → chat
        
        Args:
            message: User message to classify
            
        Returns:
            IntentMode enum indicating routing destination
        """
        message_lower = message.lower()

        # Check for autonomous goal patterns (highest specificity)
        if any(keyword in message_lower for keyword in AUTONOMOUS_KEYWORDS):
            self._log("debug", f"Intent detected: AUTONOMOUS_GOAL")
            return IntentMode.AUTONOMOUS_GOAL

        # Check for automation keywords
        if any(keyword in message_lower for keyword in AUTOMATION_KEYWORDS):
            self._log("debug", f"Intent detected: CONTROLLED_AUTOMATION")
            return IntentMode.CONTROLLED_AUTOMATION

        # Default to chat
        self._log("debug", f"Intent detected: CHAT")
        return IntentMode.CHAT

    # ========================================================================
    # Main Entry Point
    # ========================================================================

    async def handle_message(self, message: str) -> str:
        """
        Main entry point for processing user messages.
        
        Routing logic:
          1. If pending_plan exists → handle as approval/rejection
          2. Otherwise → route by detected intent
          
        This method orchestrates the entire flow:
          - Chat mode: Direct LLM response
          - Controlled automation: Plan generation + approval request
          - Autonomous goal: Safe autonomous execution loop
        
        Args:
            message: User message to process
            
        Returns:
            Conversational response string (all responses are conversational)
            
        Raises:
            Exception: Wrapped with safety error handling
        """
        try:
            self._log("info", f"Handling message: {message[:100]}...")

            # Record in conversation history
            self.conversation_history.append({
                "timestamp": datetime.now().isoformat(),
                "role": "user",
                "content": message,
            })

            # If approval is pending, handle as approval response
            if self._approval_pending:
                self._log("debug", "Processing as approval response")
                response = await self.handle_approval(message)
                return response

            # Detect intent and route
            intent = self.detect_intent(message)
            self.current_mode = intent

            # Log intent detection result
            self._log("info", f"[Orchestrator] mode={intent.value} | msg={message[:60]!r}")

            if intent == IntentMode.CHAT:
                self._log("debug", "Routing to chat mode")
                return await self._handle_chat_mode(message)

            elif intent == IntentMode.CONTROLLED_AUTOMATION:
                self._log("debug", "Routing to controlled automation mode")
                return await self._handle_controlled_automation_mode(message)

            elif intent == IntentMode.AUTONOMOUS_GOAL:
                self._log("debug", "Routing to autonomous goal mode")
                return await self._handle_autonomous_goal_mode(message)

        except Exception as e:
            self._log("error", f"Error in handle_message: {str(e)}")
            return (
                "I'm experiencing temporary local inference delay. "
                "Mixtral is running on CPU - please retry in a moment."
            )

    # ========================================================================
    # Chat Mode
    # ========================================================================

    async def _handle_chat_mode(self, message: str) -> str:
        """
        Handle conversational chat mode.
        
        Generates natural language response using LLM, optionally
        including conversation context for continuity.
        
        Args:
            message: User message
            
        Returns:
            Natural language response
        """
        self._log("info", "Entering CHAT mode")

        # Build context from recent conversation history (last 6 messages = 3 turns)
        context_messages = self.conversation_history[-6:]

        # Generate response
        try:
            # Format messages for LLM — phi-3.1-mini supports system role natively
            llm_messages = [
                {"role": "system", "content": "You are SANDHYA.AI, a helpful autonomous AI assistant. Respond naturally and concisely."}
            ]

            # Add recent conversation context
            for msg in context_messages:
                llm_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

            # Async call — proper for async context, never blocks the event loop
            self._log("debug",
                f"[Chat] → LLM | model={self.llm_client.model} | "
                f"msgs={len(llm_messages)} | max_tokens=256"
            )
            response = await self.llm_client.generate_response(
                messages=llm_messages,
                temperature=0.7,
                max_tokens=256,
            )
            self._log("debug", f"[Chat] ← LLM | chars={len(response)} | preview={response[:100]!r}")

            # Record assistant response
            self.conversation_history.append({
                "timestamp": datetime.now().isoformat(),
                "role": "assistant",
                "content": response,
                "mode": "chat",
            })

            self._log("info", "Chat response generated successfully")
            return response

        except Exception as e:
            self._log("error", f"Chat generation failed: {type(e).__name__}: {str(e)}")
            self._log("debug", traceback.format_exc())
            return f"LLM_ERROR: {type(e).__name__}: {str(e)}"

    # ========================================================================
    # Controlled Automation Mode
    # ========================================================================

    async def _handle_controlled_automation_mode(self, message: str) -> str:
        """
        Handle controlled automation with human approval.

        Uses GoalPlanner → GoalPlan → AutonomousGoalExecutor path so all
        browser actions go through the hardened ToolRegistry / BrowserSingleton.
        """
        self._log("info", "Entering CONTROLLED_AUTOMATION mode (GoalPlanner path)")

        try:
            goal_plan = await self.goal_planner.generate(message)

            if goal_plan.mode == "chat" or not goal_plan.plan:
                # Planner decided no automation needed → just reply
                return goal_plan.message or "No automation steps needed for this request."

            # Store GoalPlan as pending
            self.pending_goal_plan = goal_plan
            self.pending_plan = None        # clear legacy plan
            self._approval_pending = True

            # Build approval prompt (include deliberation if present)
            steps_text = "\n".join(
                f"  {s.step}. {s.action}: {json.dumps(s.parameters)}"
                for s in goal_plan.plan
            )

            critic_section = ""
            if goal_plan.deliberation and goal_plan.deliberation.get("critic_feedback"):
                critic_section = (
                    f"\nCritic review: {goal_plan.deliberation['critic_feedback']}\n"
                )

            return (
                f"I can help with that. Here's my plan:\n\n"
                f"{steps_text}\n"
                f"{critic_section}\n"
                f"Goal: {goal_plan.goal}\n\n"
                f"Does this look right? Reply with 'yes' to proceed or 'no' to cancel."
            )

        except Exception as e:
            self._log("error", f"Failed to generate plan: {e}")
            return (
                "I encountered an error creating an automation plan. "
                "Please refine your request and try again."
            )

    def _validate_plan(self, plan: Optional[ActionPlan]) -> Optional[str]:
        """
        Validate generated plan against safety constraints.
        
        Checks:
          - Plan is not None
          - Plan has steps
          - Step count is reasonable (≤ 10)
          - Steps are valid
        
        Args:
            plan: ActionPlan to validate
            
        Returns:
            Error message if invalid, None if valid
        """
        if plan is None:
            return (
                "I couldn't create a reliable plan for this task. "
                "Could you please be more specific about what you'd like me to do?"
            )

        if not plan.steps or len(plan.steps) == 0:
            return (
                "I couldn't determine any specific actions to take. "
                "Please provide more details about your request."
            )

        if len(plan.steps) > 10:
            return (
                f"The plan has {len(plan.steps)} steps, which exceeds my safety limit of 10. "
                "Could you break this into smaller requests?"
            )

        self._log("debug", f"Plan validation passed: {len(plan.steps)} steps")
        return None

    def _plan_to_explanation(self, original_request: str, plan: ActionPlan) -> str:
        """
        Convert structured ActionPlan into natural conversation.
        
        Args:
            original_request: User's original request
            plan: Generated ActionPlan
            
        Returns:
            Human-readable explanation requesting approval
        """
        steps_text = "\n".join(
            [f"  {i + 1}. {step.action}: {step.description or ''}"
             for i, step in enumerate(plan.steps)]
        )

        message = (
            f"I can help with that. Here's my plan:\n\n"
            f"{steps_text}\n\n"
            f"Goal: {plan.reasoning or 'Complete the requested task'}\n\n"
            f"Does this look right? Reply with 'yes' to proceed or 'no' to cancel."
        )

        return message

    # ========================================================================
    # Approval Handling
    # ========================================================================

    async def handle_approval(self, user_input: str) -> str:
        """
        Handle user approval/rejection of pending plan.
        
        If user confirms ("yes", "sure", "ok", etc.):
          1. Execute pending plan
          2. Collect execution report
          3. Generate conversational summary
        
        If user rejects ("no", "cancel", "stop", etc.):
          1. Clear pending plan
          2. Confirm cancellation
        
        Args:
            user_input: User's approval/rejection response
            
        Returns:
            Execution result or cancellation confirmation
        """
        self._log("info", "Processing approval response")

        if not self.pending_plan and not self.pending_goal_plan:
            self._log("warning", "Approval request received but no pending plan")
            return "I don't have a pending plan to execute."

        try:
            user_input_lower = user_input.lower().strip()

            # Check for approval
            approval_keywords = {"yes", "sure", "ok", "okay", "proceed", "go", "start"}
            rejection_keywords = {"no", "cancel", "stop", "quit", "abort", "don't"}

            if any(keyword in user_input_lower for keyword in approval_keywords):
                self._log("info", "Plan approved by user")
                self._log("debug", "Approval decision: APPROVED - proceeding with execution")
                return await self._execute_approved_plan()

            elif any(keyword in user_input_lower for keyword in rejection_keywords):
                self._log("info", "Plan rejected by user")
                self._log("debug", "Approval decision: REJECTED - cancelling execution")
                self.pending_plan = None
                self.pending_goal_plan = None
                self._approval_pending = False
                return "Understood. Execution cancelled as per your request."

            else:
                self._log("debug", "Ambiguous approval response, requesting clarification")
                return (
                    "I'm not sure if you want me to proceed. "
                    "Please reply with 'yes' to proceed or 'no' to cancel."
                )

        except Exception as e:
            self._log("error", f"Error in approval handling: {str(e)}")
            self.pending_plan = None
            self.pending_goal_plan = None
            self._approval_pending = False
            return f"An error occurred: {str(e)}"

    async def _execute_approved_plan(self) -> str:
        """
        Execute the approved plan through ToolRegistry (new path).

        Works with:
          - pending_goal_plan (GoalPlan) → AutonomousGoalExecutor + ToolRegistry
          - pending_plan (ActionPlan) fallback → legacy Executor (backward compat)
        """
        self._log("info", "Executing approved plan")

        try:
            self.executed_steps_memory = []

            # ── New GoalPlan path (ToolRegistry + BrowserSingleton) ──────────
            if self.pending_goal_plan is not None:
                goal_plan = self.pending_goal_plan
                self.pending_goal_plan = None
                self._approval_pending = False

                import uuid as _uuid
                task_id = str(_uuid.uuid4())[:8]
                memory = MemoryManager(self._session_id)
                memory.start_task(task_id, goal_plan.goal, "controlled")

                exec_ = AutonomousGoalExecutor(
                    tool_registry=tool_registry,
                    memory_manager=memory,
                )
                exec_.set_status_callback(lambda m: self._log("info", f"[Exec] {m}"))

                step_results = await exec_.execute_plan(goal_plan)
                memory.complete_task("controlled execution complete", iterations=1)

                successes = sum(1 for r in step_results if r["success"])
                failures  = len(step_results) - successes

                lines = []
                for r in step_results:
                    icon = "✓" if r["success"] else "✗"
                    lines.append(f"  {icon} Step {r['step']}: {r['action']} → {r['result'][:80]}")

                status_line = (
                    f"✓ All {len(step_results)} steps completed!"
                    if failures == 0
                    else f"⚠ {successes}/{len(step_results)} steps succeeded, {failures} failed."
                )

                self.conversation_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "role": "assistant",
                    "content": status_line,
                    "mode": "controlled_automation",
                })
                self._log("info", f"Controlled execution done: {status_line}")
                return f"{status_line}\n\nDetails:\n" + "\n".join(lines)

            # ── Legacy ActionPlan path (backward compat) ─────────────────────
            elif self.pending_plan is not None:
                execution_report = await self.executor.execute(self.pending_plan)
                self.pending_plan = None
                self._approval_pending = False
                return self._execution_report_to_conversation(execution_report)

            else:
                self._approval_pending = False
                return "No pending plan to execute."

        except Exception as e:
            self._log("error", f"Plan execution failed: {e}", exc_info=True)
            self.pending_goal_plan = None
            self.pending_plan = None
            self._approval_pending = False
            return f"Execution error: {type(e).__name__}: {e}"

    def _execution_report_to_conversation(self, report: ExecutionReport) -> str:
        """
        Convert structured ExecutionReport to conversational format.
        
        Args:
            report: ExecutionReport from executor
            
        Returns:
            Natural language summary of execution
        """
        if not report:
            return "Execution completed but no report was generated."

        steps_count = len(report.executed_steps) if report.executed_steps else 0
        success_count = len([s for s in (report.executed_steps or []) if s.get("success")])

        summary = (
            f"✓ Execution completed!\n\n"
            f"Summary:\n"
            f"  • Steps attempted: {steps_count}\n"
            f"  • Successful actions: {success_count}\n"
            f"  • Final status: {'Goal achieved' if success_count == steps_count else 'Partially completed'}\n\n"
        )

        if report.error_details:
            summary += f"Note: {report.error_details}\n"

        return summary

    # ========================================================================
    # Autonomous Goal Mode
    # ========================================================================

    async def _handle_autonomous_goal_mode(self, message: str) -> str:
        """
        Handle autonomous goal-driven execution with safety constraints.
        
        This mode delegates to AutonomousAgentController but wraps it with
        additional safety constraints:
          - Iteration limits
          - Step deduplication
          - Loop detection
          - Drift detection
        
        Args:
            message: Goal description
            
        Returns:
            Conversational execution report
        """
        self._log("info", "Entering AUTONOMOUS_GOAL mode")

        try:
            # Reset memory for this autonomous execution
            self.executed_steps_memory = []

            # Inform user
            opening_message = (
                f"I'll work autonomously on this goal: '{message}'\n\n"
                f"This may take multiple steps. I'll keep trying until I achieve the goal "
                f"or reach my safety limits.\n\n"
                f"Working..."
            )

            self._log("info", f"Starting autonomous execution for goal: {message}")

            # Execute autonomous goal with safety wrapping
            result = await self._safe_autonomous_execution(message)

            # Record in history
            self.conversation_history.append({
                "timestamp": datetime.now().isoformat(),
                "role": "assistant",
                "content": result,
                "mode": "autonomous_goal",
            })

            self._log("info", "Autonomous execution completed")

            return result

        except Exception as e:
            self._log("error", f"Autonomous execution failed: {str(e)}")
            return (
                f"The autonomous execution encountered an error: {str(e)}. "
                "Please try rephrasing your goal or breaking it into smaller tasks."
            )

    async def _safe_autonomous_execution(self, goal: str) -> str:
        """
        SANDHYA.AI full-tool autonomous execution loop.

        Flow for each iteration:
          1. GoalPlanner generates a structured plan (all tool categories)
          2. AutonomousGoalExecutor runs all steps using ToolRegistry
          3. ValidationAgent checks if goal is achieved
          4. If incomplete and next_plan provided → re-plan and repeat
          5. Stop at MAX_ITERATIONS or when goal is validated complete

        Returns:
            Human-readable result string.
        """
        self._log("info", "[SANDHYA] Starting full-tool autonomous execution")

        task_id = str(uuid.uuid4())[:8]
        memory = MemoryManager(self._session_id)
        memory.start_task(task_id, goal, "autonomous")

        executor = AutonomousGoalExecutor(
            tool_registry=tool_registry,
            memory_manager=memory,
        )
        executor.set_status_callback(lambda msg: self._log("info", f"[Executor] {msg}"))

        MAX_ITER = 5
        iteration = 0
        context_for_replan: Optional[str] = None
        final_reply = f"Working on: {goal}"

        try:
            while iteration < MAX_ITER:
                iteration += 1
                self._log("info", f"[SANDHYA] Iteration {iteration}/{MAX_ITER}")

                # ── 1. Plan ────────────────────────────────────────────────
                plan = await self.goal_planner.generate(
                    goal=goal,
                    context=context_for_replan,
                )
                self._log("info",
                    f"[SANDHYA] Plan: mode={plan.mode} | steps={len(plan.plan)} | "
                    f"msg={plan.message[:80]!r}"
                )

                # Chat mode → no execution needed
                if plan.mode == "chat" or not plan.plan:
                    final_reply = plan.message or "Goal resolved without execution steps."
                    break

                # ── 2. Execute ─────────────────────────────────────────────
                step_results = await executor.execute_plan(plan)

                successes = sum(1 for r in step_results if r["success"])
                failures = len(step_results) - successes
                self._log("info",
                    f"[SANDHYA] Execution done: {successes} ok / {failures} failed"
                )

                # ── 3. Validate ────────────────────────────────────────────
                validation = await self.validation_agent.validate(
                    goal=goal,
                    steps_summary=memory.steps_summary(),
                    results_summary=memory.results_summary(),
                )

                self._log("info",
                    f"[SANDHYA] Validation: completed={validation.completed} "
                    f"pct={validation.completion_pct} | {validation.reason[:80]!r}"
                )

                if validation.completed:
                    final_reply = (
                        f"✓ Goal achieved: {goal}\n\n"
                        f"{validation.reason}\n\n"
                        f"Completed in {iteration} iteration(s), "
                        f"{len(memory.steps)} steps total."
                    )
                    break

                # Not complete — prepare context for re-planning
                if validation.needs_continuation:
                    context_for_replan = (
                        f"Previous steps:\n{memory.steps_summary()}\n\n"
                        f"Results so far:\n{memory.results_summary()}\n\n"
                        f"Validation says: {validation.reason}\n"
                        f"Missing: {', '.join(validation.missing_steps)}"
                    )
                    # Override plan with validated next steps on next iteration
                    self._log("info",
                        f"[SANDHYA] Continuing with {len(validation.next_plan)} more steps"
                    )
                else:
                    # No continuation possible
                    final_reply = (
                        f"Partial completion ({validation.completion_pct}%): {goal}\n\n"
                        f"{validation.reason}"
                    )
                    break

            else:
                # Hit iteration limit
                final_reply = (
                    f"Reached iteration limit ({MAX_ITER}) for goal: {goal}\n\n"
                    f"Progress so far:\n{memory.steps_summary()}"
                )

        except Exception as e:
            self._log("error", f"[SANDHYA] Autonomous execution error: {e}", exc_info=True)
            final_reply = f"LLM_ERROR: {type(e).__name__}: {e}"

        finally:
            memory.complete_task(final_reply, iterations=iteration)

        return final_reply

    # ========================================================================
    # Safety Utilities
    # ========================================================================

    def _check_step_duplication(self, action_type: str, target: Optional[str] = None) -> bool:
        """
        Check if an action has been executed recently and too many times.
        
        Args:
            action_type: Type of action (e.g., "click", "search")
            target: Optional target identifier
            
        Returns:
            True if action is considered a duplicate loop, False otherwise
        """
        action_id = f"{action_type}:{target}" if target else action_type

        # Count occurrences in recent memory
        recent_count = self.executed_steps_memory[-MEMORY_WINDOW_SIZE:].count(action_id)

        if recent_count >= MAX_DUPLICATE_ACTIONS:
            self._log("warning", f"Step duplication detected: {action_id} (x{recent_count})")
            return True

        self.executed_steps_memory.append(action_id)
        return False

    def _detect_navigation_drift(self, current_url: str) -> bool:
        """
        Detect if navigation actions are not changing the URL.
        
        Args:
            current_url: Current page URL
            
        Returns:
            True if drift detected, False otherwise
        """
        if not self.last_observation:
            self.last_observation = {"url": current_url, "drift_attempts": 0}
            return False

        if self.last_observation.get("url") == current_url:
            drift_attempts = self.last_observation.get("drift_attempts", 0) + 1
            self.last_observation["drift_attempts"] = drift_attempts

            if drift_attempts > NAVIGATION_DRIFT_THRESHOLD:
                self._log("warning", f"Navigation drift detected ({drift_attempts} attempts)")
                return True
        else:
            # URL changed, reset counter
            self.last_observation = {"url": current_url, "drift_attempts": 0}

        return False

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """
        Retrieve full conversation history.
        
        Returns:
            List of message dicts with timestamp, role, content, mode
        """
        return self.conversation_history.copy()

    def clear_state(self):
        """Reset orchestrator state between sessions."""
        self._log("info", "Clearing orchestrator state")
        self.conversation_history = []
        self.pending_plan = None
        self.last_observation = None
        self.executed_steps_memory = []
        self.current_mode = IntentMode.CHAT
        self._approval_pending = False

    def get_session_info(self) -> Dict[str, Any]:
        """
        Get current session information.
        
        Returns:
            Dict with session_id, mode, conversation_count, pending_approval
        """
        return {
            "session_id": self._session_id,
            "current_mode": self.current_mode.value,
            "conversation_turns": len(self.conversation_history),
            "pending_approval": self._approval_pending,
            "timestamp": datetime.now().isoformat(),
        }
