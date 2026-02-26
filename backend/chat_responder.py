"""
Conversational cognition layer for autonomous browser automation.

Generates human-friendly explanations for:
- Agent decisions (why an action was chosen)
- Action execution results (what happened)
- Task completion summaries (final report)

Uses LM Studio LLM for natural language generation with
graceful fallbacks to rule-based templates.

Author: Agent System
Date: 2026-02-25
Version: 1.0.0
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from .planner import ActionDecision
from .llm_client import LLMClient
from .utils.logger import get_logger


logger = get_logger(__name__)


# ============================================================================
# Constants
# ============================================================================

EXPLANATION_TEMPERATURE = 0.3  # Deterministic responses
EXPLANATION_MAX_TOKENS = 150
EXPLANATION_TIMEOUT = 5.0  # seconds

# Action → Human-readable mapping
ACTION_DESCRIPTIONS = {
    "click": "clicking",
    "type": "entering information",
    "read": "reading",
    "scroll": "scrolling",
    "wait": "waiting",
    "navigate": "navigating",
    "finish": "completing",
}

# Status → Message mapping
STATUS_MESSAGES = {
    "success": "worked well",
    "failed": "had an issue",
    "completed": "is done",
}


# ============================================================================
# ChatResponder Class
# ============================================================================

class ChatResponder:
    """
    Generates conversational explanations for autonomous agent actions.
    
    Translates raw automation decisions and results into human-friendly
    natural language using LLM with graceful fallbacks.
    
    Capabilities:
    - Explain why an action was chosen
    - Explain execution results
    - Summarize task completion
    
    Attributes:
        llm_client: LLMClient instance for LLM generation
        _logger: Configured logger instance
    """
    
    def __init__(self, llm_client: LLMClient):
        """
        Initialize chat responder.
        
        Args:
            llm_client: LLMClient instance for LLM calls
        """
        self.llm_client = llm_client
        self._logger = get_logger(f"chat_responder.{id(self)}")
        self._logger.debug("ChatResponder initialized")
    
    async def explain_decision(
        self,
        goal: str,
        decision: ActionDecision,
        page_state: Dict[str, Any]
    ) -> str:
        """
        Generate human-friendly explanation for a decision.
        
        Example output:
        "I found a button labeled 'Enroll' that matches your goal,
        so I'm clicking it to proceed."
        
        Args:
            goal: User's goal
            decision: ActionDecision made by planner
            page_state: Current page state
            
        Returns:
            Natural language explanation (max 2 sentences)
        """
        self._logger.debug(
            f"Explaining decision: {decision.action} "
            f"(confidence: {decision.confidence:.2f})"
        )
        
        try:
            # Build explanation prompt
            prompt = self._build_decision_prompt(goal, decision, page_state)
            
            # Generate explanation via LLM
            explanation = await self._call_llm_with_timeout(prompt)
            
            # Validate and clean response
            explanation = self._clean_response(explanation)
            
            if not explanation:
                raise ValueError("Empty response from LLM")
            
            self._logger.debug(f"Generated explanation: {explanation[:100]}...")
            return explanation
        
        except Exception as e:
            self._logger.warning(f"LLM explanation failed: {e}, using fallback")
            fallback = self._fallback_decision_explanation(decision)
            return fallback
    
    async def explain_execution_result(
        self,
        decision: ActionDecision,
        result: Dict[str, Any]
    ) -> str:
        """
        Generate explanation for action execution result.
        
        Example output:
        "The click was successful and the page has updated with new content."
        
        Args:
            decision: Original ActionDecision
            result: ActionExecutor result dict
            
        Returns:
            Natural language explanation (max 2 sentences)
        """
        self._logger.debug(
            f"Explaining result: {result.get('status')} for {decision.action}"
        )
        
        try:
            # Build result explanation prompt
            prompt = self._build_result_prompt(decision, result)
            
            # Generate explanation
            explanation = await self._call_llm_with_timeout(prompt)
            
            # Clean and validate
            explanation = self._clean_response(explanation)
            
            if not explanation:
                raise ValueError("Empty response from LLM")
            
            self._logger.debug(f"Generated result explanation: {explanation[:100]}...")
            return explanation
        
        except Exception as e:
            self._logger.warning(f"LLM result explanation failed: {e}, using fallback")
            fallback = self._fallback_result_explanation(decision, result)
            return fallback
    
    async def summarize_run(
        self,
        goal: str,
        execution_history: List[Dict[str, Any]],
        final_status: str,
        steps_taken: int = 0
    ) -> str:
        """
        Generate comprehensive summary of task execution.
        
        Example output:
        "I successfully found and opened the free Python course page.
        The course includes comprehensive tutorials and hands-on projects."
        
        Args:
            goal: Original user goal
            execution_history: List of step records
            final_status: Final completion status
            steps_taken: Number of steps taken
            
        Returns:
            Human-readable summary (2-4 sentences)
        """
        self._logger.debug(
            f"Summarizing run: {final_status} ({steps_taken} steps)"
        )
        
        try:
            # Build summary prompt
            prompt = self._build_summary_prompt(
                goal=goal,
                execution_history=execution_history,
                final_status=final_status,
                steps_taken=steps_taken
            )
            
            # Generate summary
            summary = await self._call_llm_with_timeout(prompt)
            
            # Clean and validate
            summary = self._clean_response(summary)
            
            if not summary:
                raise ValueError("Empty response from LLM")
            
            self._logger.debug(f"Generated summary: {summary[:100]}...")
            return summary
        
        except Exception as e:
            self._logger.warning(f"LLM summary failed: {e}, using fallback")
            fallback = self._fallback_summary(goal, final_status, steps_taken)
            return fallback
    
    # ========================================================================
    # Prompt Builders
    # ========================================================================
    
    def _build_decision_prompt(
        self,
        goal: str,
        decision: ActionDecision,
        page_state: Dict[str, Any]
    ) -> str:
        """
        Build prompt for decision explanation.
        
        Args:
            goal: User goal
            decision: ActionDecision
            page_state: Page state
            
        Returns:
            Formatted prompt
        """
        action = ACTION_DESCRIPTIONS.get(decision.action, decision.action)
        
        # Extract relevant page elements for context
        page_context = self._extract_page_context(page_state, decision)
        
        prompt = f"""You are an intelligent browser automation assistant.

