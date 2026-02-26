"""
LLM-based planner for autonomous browser automation using LM Studio.

This planner uses a local LLM (served via LM Studio OpenAI-compatible API)
to make intelligent decisions about next actions.

Supports:
- URL: http://localhost:1234/v1/chat/completions
- Model: Any model running in LM Studio
- Temperature: Configurable (default 0.2 for deterministic)

Falls back to safe scroll action if LLM fails or returns invalid action.

Author: Agent System
Date: 2026-02-26
Version: 1.0.0
"""

import json
import asyncio
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

import aiohttp

from .planner import ActionDecision
from .utils.logger import get_logger


logger = get_logger(__name__)


# ============================================================================
# Constants
# ============================================================================

LM_STUDIO_DEFAULT_URL = "http://localhost:1234/v1"
DEFAULT_MODEL_NAME = "local-model"
DEFAULT_TEMPERATURE = 0.2

# LLM call timeouts
LLM_TIMEOUT = 15.0  # seconds
LLM_REQUEST_TIMEOUT = 30.0  # seconds with connection time


# ============================================================================
# Prompts
# ============================================================================

SYSTEM_PROMPT = """You are an expert autonomous browser automation agent.

Your task is to decide the NEXT BEST ACTION to achieve a goal.

You must analyze:
1. The current page state (URL, title, visible elements)
2. The goal the user wants to achieve
3. Recent action history (what worked, what failed)

Then decide the next action as a JSON object.

IMPORTANT CONSTRAINTS:
- Only return valid JSON
- action MUST be one of: click, type, scroll, wait, navigate, finish
- selector MUST be a valid CSS selector (for click/type actions)
- text is optional (only for type action)
- All fields are required

Return ONLY JSON, no other text.

Example output:
{"action": "click", "selector": "#enroll-btn", "text": null, "explanation": "Clicking enroll button to access course"}
{"action": "type", "selector": "input.search", "text": "Python", "explanation": "Searching for Python course"}
{"action": "scroll", "selector": null, "text": "down", "explanation": "Scrolling down to find more courses"}
{"action": "finish", "selector": null, "text": null, "explanation": "Goal achieved - user has access to Python course"}"""


def _build_user_prompt(
    goal: str,
    observation: Dict[str, Any],
    history: List[Dict[str, Any]]
) -> str:
    """
    Build user prompt for LLM with goal, observation, history.
    
    Args:
        goal: User goal
        observation: Current page observation
        history: Action history
        
    Returns:
        User prompt string
    """
    # Observation summary
    url = observation.get("url", "unknown")
    title = observation.get("title", "")
    text_summary = observation.get("main_text_summary", "")[:300]  # Limit text
    
    # Available elements
    buttons = observation.get("buttons", [])
    links = observation.get("links", [])
    inputs = observation.get("inputs", [])
    
    buttons_str = "\n".join(
        [f"  • {b.get('text', '')[:40]} ({b.get('selector', '')})" for b in buttons[:5]]
    ) or "  (none)"
    
    links_str = "\n".join(
        [f"  • {l.get('text', '')[:40]} ({l.get('selector', '')})" for l in links[:5]]
    ) or "  (none)"
    
    inputs_str = "\n".join(
        [f"  • {i.get('name', '')[:30]} (type: {i.get('type', 'text')})" for i in inputs[:3]]
    ) or "  (none)"
    
    # Recent history
    recent_history = history[-3:] if history else []
    history_str = "\n".join(
        [f"  Step {step.get('step', '?')}: {step.get('action', '?')} -> {step.get('result', '?')}"
         for step in recent_history]
    ) or "  (no history)"
    
    prompt = f"""GOAL: {goal}

CURRENT PAGE:
URL: {url}
Title: {title}
Text Summary: {text_summary}

AVAILABLE ELEMENTS:
Buttons:
{buttons_str}

Links:
{links_str}

Inputs:
{inputs_str}

RECENT ACTION HISTORY:
{history_str}

Your task: Decide the next best action to achieve the goal.
Return only valid JSON action."""
    
    return prompt


