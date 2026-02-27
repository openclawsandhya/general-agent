"""
Central orchestration layer for the Trial Automation Agent.

AutomationAgent acts as the brain of the system, handling:
- Intent detection (chat vs automation)
- Conversation management with history
- Human-in-the-loop approval for automation
- Plan generation and execution orchestration
"""

import re
from typing import List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from .models.schemas import ActionPlan, IntentType
from .llm_client import LLMClient
from .planner import Planner
from .executor import Executor
from .utils.logger import get_logger


logger = get_logger(__name__)


@dataclass
class Message:
    """Single message in conversation history."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ExecutionReport:
    """Report of an automation execution."""
    success: bool
    steps_completed: int
    total_steps: int
    execution_message: str
    reasoning: str
    details: Optional[str] = None


class AutomationAgent:
    """
    Central orchestration layer for the automation agent.
    Manages chat, planning, approval, and execution workflows.
    """
    
    # Keywords indicating automation requests
    AUTOMATION_KEYWORDS = {
        "open", "visit", "go to", "navigate", "search", "find", "look for",
        "click", "press", "scroll", "extract", "read", "get", "fetch",
        "type", "enter", "fill", "submit", "screenshot", "capture",
        "download", "upload", "buy", "purchase", "follow", "check"
    }
    
    def __init__(
        self,
        planner: Planner,
        executor: Executor,
        llm_client: LLMClient,
    ):
        """
        Initialize automation agent.
        
        Args:
            planner: Action plan generator
            executor: Plan executor
            llm_client: LLM for chat and planning
        """
        self.planner = planner
        self.executor = executor
        self.llm_client = llm_client
        
        self.conversation_history: List[Message] = []
        self.pending_plan: Optional[ActionPlan] = None
        self.pending_user_request: Optional[str] = None
        
        logger.info("AutomationAgent initialized")
    
    async def handle_message(self, user_message: str) -> str:
        """
        Main entry point for processing user messages.
        
        Handles both initial requests and approval confirmations.
        
        Args:
            user_message: User input message
            
        Returns:
            Agent response (conversational format)
        """
        user_message = user_message.strip()
        
        if not user_message:
            return "Please provide a message."
        
        logger.info(f"Processing message: {user_message[:50]}...")
        
        # Add to history
        self.conversation_history.append(Message(role="user", content=user_message))
        
        # If there's a pending plan, check for approval/rejection
        if self.pending_plan is not None:
            return await self._handle_approval_response(user_message)
        
        # Detect intent
        is_automation = self._is_automation_request(user_message)
        
        if is_automation:
            logger.info("Request classified as automation")
            return await self._handle_automation_request(user_message)
        else:
            logger.info("Request classified as chat")
            return await self._handle_chat_request(user_message)
    
    def _is_automation_request(self, message: str) -> bool:
        """
        Detect if message is automation request or conversational.
        
        Uses rule-based heuristics for speed (no LLM call).
        
        Args:
            message: User message
            
        Returns:
            True if automation request, False if conversational
        """
        message_lower = message.lower()
        
        # Check for automation keywords
        for keyword in self.AUTOMATION_KEYWORDS:
            if re.search(rf'\b{keyword}\b', message_lower):
                logger.debug(f"Found automation keyword: {keyword}")
                return True
        
        # Check for URL patterns
        if re.search(r'(?:https?://|www\.|\.com|\.org|\.net)', message_lower):
            logger.debug("Found URL pattern")
            return True
        
        # Command-like patterns
        if re.search(r'(?:can you|please|pls)\s+(?:open|search|find|click)', message_lower):
            logger.debug("Found command-like pattern")
            return True
        
        return False
    
    async def _handle_chat_request(self, user_message: str) -> str:
        """
        Handle conversational chat request.
        
        Args:
            user_message: User message
            
        Returns:
            LLM-generated response
        """
        logger.info("Entering chat mode")
        
        # Build context from recent history
        context_messages = self._build_context_messages(limit=5)
        
        system_prompt = (
            "You are a helpful and friendly assistant. "
            "Respond naturally to questions and requests. "
            "Keep responses concise and conversational."
        )
        
        # Format history for LLM context
        history_text = ""
        if context_messages:
            history_text = "\nRecent conversation:\n"
            for msg in context_messages:
                role = "User" if msg.role == "user" else "Assistant"
                history_text += f"{role}: {msg.content}\n"
        
        prompt = f"{history_text}\nUser: {user_message}\nAssistant:"
        
        try:
            response = self.llm_client.generate_response(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.7,
                max_tokens=512
            )
            
            response = response.strip()
            
            # Add to history
            self.conversation_history.append(Message(role="assistant", content=response))
            
            logger.info("Chat response generated successfully")
            return response
        
        except Exception as e:
            logger.error(f"Error generating chat response: {e}")
            error_response = (
                "I encountered an issue processing your request. "
                "Please try again or check the system logs."
            )
            self.conversation_history.append(Message(role="assistant", content=error_response))
            return error_response
    
    async def _handle_automation_request(self, user_message: str) -> str:
        """
        Handle automation request with human-in-the-loop approval.
        
        Generates a plan and asks for approval before proceeding.
        
        Args:
            user_message: User message
            
        Returns:
            Plan explanation and approval request
        """
        logger.info("Entering automation mode")
        
        try:
            # Generate plan
            logger.info("Generating action plan...")
            plan = self.planner.generate_plan(user_message)
            
            if not plan or not plan.steps:
                error_msg = (
                    "I couldn't generate a valid automation plan for your request. "
                    "Could you provide more details?"
                )
                self.conversation_history.append(
                    Message(role="assistant", content=error_msg)
                )
                logger.warning("Generated empty plan")
                return error_msg
            
            # Store plan for approval handling
            self.pending_plan = plan
            self.pending_user_request = user_message
            
            # Convert plan to human-readable format
            explanation = self._format_plan_explanation(plan)
            
            logger.info(f"Generated plan with {len(plan.steps)} steps")
            
            # Add to history
            self.conversation_history.append(
                Message(role="assistant", content=explanation)
            )
            
            return explanation
        
        except Exception as e:
            logger.error(f"Error in automation request handling: {e}")
            error_msg = (
                f"I encountered an error planning your automation: {str(e)}\n\n"
                "Please try reformulating your request."
            )
            self.conversation_history.append(
                Message(role="assistant", content=error_msg)
            )
            return error_msg
    
    async def _handle_approval_response(self, user_message: str) -> str:
        """
        Handle user response to approval request.
        
        Args:
            user_message: User approval message ("yes", "no", etc.)
            
        Returns:
            Execution result or cancellation message
        """
        logger.info("Handling approval response")
        
        # Check if user approved or rejected
        approval = self._parse_approval(user_message)
        
        if approval is None:
            # Ambiguous response
            clarification = (
                "I'm not sure if you want to proceed. "
                "Please respond with 'yes' to proceed or 'no' to cancel."
            )
            self.conversation_history.append(
                Message(role="assistant", content=clarification)
            )
            return clarification
        
        return await self._execute_pending_plan(approval)
    
    def _parse_approval(self, message: str) -> Optional[bool]:
        """
        Parse user message for approval or rejection.
        
        Args:
            message: User message
            
        Returns:
            True if approved, False if rejected, None if ambiguous
        """
        message_lower = message.lower().strip()
        
        # Affirmative responses
        affirmative = {"yes", "yeah", "yep", "ok", "okay", "proceed", "go", "sure", "alright"}
        if message_lower in affirmative or message_lower.startswith(("y ", "yes ")):
            return True
        
        # Negative responses
        negative = {"no", "nope", "cancel", "stop", "don't", "skip"}
        if message_lower in negative or message_lower.startswith(("n ", "no ")):
            return False
        
        return None
    
    async def _execute_pending_plan(self, approval: bool) -> str:
        """
        Execute pending plan if approved, or cancel if rejected.
        
        Args:
            approval: User approval status
            
        Returns:
            Execution result or cancellation message
        """
        if not approval:
            logger.info("Automation cancelled by user")
            self.pending_plan = None
            self.pending_user_request = None
            
            response = "Automation cancelled. How can I help you with something else?"
            self.conversation_history.append(
                Message(role="assistant", content=response)
            )
            return response
        
        if self.pending_plan is None:
            logger.error("No pending plan to execute")
            response = "Error: No plan to execute."
            self.conversation_history.append(
                Message(role="assistant", content=response)
            )
            return response
        
        logger.info(f"Executing automation with {len(self.pending_plan.steps)} steps")
        
        try:
            # Execute plan
            execution_result = await self.executor.execute(self.pending_plan)
            
            # Build report
            report = self._create_execution_report(
                execution_result,
                self.pending_plan
            )
            
            # Format response
            response = self._format_execution_report(report)
            
            # Clear pending state
            self.pending_plan = None
            self.pending_user_request = None
            
            # Add to history
            self.conversation_history.append(
                Message(role="assistant", content=response)
            )
            
            logger.info("Automation execution completed successfully")
            return response
        
        except Exception as e:
            logger.error(f"Error executing automation: {e}")
            
            # Clear pending state
            self.pending_plan = None
            self.pending_user_request = None
            
            error_response = (
                f"An error occurred during execution: {str(e)}\n\n"
                "Please try again or adjust your request."
            )
            self.conversation_history.append(
                Message(role="assistant", content=error_response)
            )
            return error_response
    
    def _format_plan_explanation(self, plan: ActionPlan) -> str:
        """
        Convert action plan into human-readable explanation.
        
        Args:
            plan: ActionPlan to explain
            
        Returns:
            Formatted explanation string
        """
        lines = ["I will perform the following steps:\n"]
        
        for i, step in enumerate(plan.steps, 1):
            if step.description:
                lines.append(f"{i}. {step.description}")
            else:
                # Fallback if no description
                action_name = step.action.replace("_", " ").title()
                if step.value:
                    lines.append(f"{i}. {action_name}: {step.value}")
                else:
                    lines.append(f"{i}. {action_name}")
        
        if plan.reasoning:
            lines.append(f"\nReasoning: {plan.reasoning}")
        
        lines.append("\n🔔 Shall I proceed? (yes/no)")
        
        return "\n".join(lines)
    
    def _create_execution_report(
        self,
        execution_message: str,
        plan: ActionPlan
    ) -> ExecutionReport:
        """
        Create execution report from results.
        
        Args:
            execution_message: Execution result message
            plan: Executed plan
            
        Returns:
            ExecutionReport object
        """
        # Parse execution message for success indicators
        success = "failed" not in execution_message.lower() and "error" not in execution_message.lower()
        
        # Count steps (assume all attempted)
        total_steps = len(plan.steps)
        steps_completed = total_steps if success else max(0, total_steps - 1)
        
        return ExecutionReport(
            success=success,
            steps_completed=steps_completed,
            total_steps=total_steps,
            execution_message=execution_message,
            reasoning=plan.reasoning or "No reasoning provided"
        )
    
    def _format_execution_report(self, report: ExecutionReport) -> str:
        """
        Format execution report for user display.
        
        Args:
            report: ExecutionReport object
            
        Returns:
            Formatted report string
        """
        lines = []
        
        if report.success:
            lines.append("✅ Automation completed successfully!\n")
        else:
            lines.append("⚠️ Automation encountered issues:\n")
        
        lines.append(report.execution_message)
        
        if report.reasoning:
            lines.append(f"\n📋 Plan reasoning: {report.reasoning}")
        
        lines.append(
            f"\n📊 Execution: {report.steps_completed}/{report.total_steps} steps completed"
        )
        
        return "\n".join(lines)
    
    def _build_context_messages(self, limit: int = 5) -> List[Message]:
        """
        Get recent conversation history for context.
        
        Args:
            limit: Maximum number of messages to return
            
        Returns:
            List of recent messages
        """
        if not self.conversation_history:
            return []
        
        # Return last N messages (excluding very long ones to avoid token bloat)
        recent = [
            msg for msg in self.conversation_history[-limit:]
            if len(msg.content) < 500  # Exclude very long messages for token efficiency
        ]
        
        return recent
    
    def clear_history(self) -> None:
        """Clear conversation history."""
        logger.info("Clearing conversation history")
        self.conversation_history = []
        self.pending_plan = None
        self.pending_user_request = None
    
    def get_history(self) -> List[dict]:
        """
        Get conversation history as list of dicts.
        
        Returns:
            List of message dicts
        """
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            }
            for msg in self.conversation_history
        ]
    
    def has_pending_approval(self) -> bool:
        """Check if awaiting user approval."""
        return self.pending_plan is not None
    
    def get_pending_plan_summary(self) -> Optional[str]:
        """
        Get summary of pending plan if one exists.
        
        Returns:
            Plan summary or None
        """
        if self.pending_plan is None:
            return None
        
        steps_list = "\n".join(
            f"  • {step.description or step.action}"
            for step in self.pending_plan.steps
        )
        
        return f"Pending automation with {len(self.pending_plan.steps)} steps:\n{steps_list}"