Explain clearly and concisely why this action was chosen.

GOAL: {goal}

NEXT ACTION: {decision.action}
CONFIDENCE: {decision.confidence * 100:.0f}%
REASONING: {decision.explanation}

PAGE CONTEXT: {page_context}

Generate a brief, friendly 1-2 sentence explanation of why this action makes sense.
Do NOT mention selectors or technical details.
Use natural, conversational language.
Keep it under 150 characters.

Explanation:"""
        
        return prompt
    
    def _build_result_prompt(
        self,
        decision: ActionDecision,
        result: Dict[str, Any]
    ) -> str:
        """
        Build prompt for result explanation.
        
        Args:
            decision: Original ActionDecision
            result: ActionExecutor result
            
        Returns:
            Formatted prompt
        """
        action = ACTION_DESCRIPTIONS.get(decision.action, decision.action)
        status = result.get("status", "unknown")
        details = result.get("details", "")
        
        prompt = f"""You are an intelligent browser automation assistant.

Explain what happened when performing an action.

ACTION TAKEN: {decision.action} ({action})
RESULT STATUS: {status}
RESULT DETAILS: {details}

Generate a brief, friendly 1-2 sentence explanation of the result.
Be encouraging if successful, helpful if there was an issue.
Use natural, conversational language.
Keep it under 150 characters.