# ============================================================================
# LLMPlanner Class
# ============================================================================

class LLMPlanner:
    """
    LLM-based planner using LM Studio for autonomous decision making.
    
    Uses OpenAI-compatible API to call local LLM for intelligent action selection.
    Falls back to safe scroll if LLM fails.
    
    Attributes:
        model_name: Model name (e.g., "local-model")
        api_base: LM Studio API endpoint (default: http://localhost:1234/v1)
        temperature: LLM temperature (default: 0.2 for determinism)
        _logger: Configured logger
        _session: aiohttp session for API calls
    """
    
    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        api_base: str = LM_STUDIO_DEFAULT_URL,
        temperature: float = DEFAULT_TEMPERATURE
    ):
        """
        Initialize LLM planner.
        
        Args:
            model_name: Model to use (e.g., "local-model")
            api_base: LM Studio API endpoint URL
            temperature: Temperature for deterministic responses (default 0.2)
        """
        self.model_name = model_name
        self.api_base = api_base
        self.temperature = temperature
        self._logger = get_logger(f"llm_planner.{id(self)}")
        self._session: Optional[aiohttp.ClientSession] = None
        self._logger.debug(
            f"LLMPlanner initialized: model={model_name}, api={api_base}, temp={temperature}"
        )
    
    async def replan_next_action(
        self,
        goal: str,
        page_state: Dict[str, Any],
        history: List[Dict[str, Any]],
        failures: List[Dict[str, Any]]
    ) -> ActionDecision:
        """
        Decide next action using LLM (with fallback to safe action).
        
        Args:
            goal: User goal
            page_state: Current page observation
            history: Execution history (all actions)
            failures: Failure history (failed actions only)
            
        Returns:
            ActionDecision with next action
        """
        self._logger.info(f"LLM replanning for goal: {goal[:50]}...")
        
        try:
            # Prepare history for prompt
            history_dicts = [
                {
                    "step": i + 1,
                    "action": h.get("decision", {}).get("action", "unknown"),
                    "result": h.get("execution", {}).get("status", "unknown")
                }
                for i, h in enumerate(history[-5:])  # Last 5 steps
            ]
            
            # Build prompts
            user_prompt = _build_user_prompt(goal, page_state, history_dicts)
            
            self._logger.debug("Calling LM Studio API...")
            
            # Call LLM
            llm_response = await self._call_llm(user_prompt)
            
            self._logger.debug(f"LLM response (first 100 chars): {llm_response[:100]}")
            
            # Parse response
            action_dict = self._parse_llm_response(llm_response)
            
            if not action_dict:
                self._logger.warning("Failed to parse LLM response, using safe fallback")
                return self._safe_fallback_decision("Failed to parse LLM response")
            
            # Validate action
            decision = self._validate_and_build_decision(action_dict, page_state)
            
            self._logger.info(f"LLM Decision: {decision.action} (confidence: {decision.confidence:.2f})")
            return decision
        
        except Exception as e:
            self._logger.error(f"Error in LLM planning: {e}")
            return self._safe_fallback_decision(f"LLM error: {str(e)}")
    
    async def _call_llm(self, user_prompt: str) -> str:
        """
        Call LM Studio API with user prompt.
        
        Args:
            user_prompt: User message
            
        Returns:
            LLM response string
        """
        # Create session if needed
        if not self._session:
            self._session = aiohttp.ClientSession()
        
        try:
            url = f"{self.api_base}/chat/completions"
            
            payload = {
                "model": self.model_name,
                "temperature": self.temperature,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ]
            }
            
            self._logger.debug(f"Calling LLM at {url}")
            
            async with self._session.post(
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=LLM_REQUEST_TIMEOUT)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"LLM API error {response.status}: {error_text[:200]}")
                
                data = await response.json()
                
                # Extract message from response
                if "choices" in data and len(data["choices"]) > 0:
                    message = data["choices"][0].get("message", {})
                    content = message.get("content", "")
                    return content
                else:
                    raise Exception("Unexpected LLM response format")
        
        except asyncio.TimeoutError:
            raise Exception("LLM API call timeout")
        except Exception as e:
            self._logger.error(f"LLM API error: {e}")
            raise
    
    def _parse_llm_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Parse JSON from LLM response safely.
        
        Args:
            response: LLM response string
            
        Returns:
            Parsed action dict or None
        """
        try:
            # Try to find JSON in response
            json_patterns = [
                r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}",  # JSON object
            ]
            
            for pattern in json_patterns:
                matches = re.findall(pattern, response, re.DOTALL)
                for match in reversed(matches):  # Try from end
                    try:
                        parsed = json.loads(match)
                        if isinstance(parsed, dict):
                            return parsed
                    except json.JSONDecodeError:
                        continue
            
            # Try parsing entire response
            try:
                parsed = json.loads(response)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass
            
            return None
        
        except Exception as e:
            self._logger.warning(f"Error parsing LLM response: {e}")
            return None
    
    def _validate_and_build_decision(
        self,
        action_dict: Dict[str, Any],
        page_state: Dict[str, Any]
    ) -> ActionDecision:
        """
        Validate LLM output and build ActionDecision.
        
        Args:
            action_dict: Parsed LLM action
            page_state: Current page state
            
        Returns:
            Validated ActionDecision
        """
        # Extract fields
        action = (action_dict.get("action") or "scroll").lower()
        selector = action_dict.get("selector")
        text = action_dict.get("text")
        explanation = action_dict.get("explanation", "LLM decision")
        
        # Validate action is supported
        allowed_actions = {"click", "type", "scroll", "wait", "navigate", "finish"}
        
        if action not in allowed_actions:
            self._logger.warning(f"Invalid action from LLM: {action}, using scroll")
            return self._safe_fallback_decision(f"Invalid action: {action}")
        
        # Validate selector for click/type actions
        if action in ["click", "type"]:
            if not selector or not self._selector_exists(selector, page_state):
                self._logger.warning(f"Selector not found: {selector}, using scroll")
                return self._safe_fallback_decision(f"Selector not found: {selector}")
        
        # Build decision
        return ActionDecision(
            thought=f"LLM decision: {explanation[:50]}",
            action=action,
            target_selector=selector,
            input_text=text,
            confidence=0.7,  # LLM decisions have moderate confidence
            explanation=explanation[:100]
        )
    
    def _selector_exists(self, selector: str, page_state: Dict[str, Any]) -> bool:
        """
        Check if selector exists in page_state.
        
        Args:
            selector: CSS selector
            page_state: Current page state
            
        Returns:
            True if selector found
        """
        # Check links
        for link in page_state.get("links", []):
            if link.get("selector") == selector:
                return True
        
        # Check buttons
        for btn in page_state.get("buttons", []):
            if btn.get("selector") == selector:
                return True
        
        # Check inputs
        for inp in page_state.get("inputs", []):
            if inp.get("selector") == selector:
                return True
        
        return False
    
    def _safe_fallback_decision(self, reason: str) -> ActionDecision:
        """
        Return safe fallback decision (scroll).
        
        Args:
            reason: Reason for fallback
            
        Returns:
            Safe ActionDecision
        """
        return ActionDecision(
            thought=f"Fallback due to: {reason}",
            action="scroll",
            target_selector=None,
            input_text="down",
            confidence=0.3,
            explanation=f"Safe fallback: {reason[:50]}"
        )
    
    async def shutdown(self):
        """Cleanup aiohttp session."""
        if self._session:
            await self._session.close()
            self._session = None
            self._logger.debug("LLMPlanner session closed")
    
    def __del__(self):
        """Ensure session cleanup on deletion."""
        if self._session and not self._session.closed:
            try:
                asyncio.create_task(self.shutdown())
            except:
                pass
