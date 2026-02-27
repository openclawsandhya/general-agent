"""
Human-in-the-loop approval checkpoint system for autonomous automation.

Ensures high-impact tasks (shopping, enrollments, form submissions) require
explicit user approval before execution.

Enforces safety by preventing unauthorized automation actions.

Author: Agent System
Date: 2026-02-25
Version: 1.0.0
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from .models.schemas import ActionPlan, ActionStep, ActionType
from .chat_responder import ChatResponder
from .llm_client import LLMClient
from .utils.logger import get_logger


logger = get_logger(__name__)


# ============================================================================
# Enums & Data Classes
# ============================================================================

class ApprovalLevel(Enum):
    """Approval requirement levels."""
    NOT_REQUIRED = "not_required"
    RECOMMENDED = "recommended"
    REQUIRED = "required"


@dataclass
class ApprovalRequest:
    """Structure for approval requests."""
    goal: str
    plan: ActionPlan
    explanation: str
    approval_level: ApprovalLevel
    risk_assessment: str
    timestamp: str
    request_id: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "goal": self.goal,
            "plan": self.plan.dict() if self.plan else None,
            "explanation": self.explanation,
            "approval_level": self.approval_level.value,
            "risk_assessment": self.risk_assessment,
            "timestamp": self.timestamp,
            "request_id": self.request_id,
        }


# ============================================================================
# ApprovalManager Class
# ============================================================================

class ApprovalManager:
    """
    Human-in-the-loop approval checkpoint manager.
    
    Ensures high-impact automation requires explicit user approval:
    - Shopping transactions
    - Form submissions
    - Course enrollments
    - External domain navigation
    
    Lower-risk actions (read, search, scroll) proceed without approval.
    
    Attributes:
        pending_request: Current pending ApprovalRequest
        awaiting_approval: Boolean flag for approval state
        chat_responder: ChatResponder for conversational explanations
        _logger: Configured logger instance
    """
    
    # High-risk keywords that trigger approval
    HIGH_RISK_KEYWORDS = {
        "buy", "purchase", "checkout", "payment", "card", "credit",
        "submit", "enroll", "sign up", "register", "create account",
        "delete", "remove", "unsubscribe", "cancel subscription",
        "download", "upload", "install", "confirm", "verify",
    }
    
    # High-risk selectors
    HIGH_RISK_SELECTORS = {
        "button[type='submit']", "button.submit", "button.checkout",
        "button.enroll", "button.register", "a.enroll", "a.buy",
        "input[type='submit']", ".payment-btn", ".buy-btn",
    }
    
    # External domains (require approval for navigation)
    EXTERNAL_DOMAIN_KEYWORDS = {
        "paypal", "stripe", "amazon", "ebay", "shopify",
    }
    
    # Safe actions that don't require approval
    SAFE_ACTIONS = {
        ActionType.EXTRACT_TEXT,
        ActionType.SCROLL,
        ActionType.WAIT,
    }
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Initialize approval manager.
        
        Args:
            llm_client: Optional LLMClient for ChatResponder
        """
        self.pending_request: Optional[ApprovalRequest] = None
        self.awaiting_approval = False
        self.chat_responder = ChatResponder(llm_client) if llm_client else None
        self._logger = get_logger(f"approval_manager.{id(self)}")
        self._request_counter = 0
        self._logger.debug("ApprovalManager initialized")
    
    async def create_approval_request(
        self,
        goal: str,
        plan: ActionPlan,
        page_state: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, bool]:
        """
        Create approval request for a plan.
        
        Analyzes plan risk level and generates conversational message.
        
        Args:
            goal: User goal
            plan: ActionPlan to evaluate
            page_state: Optional current page state
            
        Returns:
            Tuple of (message, requires_approval)
            - message: Conversational explanation
            - requires_approval: Boolean indicating if approval needed
        """
        self._logger.info("Creating approval request")
        
        try:
            # Assess plan risk level
            approval_level, risk_assessment = self._assess_risk(plan, page_state or {})
            
            self._logger.debug(f"Risk level: {approval_level.value}")
            
            # Generate explanation
            explanation = await self._generate_explanation(goal, plan)
            
            # Create request
            request_id = self._generate_request_id()
            request = ApprovalRequest(
                goal=goal,
                plan=plan,
                explanation=explanation,
                approval_level=approval_level,
                risk_assessment=risk_assessment,
                timestamp=datetime.now().isoformat(),
                request_id=request_id,
            )
            
            # Store request
            self.pending_request = request
            
            # Determine if approval required
            requires_approval = (
                approval_level in [ApprovalLevel.REQUIRED, ApprovalLevel.RECOMMENDED]
            )
            
            if requires_approval:
                self.awaiting_approval = True
                message = await self._build_approval_message(request)
                self._logger.info(f"Approval required: {request_id}")
            else:
                message = explanation
                self._logger.info(f"Auto-approved: {request_id}")
            
            return message, requires_approval
        
        except Exception as e:
            self._logger.error(f"Error creating approval request: {e}")
            return f"Error processing request: {str(e)}", True
    
    def approve(self) -> bool:
        """
        Approve pending request.
        
        Returns:
            True if approval was successful
        """
        if not self.awaiting_approval or not self.pending_request:
            self._logger.warning("No pending request to approve")
            return False
        
        self._logger.info(f"Approving request: {self.pending_request.request_id}")
        self.awaiting_approval = False
        return True
    
    def reject(self) -> bool:
        """
        Reject pending request.
        
        Returns:
            True if rejection was successful
        """
        if not self.awaiting_approval or not self.pending_request:
            self._logger.warning("No pending request to reject")
            return False
        
        self._logger.info(f"Rejecting request: {self.pending_request.request_id}")
        self.clear()
        return True
    
    def has_pending(self) -> bool:
        """
        Check if approval is pending.
        
        Returns:
            True if waiting for user approval
        """
        return self.awaiting_approval
    
    def get_plan(self) -> Optional[ActionPlan]:
        """
        Get pending plan.
        
        Returns:
            ActionPlan if pending, None otherwise
        """
        if self.pending_request:
            return self.pending_request.plan
        return None
    
    def get_request_info(self) -> Optional[Dict[str, Any]]:
        """
        Get full pending request information.
        
        Returns:
            Request dict or None
        """
        if self.pending_request:
            return self.pending_request.to_dict()
        return None
    
    def clear(self):
        """Clear approval state."""
        self._logger.debug("Clearing approval state")
        self.pending_request = None
        self.awaiting_approval = False
    
    # ========================================================================
    # Risk Assessment
    # ========================================================================
    
    def _assess_risk(
        self,
        plan: ActionPlan,
        page_state: Dict[str, Any]
    ) -> Tuple[ApprovalLevel, str]:
        """
        Assess plan risk level.
        
        Returns approval level and risk description.
        
        Args:
            plan: ActionPlan to assess
            page_state: Current page state
            
        Returns:
            Tuple of (ApprovalLevel, risk_description)
        """
        self._logger.debug("Assessing plan risk")
        
        if not plan or not plan.steps:
            return ApprovalLevel.NOT_REQUIRED, "Empty plan"
        
        risk_factors = []
        risk_score = 0
        
        # Analyze each step
        for step in plan.steps:
            action_risk, reason = self._assess_step_risk(step, page_state)
            risk_score += action_risk
            if reason:
                risk_factors.append(reason)
        
        # Determine approval level
        if risk_score >= 8:
            return ApprovalLevel.REQUIRED, " | ".join(risk_factors)
        elif risk_score >= 5:
            return ApprovalLevel.RECOMMENDED, " | ".join(risk_factors)
        else:
            return ApprovalLevel.NOT_REQUIRED, "Low-risk actions"
    
    def _assess_step_risk(
        self,
        step: ActionStep,
        page_state: Dict[str, Any]
    ) -> Tuple[int, Optional[str]]:
        """
        Assess risk of a single step.
        
        Args:
            step: ActionStep to assess
            page_state: Current page state
            
        Returns:
            Tuple of (risk_score: 0-5, reason: optional)
        """
        risk_score = 0
        reason = None
        
        # Safe actions don't require approval
        if step.action in self.SAFE_ACTIONS:
            return 0, None
        
        # Check action type
        if step.action == ActionType.CLICK:
            risk_score += self._assess_click_risk(step, page_state)
        elif step.action == ActionType.FILL_INPUT:
            risk_score += self._assess_input_risk(step)
        elif step.action == ActionType.OPEN_URL:
            risk_score += self._assess_navigation_risk(step)
        elif step.action == ActionType.SUBMIT_FORM:
            risk_score += 5  # Form submission always high risk
            reason = "Form submission"
        
        return risk_score, reason
    
    def _assess_click_risk(
        self,
        step: ActionStep,
        page_state: Dict[str, Any]
    ) -> int:
        """
        Assess risk of click action.
        
        Args:
            step: ActionStep with click action
            page_state: Current page state
            
        Returns:
            Risk score 0-5
        """
        risk = 1  # Base risk
        
        description = (step.description or "").lower()
        
        # Check if clicking on high-risk button
        for button in page_state.get("buttons", []):
            btn_text = button.get("text", "").lower()
            if any(kw in btn_text for kw in self.HIGH_RISK_KEYWORDS):
                risk += 3
                return risk
        
        # Check description keywords
        for keyword in self.HIGH_RISK_KEYWORDS:
            if keyword in description:
                risk += 2
                return risk
        
        return risk
    
    def _assess_input_risk(self, step: ActionStep) -> int:
        """
        Assess risk of input/fill action.
        
        Args:
            step: ActionStep with fill action
            
        Returns:
            Risk score 0-5
        """
        description = (step.description or "").lower()
        
        # Payment/sensitive info is high risk
        if any(kw in description for kw in ["card", "password", "payment"]):
            return 5
        
        # Regular form input is low risk
        return 1
    
    def _assess_navigation_risk(self, step: ActionStep) -> int:
        """
        Assess risk of navigation action.
        
        Args:
            step: ActionStep with navigation
            
        Returns:
            Risk score 0-5
        """
        url = (step.value or "").lower()
        
        # External payment processors require approval
        for domain in self.EXTERNAL_DOMAIN_KEYWORDS:
            if domain in url:
                return 5
        
        # Regular navigation low risk
        return 1
    
    # ========================================================================
    # Message Generation
    # ========================================================================
    
    async def _generate_explanation(self, goal: str, plan: ActionPlan) -> str:
        """
        Generate explanation of plan steps.
        
        Args:
            goal: User goal
            plan: ActionPlan
            
        Returns:
            Human-friendly explanation
        """
        try:
            if not plan or not plan.steps:
                return "No actions planned."
            
            # Build step descriptions
            steps = []
            for step in plan.steps[:5]:  # Limit to 5 steps
                description = step.description or str(step.action)
                steps.append(f"• {description}")
            
            explanation = (
                f"I plan to:\n{chr(10).join(steps)}\n\n"
                f"This should help achieve: {goal}"
            )
            
            return explanation
        
        except Exception as e:
            self._logger.warning(f"Error generating explanation: {e}")
            return "I have a plan to proceed."
    
    async def _build_approval_message(self, request: ApprovalRequest) -> str:
        """
        Build conversational approval request message.
        
        Args:
            request: ApprovalRequest
            
        Returns:
            Message asking for approval
        """
        message = f"""{request.explanation}

Risk Assessment: {request.risk_assessment}

Would you like me to proceed? (yes/no)"""
        
        return message
    
    # ========================================================================
    # Utilities
    # ========================================================================
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID."""
        self._request_counter += 1
        return f"req_{self._request_counter}_{int(datetime.now().timestamp() * 1000)}"
    
    def can_execute(self, action: ActionType) -> bool:
        """
        Check if action can execute without approval.
        
        Args:
            action: Action type
            
        Returns:
            True if action is low-risk
        """
        return action in self.SAFE_ACTIONS
    
    def should_require_approval_for_goal(self, goal: str) -> bool:
        """
        Quick check if goal likely requires approval.
        
        Args:
            goal: User goal
            
        Returns:
            True if approval probably needed
        """
        goal_lower = goal.lower()
        
        for keyword in self.HIGH_RISK_KEYWORDS:
            if keyword in goal_lower:
                return True
        
        return False
    
    def get_approval_status_summary(self) -> str:
        """
        Get summary of current approval status.
        
        Returns:
            Status string
        """
        if not self.awaiting_approval:
            return "No pending approval"
        
        if self.pending_request:
            return (
                f"Awaiting approval for: {self.pending_request.goal} "
                f"(Risk: {self.pending_request.approval_level.value})"
            )
        
        return "Approval status unknown"