Explanation:"""
        
        return prompt
    
    def _build_summary_prompt(
        self,
        goal: str,
        execution_history: List[Dict[str, Any]],
        final_status: str,
        steps_taken: int
    ) -> str:
        """
        Build prompt for run summary.
        
        Args:
            goal: Original goal
            execution_history: Step history
            final_status: Final status
            steps_taken: Number of steps
            
        Returns:
            Formatted prompt
        """
        # Extract action sequence
        actions: List[str] = [
            str(step.get("decision", {}).get("action") or "unknown")
            for step in execution_history[:10]  # Limit to first 10
        ]
        action_sequence = " → ".join([ACTION_DESCRIPTIONS.get(a, a) for a in actions])
        
        # Status description
        status_desc = {
            "completed": "successfully completed",
            "max_steps_reached": "reached maximum attempts",
            "loop_detected": "detected a repetitive pattern",
            "error": "encountered an error",
        }.get(final_status, final_status)
        
        prompt = f"""You are an intelligent browser automation assistant.

Summarize what happened during task execution.

USER GOAL: {goal}
FINAL STATUS: {status_desc}
STEPS TAKEN: {steps_taken}
ACTION SEQUENCE: {action_sequence}

Generate a brief, friendly 2-3 sentence summary of the execution.
If successful, describe what was accomplished.
If there were issues, be helpful and supportive.
Use natural, conversational language.

Summary:"""
        
        return prompt
    
    # ========================================================================
    # LLM Interaction
    # ========================================================================
    
    async def _call_llm_with_timeout(self, prompt: str) -> str:
        """
        Call LLM with timeout and error handling.
        
        Args:
            prompt: Prompt to send
            
        Returns:
            LLM response text
            
        Raises:
            Exception: If LLM call fails
        """
        try:
            response = await asyncio.wait_for(
                self._call_llm(prompt),
                timeout=EXPLANATION_TIMEOUT
            )
            return response
        except asyncio.TimeoutError:
            self._logger.warning("LLM explanation timeout")
            raise TimeoutError("LLM response timeout")
        except Exception as e:
            self._logger.warning(f"LLM call failed: {e}")
            raise
    
    async def _call_llm(self, prompt: str) -> str:
        """
        Call LLM client (async wrapper).
        
        Args:
            prompt: Prompt to send
            
        Returns:
            LLM response
        """
        # Run in executor to avoid blocking
        return await asyncio.to_thread(
            self.llm_client.generate_response,
            prompt=prompt,
            temperature=EXPLANATION_TEMPERATURE,
            max_tokens=EXPLANATION_MAX_TOKENS
        )
    
    # ========================================================================
    # Response Processing
    # ========================================================================
    
    def _clean_response(self, response: str) -> str:
        """
        Clean and validate LLM response.
        
        Args:
            response: Raw response from LLM
            
        Returns:
            Cleaned response text
        """
        if not response:
            return ""
        
        # Strip whitespace and quotes
        response = response.strip().strip('"\'')
        
        # Remove technical terms (selectors, etc.)
        response = self._remove_selectors(response)
        
        # Limit length
        if len(response) > 300:
            response = response[:300].rstrip() + "..."
        
        return response
    
    def _remove_selectors(self, text: str) -> str:
        """
        Remove CSS selectors and technical markers.
        
        Args:
            text: Text to clean
            
        Returns:
            Cleaned text
        """
        # Remove patterns like #id, .class, [attr]
        import re
        text = re.sub(r'#[\w-]+', '', text)
        text = re.sub(r'\.[\w-]+', '', text)
        text = re.sub(r'\[[\w-]+\]', '', text)
        return text
    
    # ========================================================================
    # Fallback Functions (CRITICAL)
    # ========================================================================
    
    def _fallback_decision_explanation(self, decision: ActionDecision) -> str:
        """
        Rule-based fallback explanation for decisions.
        
        Args:
            decision: ActionDecision
            
        Returns:
            Explanation text
        """
        action = ACTION_DESCRIPTIONS.get(decision.action, decision.action)
        
        explanations = {
            "click": f"I found a relevant button to click based on your goal.",
            "type": f"I located a search field and will enter your query.",
            "read": f"I'm reading the page to find relevant information.",
            "scroll": f"I'm scrolling to explore more content on this page.",
            "wait": f"I'm pausing briefly for the page to load.",
            "navigate": f"I'm navigating to the next relevant page.",
            "finish": f"I've found what you were looking for!",
        }
        
        return explanations.get(
            decision.action,
            "I am performing the next step to move closer to your goal."
        )
    
    def _fallback_result_explanation(
        self,
        decision: ActionDecision,
        result: Dict[str, Any]
    ) -> str:
        """
        Rule-based fallback explanation for results.
        
        Args:
            decision: Original ActionDecision
            result: ActionExecutor result
            
        Returns:
            Explanation text
        """
        action = ACTION_DESCRIPTIONS.get(decision.action, decision.action)
        status = result.get("status", "unknown")
        
        if status == "success":
            explanations = {
                "click": "The click was successful and the page has updated.",
                "type": "I've entered the information successfully.",
                "read": "I've analyzed the page content.",
                "scroll": "I've scrolled to show more content.",
                "navigate": "I've navigated to the page successfully.",
                "finish": "The task is complete!",
            }
            return explanations.get(
                decision.action,
                "That action completed successfully."
            )
        elif status == "completed":
            return "The task has been completed successfully."
        else:  # failed
            return "That action encountered an issue. Let me try another approach."
    
    def _fallback_summary(
        self,
        goal: str,
        final_status: str,
        steps_taken: int
    ) -> str:
        """
        Rule-based fallback summary.
        
        Args:
            goal: Original goal
            final_status: Final status
            steps_taken: Number of steps
            
        Returns:
            Summary text
        """
        summaries = {
            "completed": f"✓ I successfully worked on your request: {goal}",
            "max_steps_reached": f"I attempted to complete your request ({goal}) but reached my attempt limit. You may need to refine the request.",
            "loop_detected": f"I was working on '{goal}' but detected a repetitive pattern, so I stopped to prevent an infinite loop.",
            "error": f"I encountered an error while trying to complete: {goal}",
        }
        
        return summaries.get(
            final_status,
            f"Task execution completed with status: {final_status}"
        )
    
    # ========================================================================
    # Utilities
    # ========================================================================
    
    def _extract_page_context(
        self,
        page_state: Dict[str, Any],
        decision: ActionDecision
    ) -> str:
        """
        Extract human-readable page context for prompt.
        
        Args:
            page_state: Page state dict
            decision: ActionDecision
            
        Returns:
            Context description
        """
        context_parts = []
        
        # Add title
        title = page_state.get("title")
        if title and title != "Unknown":
            context_parts.append(f"Page: {title}")
        
        # Add relevant elements for decision
        if decision.action == "click":
            # Find the element being clicked
            found_click_target = False
            for btn in page_state.get("buttons", []):
                btn_item: Dict[str, Any] = btn
                if btn_item.get("selector") == decision.target_selector:
                    context_parts.append(f"Button: {btn_item.get('text', 'button')}")
                    found_click_target = True
                    break
            if not found_click_target:
                for link in page_state.get("links", []):
                    link_item: Dict[str, Any] = link
                    if link_item.get("selector") == decision.target_selector:
                        context_parts.append(f"Link: {link_item.get('text', 'link')}")
                        break
        
        elif decision.action == "type":
            # Find the input field
            for inp in page_state.get("inputs", []):
                if inp.get("selector") == decision.target_selector:
                    placeholder = inp.get("placeholder") or inp.get("name", "input field")
                    context_parts.append(f"Input: {placeholder}")
                    break
        
        # Add visible text summary
        text = page_state.get("main_text_summary", "")
        if text:
            context_parts.append(f"Content: {text[:100]}...")
        
        return " | ".join(context_parts) if context_parts else "Standard web page"
