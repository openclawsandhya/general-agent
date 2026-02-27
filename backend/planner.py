"""
Action planner that converts user requests into structured automation plans.

This module includes:
- Planner: Multi-step plan generation from user goals
- AutonomousPlanner: Single-action decision making based on page state
- GoalPlanner: SANDHYA.AI autonomous goal planner (full tool suite)
"""

import json
import re
import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from .models.schemas import ActionPlan, ActionStep, ActionType, GoalStep, GoalPlan
from .llm_client import LLMClient
from .system_prompt import SANDHYA_SYSTEM_PROMPT
from .utils.logger import get_logger


logger = get_logger(__name__)


# ============================================================================
# Enums & Data Classes
# ============================================================================

class AutonomousActionType(Enum):
    """Single action types for autonomous planner."""
    CLICK = "click"
    TYPE = "type"
    READ = "read"
    SCROLL = "scroll"
    WAIT = "wait"
    NAVIGATE = "navigate"
    FINISH = "finish"


@dataclass
class ActionDecision:
    """Structured decision output from autonomous planner."""
    thought: str  # Reasoning about next action
    action: str  # Action type (click, type, read, scroll, wait, navigate, finish)
    target_selector: Optional[str]  # CSS selector for the target element
    input_text: Optional[str]  # Text to type if action is "type"
    confidence: float  # 0.0-1.0 confidence in decision
    explanation: str  # Why this action is optimal
    timestamp: str = None  # ISO timestamp
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "thought": self.thought,
            "action": self.action,
            "target_selector": self.target_selector,
            "input_text": self.input_text,
            "confidence": self.confidence,
            "explanation": self.explanation,
            "timestamp": self.timestamp,
        }


class Planner:
    """Converts automation requests into structured action plans."""
    
    def __init__(self, llm_client: LLMClient):
        """
        Initialize planner.
        
        Args:
            llm_client: LLM client for generating plans
        """
        self.llm_client = llm_client
        logger.info("Planner initialized")
    
    def generate_plan(self, request: str) -> ActionPlan:
        """
        Generate action plan from user request.
        
        Args:
            request: User automation request
            
        Returns:
            ActionPlan with sequence of steps
        """
        logger.info(f"Generating plan for: {request}")
        
        system_prompt = """You are an expert at planning browser automation tasks.
Convert user requests into a JSON array of action steps.

Available actions:
- open_url: Open a URL. Requires 'value' (the URL)
- search: Search a query. Requires 'value' (search query)
- click: Click an element. Requires 'selector' (CSS selector)
- click_first_result: Click first search result. No additional parameters.
- scroll: Scroll page. Requires 'value' ('up' or 'down') and optionally 'amount' (default 3)
- extract_text: Extract text. Optionally requires 'selector' for specific element
- fill_input: Fill input field. Requires 'selector' and 'value'
- wait: Wait for duration. Requires 'duration_ms'
- navigate_back: Go back. No additional parameters.

IMPORTANT: Return ONLY valid JSON, no other text. Example:
{
  "steps": [
    {"action": "open_url", "value": "https://google.com", "description": "Open Google"},
    {"action": "search", "value": "python tutorial", "description": "Search for Python tutorials"}
  ],
  "reasoning": "Opening Google and searching for tutorials"
}"""
        
        user_prompt = f"""Plan these browser automation steps:
{request}

Return valid JSON with 'steps' array and 'reasoning' string."""
        
        try:
            response = self.llm_client.generate_response_sync(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=1024
            )
            
            # Extract JSON from response (sometimes model adds explanations)
            plan_dict = self._extract_json(response)
            
            if not plan_dict or "steps" not in plan_dict:
                logger.warning("LLM response doesn't contain valid plan, using fallback")
                return self._create_fallback_plan(request)
            
            # Convert to ActionPlan, validating each step
            steps = []
            invalid_steps = 0
            
            for step_data in plan_dict.get("steps", []):
                try:
                    action_name = step_data.get("action", "open_url")
                    
                    # Validate action against ActionType enum
                    if not self._is_valid_action(action_name):
                        logger.warning(
                            f"Invalid action '{action_name}' in plan, skipping step. "
                            f"Valid actions: {self._get_valid_actions()}"
                        )
                        invalid_steps += 1
                        continue
                    
                    action = ActionType(action_name)
                    step = ActionStep(
                        action=action,
                        value=step_data.get("value"),
                        selector=step_data.get("selector"),
                        duration_ms=step_data.get("duration_ms"),
                        description=step_data.get("description"),
                    )
                    steps.append(step)
                except (ValueError, KeyError) as e:
                    logger.warning(f"Invalid step in plan: {e}, skipping")
                    invalid_steps += 1
                    continue
            
            # Log if any steps were invalid
            if invalid_steps > 0:
                logger.debug(f"Rejected {invalid_steps} invalid steps during plan generation")
            
            plan = ActionPlan(
                steps=steps,
                reasoning=plan_dict.get("reasoning", "Generated from user request")
            )
            
            logger.info(f"Generated plan with {len(plan.steps)} steps (validated)")
            return plan
            
        except Exception as e:
            logger.error(f"Error generating plan: {e}")
            return self._create_fallback_plan(request)
    
    def _extract_json(self, text: str) -> Optional[dict]:
        """
        Extract JSON from text response.
        
        Args:
            text: Text containing JSON
            
        Returns:
            Parsed JSON dict or None
        """
        # Try to find JSON object in the text
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, text, re.DOTALL)
        
        for match in reversed(matches):  # Try from end (more likely to be valid)
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
        
        # Try parsing entire text
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None
    
    def _create_fallback_plan(self, request: str) -> ActionPlan:
        """
        Create a basic fallback plan by parsing request keywords.
        
        Args:
            request: User request
            
        Returns:
            Simple ActionPlan
        """
        logger.info("Creating fallback plan from request parsing")
        
        steps = []
        request_lower = request.lower()
        
        # Try to extract URL/search query
        url_match = re.search(r'(?:https?://|www\.)[^\s]+|\.com[^\s]*', request)
        search_match = re.search(r'(?:search|find)(?:\s+for)?\s+["\']?([^"\']+)["\']?', request)
        
        if "open" in request_lower or "go" in request_lower or url_match:
            if url_match:
                url = url_match.group(0)
                if not url.startswith("http"):
                    url = "https://" + url
                steps.append(ActionStep(
                    action=ActionType.OPEN_URL,
                    value=url,
                    description=f"Open {url}"
                ))
            else:
                steps.append(ActionStep(
                    action=ActionType.OPEN_URL,
                    value="https://www.google.com",
                    description="Open Google"
                ))
        
        if "search" in request_lower or search_match:
            query = search_match.group(1) if search_match else "result"
            steps.append(ActionStep(
                action=ActionType.SEARCH,
                value=query,
                description=f"Search for {query}"
            ))
            steps.append(ActionStep(
                action=ActionType.CLICK,
                value="click_first_result",
                description="Click first result"
            ))
        
        if "click" in request_lower or "press" in request_lower:
            steps.append(ActionStep(
                action=ActionType.CLICK,
                value="button, a",
                description="Click button or link"
            ))
        
        if "scroll" in request_lower:
            direction = "down" if "down" in request_lower else "up"
            steps.append(ActionStep(
                action=ActionType.SCROLL,
                value=direction,
                description=f"Scroll {direction}"
            ))
        
        if "extract" in request_lower or "read" in request_lower:
            steps.append(ActionStep(
                action=ActionType.EXTRACT_TEXT,
                description="Extract text from page"
            ))
        
        # If no steps were identified, default to opening Google
        if not steps:
            steps.append(ActionStep(
                action=ActionType.OPEN_URL,
                value="https://www.google.com",
                description="Open Google"
            ))
        
        return ActionPlan(
            steps=steps,
            reasoning="Fallback plan generated from keyword matching"
        )
    
    def _is_valid_action(self, action_name: str) -> bool:
        """
        Check if action name is valid against ActionType enum.
        
        Args:
            action_name: Action name to validate
            
        Returns:
            True if action is valid, False otherwise
        """
        try:
            ActionType(action_name)
            return True
        except ValueError:
            return False
    
    def _get_valid_actions(self) -> str:
        """
        Get comma-separated list of valid action names.
        
        Returns:
            String of valid action names
        """
        valid_actions = [action.value for action in ActionType]
        return ", ".join(valid_actions)


# ============================================================================
# AutonomousPlanner Class
# ============================================================================

class AutonomousPlanner:
    """
    Intelligent single-action decision planner for autonomous browsing.
    
    Takes current page state and user goal, decides the SINGLE best next action.
    Uses LLM reasoning with heuristic fallback for reliability.
    
    Attributes:
        llm_client: LLMClient instance for LLM reasoning
        max_retries: Maximum retry attempts (default 2)
        decision_timeout: Timeout for LLM response (default 8 seconds)
        temperature: LLM temperature for reasoning (default 0.2 - deterministic)
    """
    
    DECISION_TIMEOUT = 8.0  # seconds
    MAX_RETRIES = 2
    DECISION_TEMPERATURE = 0.2
    
    def __init__(self, llm_client: LLMClient):
        """
        Initialize autonomous planner.
        
        Args:
            llm_client: LLMClient instance for reasoning
        """
        self.llm_client = llm_client
        self._logger = get_logger(f"autonomous_planner.{id(self)}")
        self._logger.debug("AutonomousPlanner initialized")
    
    async def decide_next_action(
        self,
        user_goal: str,
        page_state: Dict[str, Any],
        conversation_history: List[Dict[str, str]] = None
    ) -> ActionDecision:
        """
        Decide the SINGLE best next action based on goal and page state.
        
        Uses LLM reasoning with heuristic fallback.
        
        Args:
            user_goal: Natural language goal (e.g., "Find a free Python course")
            page_state: Structured page state from PageAnalyzer
            conversation_history: Optional conversation history for context
            
        Returns:
            ActionDecision with thought, action, selector, etc.
        """
        self._logger.info(f"Deciding next action for goal: {user_goal[:60]}...")
        
        try:
            # Try LLM-based decision making
            decision = await self._decide_via_llm(
                user_goal,
                page_state,
                conversation_history or []
            )
            return decision
        
        except Exception as e:
            self._logger.warning(f"LLM decision failed: {e}, using heuristic fallback")
            # Fallback to heuristic-based decision
            decision = self._decide_via_heuristics(user_goal, page_state)
            return decision
    
    async def _decide_via_llm(
        self,
        user_goal: str,
        page_state: Dict[str, Any],
        conversation_history: List[Dict[str, str]]
    ) -> ActionDecision:
        """
        Make decision using LLM reasoning.
        
        Args:
            user_goal: User's goal
            page_state: Page state from analyzer
            conversation_history: Conversation context
            
        Returns:
            ActionDecision
        """
        self._logger.debug("Using LLM for decision making")
        
        # Build reasoning prompt
        prompt = self._build_decision_prompt(user_goal, page_state, conversation_history)
        
        try:
            # Call LLM with timeout
            response = await asyncio.wait_for(
                self._call_llm(prompt),
                timeout=self.DECISION_TIMEOUT
            )
            
            # Parse response
            decision = self._parse_llm_response(response, page_state)
            
            self._logger.debug(f"LLM decided: {decision.action}")
            return decision
        
        except asyncio.TimeoutError:
            self._logger.warning("LLM response timeout")
            raise
        except Exception as e:
            self._logger.warning(f"LLM parsing error: {e}")
            raise
    
    def _build_decision_prompt(
        self,
        user_goal: str,
        page_state: Dict[str, Any],
        conversation_history: List[Dict[str, str]]
    ) -> str:
        """
        Build structured reasoning prompt for LLM.
        
        Args:
            user_goal: User goal
            page_state: Page state dict
            conversation_history: Conversation context
            
        Returns:
            Formatted prompt string
        """
        # Format links
        links_text = ""
        for link in page_state.get("links", [])[:10]:
            links_text += f"- {link.get('text', '')} | {link.get('selector', '')}\n"
        
        # Format buttons
        buttons_text = ""
        for btn in page_state.get("buttons", [])[:8]:
            buttons_text += f"- {btn.get('text', '')} | {btn.get('selector', '')}\n"
        
        # Format inputs
        inputs_text = ""
        for inp in page_state.get("inputs", [])[:6]:
            placeholder = inp.get('placeholder', '')
            name = inp.get('name', '')
            selector = inp.get('selector', '')
            inputs_text += f"- placeholder:'{placeholder}' name:'{name}' | {selector}\n"
        
        # Format conversation history (last 5 messages)
        conv_text = ""
        for msg in conversation_history[-5:]:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:200]
            conv_text += f"{role}: {content}\n"
        
        prompt = f"""You are an autonomous browser automation decision maker.

GOAL: {user_goal}

CURRENT PAGE:
Title: {page_state.get('title', 'Unknown')}
URL: {page_state.get('url', 'Unknown')}

VISIBLE LINKS:
{links_text or "(none)"}

VISIBLE BUTTONS:
{buttons_text or "(none)"}

INPUT FIELDS:
{inputs_text or "(none)"}

TEXT CONTENT:
{page_state.get('main_text_summary', '')[:500]}

CONVERSATION:
{conv_text or "(none)"}

DECISION RULES:
1. If relevant link/button exists → "click" that element
2. If search box visible & goal needs search → "type" in search box
3. If need to read content on page → "read"
4. If goal needs scrolling to find relevant elements → "scroll"
5. If goal has been achieved → "finish"
6. ONLY use selectors that appear in page state above
7. Match goal semantically to visible elements

Decide the SINGLE best next action.

Return STRICT JSON (no other text):
{{
  "thought": "Reasoning about why this action",
  "action": "click|type|read|scroll|wait|navigate|finish",
  "target_selector": "CSS selector or null",
  "input_text": "text to type or null",
  "confidence": 0.0-1.0,
  "explanation": "Why this action is optimal"
}}"""
        
        return prompt
    
    async def _call_llm(self, prompt: str) -> str:
        """
        Call LLM with retry logic.
        
        Args:
            prompt: Prompt to send
            
        Returns:
            LLM response string
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.llm_client.generate_response_sync(
                    prompt=prompt,
                    temperature=self.DECISION_TEMPERATURE,
                    max_tokens=512
                )
                return response
            except Exception as e:
                self._logger.debug(f"LLM attempt {attempt + 1} failed: {e}")
                if attempt == self.MAX_RETRIES - 1:
                    raise
                await asyncio.sleep(0.5)  # Brief wait before retry
    
    def _parse_llm_response(
        self,
        response: str,
        page_state: Dict[str, Any]
    ) -> ActionDecision:
        """
        Parse LLM response into ActionDecision.
        
        Validates against page state and applies safety rules.
        
        Args:
            response: LLM response string
            page_state: Page state for validation
            
        Returns:
            ActionDecision
        """
        try:
            # Extract JSON from response
            decision_dict = self._extract_json_from_response(response)
            
            if not decision_dict:
                self._logger.warning("Could not extract JSON from LLM response")
                raise ValueError("Invalid JSON in response")
            
            # Validate action
            action = decision_dict.get("action", "read").lower()
            valid_actions = {
                "click", "type", "read", "scroll", "wait", "navigate", "finish"
            }
            if action not in valid_actions:
                self._logger.warning(f"Invalid action: {action}, defaulting to read")
                action = "read"
            
            # Validate and clean selector
            target_selector = decision_dict.get("target_selector")
            if target_selector and action == "click":
                # Verify selector exists in page state
                if not self._selector_in_page_state(target_selector, page_state):
                    self._logger.warning(f"Selector not in page state: {target_selector}")
                    target_selector = None
            
            # Build decision
            decision = ActionDecision(
                thought=decision_dict.get("thought", ""),
                action=action,
                target_selector=target_selector,
                input_text=decision_dict.get("input_text"),
                confidence=min(1.0, max(0.0, float(decision_dict.get("confidence", 0.5)))),
                explanation=decision_dict.get("explanation", "")
            )
            
            return decision
        
        except Exception as e:
            self._logger.error(f"Error parsing LLM response: {e}")
            raise
    
    def _decide_via_heuristics(
        self,
        user_goal: str,
        page_state: Dict[str, Any]
    ) -> ActionDecision:
        """
        Make decision using rule-based heuristics (fallback).
        
        Args:
            user_goal: User goal
            page_state: Page state
            
        Returns:
            ActionDecision
        """
        self._logger.info("Making decision via heuristics")
        
        goal_lower = user_goal.lower()
        
        # Rule 1: Match keywords to clickable elements
        search_keywords = {"search", "find", "look", "query", "check", "discover"}
        if any(kw in goal_lower for kw in search_keywords):
            # Find search input
            for inp in page_state.get("inputs", []):
                if "search" in (inp.get("placeholder", "") + inp.get("name", "")).lower():
                    return ActionDecision(
                        thought="Goal requires search, found search input",
                        action="type",
                        target_selector=inp.get("selector"),
                        input_text=self._extract_search_term(user_goal),
                        confidence=0.8,
                        explanation="Using search box to find information"
                    )
        
        # Rule 2: Look for "free" or "course" in links for course-related goals
        if "course" in goal_lower or "learn" in goal_lower:
            for link in page_state.get("links", []):
                link_text = link.get("text", "").lower()
                if any(kw in link_text for kw in {"free", "tutorial", "course", "learn"}):
                    return ActionDecision(
                        thought="Found relevant course link matching goal",
                        action="click",
                        target_selector=link.get("selector"),
                        input_text=None,
                        confidence=0.9,
                        explanation=f"Clicking on {link.get('text', 'link')} that matches goal"
                    )
        
        # Rule 3: Match button text to goal
        action_keywords = {
            "view": "click",
            "read": "read",
            "enroll": "click",
            "register": "click",
            "download": "click",
            "submit": "click",
            "next": "click",
        }
        
        for btn in page_state.get("buttons", []):
            btn_text = btn.get("text", "").lower()
            for keyword, action in action_keywords.items():
                if keyword in btn_text:
                    return ActionDecision(
                        thought=f"Found button matching goal keyword: {keyword}",
                        action=action,
                        target_selector=btn.get("selector"),
                        input_text=None,
                        confidence=0.8,
                        explanation=f"Clicking button: {btn.get('text')}"
                    )
        
        # Rule 4: Check if goal appears to be completed
        page_text = (page_state.get("main_text_summary", "") + " " +
                     " ".join([h for h in page_state.get("headings", [])])).lower()
        
        if any(kw in page_text for kw in ["success", "complete", "accomplished", "done"]):
            if any(pattern in goal_lower for pattern in ["find", "search", "get"]):
                return ActionDecision(
                    thought="Goal appears to be satisfied based on page content",
                    action="finish",
                    target_selector=None,
                    input_text=None,
                    confidence=0.7,
                    explanation="Page appears to contain what was requested"
                )
        
        # Rule 5: Default to scrolling to find more content
        return ActionDecision(
            thought="No obvious next action, scroll to explore more content",
            action="scroll",
            target_selector=None,
            input_text=None,
            confidence=0.5,
            explanation="Scrolling page to find relevant content"
        )
    
    def _extract_json_from_response(self, response: str) -> Optional[Dict]:
        """
        Extract JSON from LLM response.
        
        Args:
            response: Response string potentially containing JSON
            
        Returns:
            Parsed dict or None
        """
        # Try to find JSON object
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, response, re.DOTALL)
        
        for match in reversed(matches):  # Try from end
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
        
        # Try entire response
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return None
    
    def _selector_in_page_state(self, selector: str, page_state: Dict[str, Any]) -> bool:
        """
        Check if selector exists in page state.
        
        Args:
            selector: CSS selector to check
            page_state: Page state dict
            
        Returns:
            True if selector is in page state
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
    
    @staticmethod
    def _extract_search_term(goal: str) -> str:
        """
        Extract search term from goal.
        
        Args:
            goal: Goal string
            
        Returns:
            Extracted search term or empty string
        """
        # Look for patterns like "search for X", "find X", etc.
        patterns = [
            r"(?:search|find|look for)\s+(?:for\s+)?['\"]?([^'\"]+)['\"]?",
            r"['\"]([^'\"]+)['\"]",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, goal, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Fallback: return last few words
        words = goal.split()
        return " ".join(words[-3:]) if len(words) > 0 else ""


# ============================================================================
# HybridPlanner Class - True Autonomous Re-Planning with Deterministic Rules
# ============================================================================

class HybridPlanner:
    """
    Hybrid planner for true autonomous re-planning using deterministic rules + LLM.
    
    Decides ONLY the next best action (not a full multi-step plan).
    
    Strategy:
    1. Primary: Deterministic rule-based decision (no LLM calls)
    2. Fallback: LLM reasoning (only if rules don't apply)
    
    Rules (in priority order):
    1. If goal already satisfied → finish
    2. If same selector failed repeatedly → scroll (avoid loop)
    3. If link/button text matches goal → click best match
    4. If search input exists and goal is a query → type into search
    5. If page is long and goal not satisfied → scroll
    6. Otherwise → LLM decision
    
    Always validates action before returning to ensure:
    - Action is in allowed list
    - Selectors exist in page_state
    - Confidence is between 0-1
    - Falls back to safe action (scroll) if validation fails
    
    Attributes:
        llm_client: LLMClient for fallback LLM reasoning
        _logger: Configured logger instance
        _llm_timeout: Timeout for LLM calls (seconds)
        _llm_temperature: Temperature for deterministic LLM responses
    """
    
    # Supported actions
    ALLOWED_ACTIONS = {"click", "type", "read", "scroll", "wait", "navigate", "finish"}
    
    # LLM configuration
    LLM_TIMEOUT = 8.0  # seconds
    LLM_TEMPERATURE = 0.2  # Deterministic
    LLM_MAX_TOKENS = 512
    
    # Goal satisfaction keywords
    SATISFACTION_KEYWORDS = {
        "success", "complete", "done", "accomplished",
        "result found", "results found", "product page",
        "confirmed", "verified", "logged in"
    }
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Initialize hybrid planner.
        
        Args:
            llm_client: Optional LLMClient for fallback reasoning
        """
        self.llm_client = llm_client
        self._logger = get_logger(f"hybrid_planner.{id(self)}")
        self._logger.debug("HybridPlanner initialized")
    
    async def replan_next_action(
        self,
        goal: str,
        page_state: Dict[str, Any],
        history: List[Dict[str, Any]],
        failures: List[Dict[str, Any]],
        strategic_state: Optional[Dict[str, Any]] = None
    ) -> ActionDecision:
        """
        Decide the next best action using hybrid strategy with strategic awareness.
        
        Process:
        1. Analyze strategic state for patterns (repeated failures, stuck conditions)
        2. Try deterministic rules (fast, reliable)
        3. Fall back to LLM only if rules don't apply
        4. Validate result before returning
        
        Strategic Behaviors:
        - If is_stuck == True: Strongly prefer exploration (scroll, navigate, different elements)
        - If failure_rate > 0.5: Lower confidence, bias toward exploration, avoid finish
        - If same action repeated 3 times: Force different action category
        - If repeated_selector: Avoid that selector, try alternatives
        
        Args:
            goal: User goal description
            page_state: Current page state from PageAnalyzer
            history: Recent action history
            failures: Recent failures
            strategic_state: Optional strategic analysis (failure patterns, stuck state)
            
        Returns:
            ActionDecision with next action to take
        """
        self._logger.info(f"Replanning next action for goal: {goal[:50]}...")
        
        # Parse strategic state (if provided)
        is_stuck = False
        failure_rate = 0.0
        repeated_selector = None
        repeated_action = None
        last_3_actions = []
        
        if strategic_state:
            is_stuck = strategic_state.get("is_stuck", False)
            failure_rate = strategic_state.get("failure_rate", 0.0)
            repeated_selector = strategic_state.get("repeated_selector")
            repeated_action = strategic_state.get("repeated_action")
            last_3_actions = strategic_state.get("last_3_actions", [])
            
            self._logger.debug(
                f"Strategic state: stuck={is_stuck}, failure_rate={failure_rate:.2f}, "
                f"repeated_selector={repeated_selector}, repeated_action={repeated_action}"
            )
        
        try:
            # ================================================================
            # STRATEGIC OVERRIDE: If stuck, force exploration immediately
            # ================================================================
            if is_stuck:
                self._logger.warning("Agent is stuck - forcing exploratory action")
                
                # Prefer scroll or navigation over clicking same things
                # Check if scroll was recent
                recent_scrolls = [a for a in last_3_actions if a == "scroll"]
                
                if len(recent_scrolls) >= 2:
                    # Too many scrolls, try going back or searching
                    self._logger.debug("Too many recent scrolls, suggesting navigation back")
                    return ActionDecision(
                        thought="Agent stuck after multiple scrolls, going back to try different path",
                        action="navigate",
                        target_selector=None,
                        input_text="back",
                        confidence=0.6,
                        explanation="Strategic: Stuck condition - navigating back to explore alternatives"
                    )
                else:
                    # Default stuck recovery: scroll to find new elements
                    return ActionDecision(
                        thought="Agent stuck, scrolling to discover new elements",
                        action="scroll",
                        target_selector=None,
                        input_text="down",
                        confidence=0.7,
                        explanation="Strategic: Stuck condition - exploring page for alternative elements"
                    )
            
            # ================================================================
            # RULE 1: Check if goal is already satisfied
            # ================================================================
            # STRATEGIC: Don't finish if failure rate is high (not confident in state)
            if self._goal_satisfied(goal, page_state):
                if failure_rate > 0.5:
                    self._logger.warning(
                        f"Goal appears satisfied but failure rate is high ({failure_rate:.2f}) - continuing exploration"
                    )
                    # Don't finish, continue exploring
                else:
                    self._logger.debug("Rule 1: Goal satisfied → finish")
                    return ActionDecision(
                        thought="Goal appears to be satisfied on current page",
                        action="finish",
                        target_selector=None,
                        input_text=None,
                        confidence=0.9,
                        explanation="Goal content found on page"
                    )
            
            # ================================================================
            # RULE 2: Check if same selector failed repeatedly
            # ================================================================
            stuck_selector = repeated_selector or self._recent_failures_on_same_selector(failures)
            if stuck_selector:
                self._logger.debug(f"Rule 2: Stuck on selector {stuck_selector} → scroll to find alternatives")
                return ActionDecision(
                    thought=f"Selector {stuck_selector} failed multiple times, scrolling to find alternative",
                    action="scroll",
                    target_selector=None,
                    input_text="down",
                    confidence=0.8,
                    explanation="Strategic: Avoiding repeated selector failure, exploring page"
                )
            
            # ================================================================
            # STRATEGIC: Check if same action repeated 3 times - force different category
            # ================================================================
            if last_3_actions and len(last_3_actions) >= 3:
                if last_3_actions[-1] == last_3_actions[-2] == last_3_actions[-3]:
                    repeated = last_3_actions[-1]
                    self._logger.warning(f"Same action repeated 3 times: {repeated} - forcing alternative")
                    
                    # Choose different action category
                    if repeated == "click":
                        return ActionDecision(
                            thought="Click repeated 3 times, trying scroll instead",
                            action="scroll",
                            target_selector=None,
                            input_text="down",
                            confidence=0.6,
                            explanation="Strategic: Breaking repetition pattern by scrolling"
                        )
                    elif repeated == "scroll":
                        # Find any clickable element
                        best_match = self._find_best_matching_link(goal, page_state)
                        if best_match:
                            return ActionDecision(
                                thought="Scroll repeated 3 times, trying click instead",
                                action="click",
                                target_selector=best_match["selector"],
                                input_text=None,
                                confidence=0.6,
                                explanation="Strategic: Breaking scroll loop by clicking element"
                            )
                    elif repeated == "type":
                        return ActionDecision(
                            thought="Type repeated 3 times, trying scroll",
                            action="scroll",
                            target_selector=None,
                            input_text="down",
                            confidence=0.6,
                            explanation="Strategic: Breaking type repetition by exploring"
                        )
            
            # ================================================================
            # RULE 3: Find best matching link or button
            # ================================================================
            best_match = self._find_best_matching_link(goal, page_state)
            
            # STRATEGIC: Filter out repeated_selector if provided
            if best_match and repeated_selector and best_match["selector"] == repeated_selector:
                self._logger.debug(f"Best match is repeated selector {repeated_selector}, skipping")
                best_match = None  # Force alternative
            
            if best_match:
                self._logger.debug(f"Rule 3: Found matching link/button: {best_match['text']}")
                
                # STRATEGIC: Lower confidence if high failure rate
                confidence = 0.85
                if failure_rate > 0.5:
                    confidence = 0.65
                    self._logger.debug(f"Lowering confidence due to high failure rate ({failure_rate:.2f})")
                
                return ActionDecision(
                    thought=f"Found element that matches goal: '{best_match['text']}'",
                    action="click",
                    target_selector=best_match["selector"],
                    input_text=None,
                    confidence=confidence,
                    explanation=f"Clicking on '{best_match['text']}' which matches the goal"
                )
            
            # ================================================================
            # RULE 4: If goal looks like a search query and search input exists
            # ================================================================
            # STRATEGIC: Avoid if 'type' action repeated multiple times
            if repeated_action != "type":  # Only if type not failing repeatedly
                search_input = self._find_search_input(page_state.get("inputs", []))
                if search_input and self._is_search_goal(goal):
                    search_term = self._extract_search_keywords(goal)
                    if search_term:
                        self._logger.debug(f"Rule 4: Searching for '{search_term}' via search input")
                        
                        # STRATEGIC: Lower confidence if high failure rate
                        confidence = 0.8
                        if failure_rate > 0.5:
                            confidence = 0.6
                        
                        return ActionDecision(
                            thought=f"Goal is a search query, found search input",
                            action="type",
                            target_selector=search_input["selector"],
                            input_text=search_term,
                            confidence=confidence,
                            explanation=f"Typing search query into search box: '{search_term}'"
                        )
            
            # ================================================================
            # RULE 5: If page is long and goal not satisfied, scroll
            # ================================================================
            # STRATEGIC: Only if not scrolling repeatedly
            if repeated_action != "scroll":  # Avoid if scroll is failing
                if self._page_is_long(page_state):
                    # Check if we haven't scrolled recently
                    recent_scrolls = [h for h in history[-5:] if h.get("decision", {}).get("action") == "scroll"]
                    if len(recent_scrolls) < 2:  # Only if few scrolls in history
                        self._logger.debug("Rule 5: Page is long and goal unsatisfied → scroll")
                        
                        # STRATEGIC: Lower confidence if high failure rate
                        confidence = 0.7
                        if failure_rate > 0.5:
                            confidence = 0.5
                        
                        return ActionDecision(
                            thought="Page is long and goal not satisfied yet, scrolling to explore",
                            action="scroll",
                            target_selector=None,
                            input_text="down",
                            confidence=confidence,
                            explanation="Scrolling down to find relevant content"
                        )
            
            # ================================================================
            # FALLBACK: Use LLM for complex decision
            # ================================================================
            self._logger.debug("No deterministic rule applied → using LLM fallback")
            decision = await self._llm_decision(goal, page_state, history, failures)
            
            # STRATEGIC: Adjust LLM decision confidence based on failure rate
            if failure_rate > 0.5:
                original_confidence = decision.confidence
                decision.confidence = min(original_confidence * 0.8, 0.7)  # Cap at 0.7
                self._logger.debug(
                    f"Adjusted LLM confidence due to high failure rate: "
                    f"{original_confidence:.2f} → {decision.confidence:.2f}"
                )
            
            # Validate before returning
            decision = self._validate_and_correct_decision(decision, page_state)
            
            self._logger.info(f"LLM decision: {decision.action} (confidence: {decision.confidence:.2f})")
            return decision
        
        except Exception as e:
            self._logger.error(f"Error in replan_next_action: {e}")
            # Safe fallback: scroll
            return ActionDecision(
                thought="Error during planning, using safe fallback",
                action="scroll",
                target_selector=None,
                input_text="down",
                confidence=0.3,
                explanation="Error occurred, scrolling to explore page safely"
            )
    
    # ========================================================================
    # Deterministic Rule Helpers
    # ========================================================================
    
    def _goal_satisfied(self, goal: str, page_state: Dict[str, Any]) -> bool:
        """
        Check if goal is already satisfied on current page.
        
        PRODUCTION FIX: Enhanced heuristics with semantic signals:
        - Goal keywords appear in page text
        - Page title/headings contain satisfaction keywords
        - Content density suggests informational completeness
        - URL patterns suggest goal-relevant page
        
        Args:
            goal: User goal
            page_state: Current page state
            
        Returns:
            True if goal appears satisfied
        """
        goal_lower = goal.lower()
        text_lower = page_state.get("main_text_summary", "").lower()
        title_lower = page_state.get("title", "").lower()
        headings_lower = " ".join(page_state.get("headings", [])).lower()
        url_lower = page_state.get("url", "").lower()
        
        # PRODUCTION FIX: Check URL patterns for goal-relevant pages
        url_indicators = {
            "course": ["course", "learn", "tutorial", "class", "training"],
            "product": ["product", "item", "details", "shop"],
            "article": ["article", "post", "blog", "news"],
            "result": ["search", "results", "query"],
        }
        
        goal_type = None
        for gtype, patterns in url_indicators.items():
            if any(p in goal_lower for p in patterns):
                goal_type = gtype
                break
        
        # If URL matches goal type, stronger signal
        url_match = False
        if goal_type:
            url_match = any(p in url_lower for p in url_indicators[goal_type])
        
        # Check satisfaction keywords
        text_combined = f"{text_lower} {title_lower} {headings_lower}"
        
        satisfaction_found = False
        for keyword in self.SATISFACTION_KEYWORDS:
            if keyword in text_combined:
                self._logger.debug(f"Satisfaction keyword found: {keyword}")
                satisfaction_found = True
                break
        
        # PRODUCTION FIX: Check if goal keywords appear with sufficient density
        goal_keywords = self._extract_keywords(goal)
        matches = sum(1 for kw in goal_keywords if kw in text_lower)
        keyword_density = matches / len(goal_keywords) if goal_keywords else 0
        
        # PRODUCTION FIX: Content density check (prevents premature finish on sparse pages)
        text_length = len(page_state.get("main_text_summary", ""))
        has_substantial_content = text_length > 400  # At least 400 chars
        
        # Require ALL conditions for confident satisfaction:
        # 1. High keyword density (80%+ of goal words present)
        # 2. Substantial content (not a loading/error page)
        # 3. EITHER satisfaction keywords OR URL match
        if keyword_density >= 0.8 and has_substantial_content:
            if satisfaction_found or url_match:
                self._logger.info(
                    f"Goal likely satisfied: keyword_density={keyword_density:.2f}, "
                    f"content_length={text_length}, url_match={url_match}"
                )
                return True
        
        # PRODUCTION FIX: Secondary check - if keyword density is very high (90%+) alone
        if keyword_density >= 0.9 and text_length > 600:
            self._logger.info(f"Goal likely satisfied: high keyword density ({keyword_density:.2f})")
            return True
        
        self._logger.debug(
            f"Goal not satisfied: keyword_density={keyword_density:.2f}, "
            f"content_length={text_length}, satisfaction_found={satisfaction_found}"
        )
        return False
    
    def _find_best_matching_link(self, goal: str, page_state: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """
        Find best matching link/button for goal.
        
        Uses semantic similarity between goal and element text.
        
        Args:
            goal: User goal
            page_state: Current page state
            
        Returns:
            Best matching link/button dict or None
        """
        goal_keywords = self._extract_keywords(goal)
        best_match = None
        best_score = 0
        
        # Check links
        for link in page_state.get("links", []):
            text = link.get("text", "").lower()
            score = self._calculate_match_score(text, goal_keywords)
            
            if score > best_score:
                best_score = score
                best_match = link
        
        # Check buttons (may have higher priority)
        for button in page_state.get("buttons", []):
            text = button.get("text", "").lower()
            score = self._calculate_match_score(text, goal_keywords)
            
            # Buttons get slight boost
            score *= 1.1
            
            if score > best_score:
                best_score = score
                best_match = button
        
        # Only return if score is significant (>0.5)
        if best_score > 0.5:
            self._logger.debug(f"Found matching element: '{best_match['text']}' (score: {best_score:.2f})")
            return best_match
        
        return None
    
    def _find_search_input(self, inputs: List[Dict[str, Any]]) -> Optional[Dict[str, str]]:
        """
        Find search input field if exists.
        
        Looks for inputs with:
        - type="search"
        - placeholder containing "search"
        - name containing "search" or "q"
        
        Args:
            inputs: List of input fields from page_state
            
        Returns:
            Search input dict or None
        """
        for inp in inputs:
            input_type = inp.get("type", "").lower()
            placeholder = inp.get("placeholder", "").lower()
            name = inp.get("name", "").lower()
            
            # Type is explicitly search
            if input_type == "search":
                self._logger.debug(f"Found search input (type=search)")
                return inp
            
            # Placeholder suggests search
            if "search" in placeholder or "query" in placeholder:
                self._logger.debug(f"Found search input (placeholder)")
                return inp
            
            # Name suggests search
            if "search" in name or name == "q" or "query" in name:
                self._logger.debug(f"Found search input (name)")
                return inp
        
        return None
    
    def _recent_failures_on_same_selector(self, failures: List[Dict[str, Any]]) -> Optional[str]:
        """
        Check if same selector failed multiple times recently (action stuck).
        
        Args:
            failures: Recent failures list
            
        Returns:
            Selector that failed repeatedly, or None
        """
        if not failures or len(failures) < 2:
            return None
        
        # Get last 5 failures
        recent = failures[-5:]
        selectors = [f.get("selector") for f in recent if f.get("selector")]
        
        if not selectors:
            return None
        
        # Count occurrences
        from collections import Counter
        selector_counts = Counter(selectors)
        
        # If any selector appears 2+ times, we're stuck
        for selector, count in selector_counts.most_common():
            if count >= 2:
                self._logger.debug(f"Selector {selector} failed {count} times, likely stuck")
                return selector
        
        return None
    
    def _page_is_long(self, page_state: Dict[str, Any]) -> bool:
        """
        Heuristic to determine if page is long (worth scrolling through).
        
        Indicators:
        - Text summary > 800 chars
        - Many links/buttons
        
        Args:
            page_state: Current page state
            
        Returns:
            True if page likely has more content to scroll
        """
        text_length = len(page_state.get("main_text_summary", ""))
        link_count = len(page_state.get("links", []))
        button_count = len(page_state.get("buttons", []))
        
        return text_length > 800 or (link_count + button_count) > 5
    
    def _is_search_goal(self, goal: str) -> bool:
        """
        Heuristic to determine if goal is a search/query.
        
        Args:
            goal: User goal
            
        Returns:
            True if goal looks like a search query
        """
        search_keywords = {"search", "find", "look", "query", "research", "what", "how", "where"}
        goal_lower = goal.lower()
        
        return any(kw in goal_lower for kw in search_keywords)
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract meaningful keywords from text.
        
        Removes common stopwords, splits by whitespace.
        
        Args:
            text: Text to extract keywords from
            
        Returns:
            List of keywords
        """
        stopwords = {
            "the", "a", "an", "and", "or", "but", "is", "are", "was", "were",
            "i", "you", "he", "she", "it", "we", "they", "that", "this",
            "to", "for", "in", "on", "at", "by", "from", "with", "as"
        }
        
        words = text.lower().split()
        keywords = [
            w.strip('.,!?;:') for w in words
            if len(w) > 2 and w.lower() not in stopwords
        ]
        
        return keywords[:5]  # Limit to first 5 keywords
    
    def _extract_search_keywords(self, goal: str) -> str:
        """
        Extract search query from goal.
        
        Handles patterns like "search for X", "find X", etc.
        
        Args:
            goal: User goal
            
        Returns:
            Search query string
        """
        patterns = [
            r"(?:search|find|look for)\s+(?:for\s+)?['\"]?([^'\"]+)['\"]?",
            r"['\"]([^'\"]+)['\"]",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, goal, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Fallback: return all non-stopword keywords
        keywords = self._extract_keywords(goal)
        return " ".join(keywords) if keywords else goal
    
    def _calculate_match_score(self, text: str, keywords: List[str]) -> float:
        """
        Calculate semantic match score between text and keywords.
        
        Simple heuristic: count keyword matches / total keywords.
        
        Args:
            text: Text to match against
            keywords: List of keywords
            
        Returns:
            Match score 0.0-1.0
        """
        if not keywords:
            return 0.0
        
        matches = sum(1 for kw in keywords if kw in text)
        return matches / len(keywords)
    
    # ========================================================================
    # LLM Fallback
    # ========================================================================
    
    async def _llm_decision(
        self,
        goal: str,
        page_state: Dict[str, Any],
        history: List[Dict[str, Any]],
        failures: List[Dict[str, Any]]
    ) -> ActionDecision:
        """
        Use LLM to decide next action (fallback from rules).
        
        Only called if deterministic rules don't apply.
        
        Args:
            goal: User goal
            page_state: Current page state
            history: Recent action history
            failures: Recent failures
            
        Returns:
            ActionDecision from LLM reasoning
        """
        self._logger.debug("Calling LLM for action decision")
        
        if not self.llm_client:
            self._logger.warning("No LLM client available, returning safe fallback")
            return ActionDecision(
                thought="No LLM available for reasoning",
                action="scroll",
                target_selector=None,
                input_text="down",
                confidence=0.4,
                explanation="Using fallback scroll action"
            )
        
        try:
            # Build LLM prompt
            prompt = self._build_llm_prompt(goal, page_state, history, failures)
            
            self._logger.debug(f"LLM prompt length: {len(prompt)} chars")
            
            # Call LLM with timeout
            response = await asyncio.wait_for(
                self._call_llm(prompt),
                timeout=self.LLM_TIMEOUT
            )
            
            # Parse response to ActionDecision
            decision_dict = self._extract_json_from_response(response)
            
            if decision_dict:
                decision = ActionDecision(
                    thought=decision_dict.get("thought", "LLM decision"),
                    action=decision_dict.get("action", "scroll").lower(),
                    target_selector=decision_dict.get("target_selector"),
                    input_text=decision_dict.get("input_text"),
                    confidence=float(decision_dict.get("confidence", 0.5)),
                    explanation=decision_dict.get("explanation", "")
                )
                
                self._logger.debug(f"LLM decision parsed: {decision.action}")
                return decision
            else:
                self._logger.warning("Failed to parse LLM response as JSON")
                return self._safe_fallback_decision()
        
        except asyncio.TimeoutError:
            self._logger.warning("LLM call timed out")
            return self._safe_fallback_decision()
        
        except Exception as e:
            self._logger.error(f"Error in LLM decision: {e}")
            return self._safe_fallback_decision()
    
    def _build_llm_prompt(
        self,
        goal: str,
        page_state: Dict[str, Any],
        history: List[Dict[str, Any]],
        failures: List[Dict[str, Any]]
    ) -> str:
        """
        Build LLM prompt for action decision.
        
        Includes: goal, page context, recent history, failures.
        
        Args:
            goal: User goal
            page_state: Current page state
            history: Recent action history
            failures: Recent failures
            
        Returns:
            LLM prompt string
        """
        # Summarize page elements
        links_summary = "\n".join(
            [f"  - {link['text'][:40]} ({link['selector']})"
             for link in page_state.get("links", [])[:5]]
        ) or "  (none)"
        
        buttons_summary = "\n".join(
            [f"  - {btn['text'][:40]} ({btn['selector']})"
             for btn in page_state.get("buttons", [])[:5]]
        ) or "  (none)"
        
        inputs_summary = "\n".join(
            [f"  - {inp.get('name', 'unknown')[:20]} (type: {inp.get('type', 'text')})"
             for inp in page_state.get("inputs", [])[:3]]
        ) or "  (none)"
        
        # Recent history
        recent_actions = "\n".join(
            [f"  - {h.get('action', 'unknown')}: {h.get('description', '')[:40]}"
             for h in history[-3:]]
        ) or "  (none)"
        
        # Recent failures
        recent_failures = "\n".join(
            [f"  - Selector: {f.get('selector', 'unknown')}: {f.get('error', '')[:40]}"
             for f in failures[-2:]]
        ) or "  (none)"
        
        prompt = f"""You are an autonomous browser automation agent. Decide the NEXT BEST action.

USER GOAL: {goal}

CURRENT PAGE:
- URL: {page_state.get('url', 'unknown')}
- Title: {page_state.get('title', 'unknown')}
- Summary: {page_state.get('main_text_summary', '')[:200]}

AVAILABLE LINKS:
{links_summary}

AVAILABLE BUTTONS:
{buttons_summary}

AVAILABLE INPUTS:
{inputs_summary}

RECENT ACTIONS:
{recent_actions}

RECENT FAILURES:
{recent_failures}

ALLOWED ACTIONS: click, type, read, scroll, wait, navigate, finish

Return ONLY valid JSON with this exact structure:
{{
  "thought": "Your reasoning (1 sentence)",
  "action": "click|type|read|scroll|wait|navigate|finish",
  "target_selector": "CSS selector or null",
  "input_text": "Text to type or null",
  "confidence": 0.0-1.0,
  "explanation": "Why this action (1 sentence)"
}}

Remember:
- ONLY use selectors that appear above
- Prefer click/read over scroll
- Use finish only when goal is achieved
- Be concise and deterministic"""
        
        return prompt
    
    async def _call_llm(self, prompt: str) -> str:
        """
        Call LLM with prompt (async wrapper).
        
        Args:
            prompt: LLM prompt
            
        Returns:
            LLM response string
        """
        # Run LLM call in thread pool (blocking operation)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.llm_client.generate_response_sync(
                prompt=prompt,
                temperature=self.LLM_TEMPERATURE,
                max_tokens=self.LLM_MAX_TOKENS
            )
        )
        return response
    
    def _extract_json_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from LLM response.
        
        Args:
            response: LLM response string
            
        Returns:
            Parsed dict or None
        """
        try:
            # Try to find JSON object in text
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            matches = re.findall(json_pattern, response, re.DOTALL)
            
            for match in reversed(matches):  # Try from end
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue
            
            # Try entire response
            return json.loads(response)
        
        except Exception as e:
            self._logger.warning(f"Error extracting JSON: {e}")
            return None
    
    # ========================================================================
    # Validation & Correction
    # ========================================================================
    
    def _validate_and_correct_decision(
        self,
        decision: ActionDecision,
        page_state: Dict[str, Any]
    ) -> ActionDecision:
        """
        Validate decision and correct if invalid.
        
        Checks:
        1. Action is in allowed list
        2. Selector exists in page_state (for click/type)
        3. Confidence is 0-1
        
        Falls back to scroll if invalid.
        
        Args:
            decision: ActionDecision to validate
            page_state: Current page state
            
        Returns:
            Validated ActionDecision
        """
        # Validate action
        if decision.action not in self.ALLOWED_ACTIONS:
            self._logger.warning(f"Invalid action '{decision.action}', correcting to scroll")
            return self._safe_fallback_decision()
        
        # Validate selector for click/type
        if decision.action in ["click", "type"]:
            if decision.target_selector:
                # Check if selector exists
                selector_exists = self._selector_exists(decision.target_selector, page_state)
                if not selector_exists:
                    self._logger.warning(
                        f"Selector '{decision.target_selector}' not found in page, "
                        "correcting to scroll"
                    )
                    return self._safe_fallback_decision()
        
        # Validate confidence
        decision.confidence = max(0.0, min(1.0, decision.confidence))
        
        return decision
    
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
    
    def _safe_fallback_decision(self) -> ActionDecision:
        """
        Return safe fallback decision (scroll).
        
        Used when decision validation fails or errors occur.
        
        Returns:
            Safe ActionDecision
        """
        return ActionDecision(
            thought="Fallback due to validation failure",
            action="scroll",
            target_selector=None,
            input_text="down",
            confidence=0.3,
            explanation="Using safe scroll fallback"
        )


# ============================================================================
# GoalPlanner — SANDHYA.AI master planner
# ============================================================================

class GoalPlanner:
    """
    Converts high-level user goals into structured GoalPlan objects.

    Uses SANDHYA_SYSTEM_PROMPT to instruct the LLM to return a JSON plan
    covering all tool categories (browser, filesystem, code, web research).

    Supports:
      - async generate(goal, history=[])   — primary interface
      - re-planning given previous results — for autonomous loop
    """

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
        logger.info("[GoalPlanner] Initialized")

    async def generate(
        self,
        goal: str,
        history: Optional[List[Dict[str, str]]] = None,
        context: Optional[str] = None,
    ) -> GoalPlan:
        """
        Generate a GoalPlan for the given user goal.

        Args:
            goal:    User's natural-language goal.
            history: Optional prior conversation turns [{"role":"user","content":"..."}].
            context: Optional previous execution context / results for re-planning.

        Returns:
            GoalPlan with mode, goal, plan steps, and message.
        """
        logger.info(f"[GoalPlanner] Generating plan for: {goal[:80]!r}")

        user_content = goal
        if context:
            user_content = (
                f"{goal}\n\n"
                f"[Previous execution context — use to continue or correct the plan]\n"
                f"{context}"
            )

        try:
            raw = await self.llm.generate_response(
                prompt=user_content,
                system_prompt=SANDHYA_SYSTEM_PROMPT,
                temperature=0.2,
                max_tokens=600,
            )

            logger.debug(f"[GoalPlanner] Raw response: {raw[:400]!r}")

            if raw.startswith("LLM_ERROR"):
                logger.warning(f"[GoalPlanner] LLM error: {raw}")
                return self._chat_fallback(goal, raw)

            plan = self._parse_plan(raw, goal)
            logger.info(
                f"[GoalPlanner] mode={plan.mode} | steps={len(plan.plan)} | "
                f"goal={plan.goal[:60]!r}"
            )
            return plan

        except Exception as e:
            logger.error(f"[GoalPlanner] Exception: {e}", exc_info=True)
            return self._chat_fallback(goal, str(e))

    def _parse_plan(self, raw: str, original_goal: str) -> GoalPlan:
        """Parse LLM JSON response into a GoalPlan.

        Supports two output shapes:
          NEW: {mode, goal, message, deliberation:{planner_plan,critic_feedback,refined_plan}, final_plan:{goal,steps:[...]}}
          LEGACY: {mode, goal, message, plan:[...]}
        """
        data = self._extract_json(raw)

        if data is None:
            logger.warning("[GoalPlanner] Could not parse JSON plan")
            return GoalPlan(
                mode="chat",
                goal=original_goal,
                plan=[],
                message=raw.strip()[:500] if raw.strip() else "I'm ready to help.",
            )

        mode = str(data.get("mode", "chat")).lower()
        goal = str(data.get("goal", original_goal))
        message = str(data.get("message", ""))

        # ── NEW format: final_plan.steps takes priority ──────────────────────
        raw_steps: list = []
        deliberation: Optional[dict] = None

        final_plan = data.get("final_plan")
        if isinstance(final_plan, dict):
            raw_steps = final_plan.get("steps", []) or []
            if not isinstance(raw_steps, list):
                raw_steps = []
            # override goal from final_plan if more specific
            if final_plan.get("goal"):
                goal = str(final_plan["goal"])

        # ── LEGACY format fallback ────────────────────────────────────────────
        if not raw_steps:
            raw_steps = data.get("plan", []) or []
            if not isinstance(raw_steps, list):
                raw_steps = []

        # ── Extract deliberation payload ──────────────────────────────────────
        delib = data.get("deliberation")
        if isinstance(delib, dict):
            deliberation = {
                "planner_plan": delib.get("planner_plan", []),
                "critic_feedback": delib.get("critic_feedback", ""),
                "refined_plan": delib.get("refined_plan", []),
            }
            logger.debug(
                f"[GoalPlanner] deliberation captured | "
                f"planner_steps={len(deliberation['planner_plan'])} | "
                f"critic={str(deliberation['critic_feedback'])[:80]!r}"
            )

        steps = []
        for item in raw_steps:
            if not isinstance(item, dict):
                continue
            action = str(item.get("action", "")).strip()
            if not action:
                continue
            params = item.get("parameters", {})
            if not isinstance(params, dict):
                params = {}
            steps.append(GoalStep(
                step=int(item.get("step", len(steps) + 1)),
                action=action,
                parameters=params,
                description=item.get("description"),
            ))

        return GoalPlan(
            mode=mode,
            goal=goal,
            plan=steps,
            message=message,
            deliberation=deliberation,
        )

    def _extract_json(self, text: str) -> Optional[dict]:
        """Extract first valid JSON object from text."""
        # Strip markdown fences
        text = re.sub(r"```(?:json)?", "", text).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # Find first {...}
        for m in re.finditer(r'\{.*\}', text, re.DOTALL):
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                continue
        return None

    def _chat_fallback(self, goal: str, error_detail: str) -> GoalPlan:
        """Return a safe chat-mode fallback when LLM fails."""
        return GoalPlan(
            mode="chat",
            goal=goal,
            plan=[],
            message=f"I encountered an issue generating a plan: {error_detail[:200]}",
        )

    async def plan(self, goal: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Single-call deliberative planning via SANDHYA_SYSTEM_PROMPT.

        The system prompt already encodes the full Planner → Critic → Refiner
        → Execution Strategist reasoning chain, so a single LLM call produces
        the complete deliberation + final_plan JSON.

        Args:
            goal:    User's natural-language goal.
            context: Optional dict of additional context (previous results, memory, etc.).

        Returns:
            Raw JSON string from the LLM — structure is NOT altered.
            On LLM failure, returns an ``LLM_ERROR:`` prefixed string.
        """
        context = context or {}

        prompt = f"""
{SANDHYA_SYSTEM_PROMPT}

User Goal:
{goal}

Context:
{context}

Return ONLY valid JSON.
"""

        logger.info(f"[GoalPlanner.plan] Single-call deliberation for: {goal[:80]!r}")
        response = await self.llm.complete(prompt)
        logger.debug(f"[GoalPlanner.plan] Raw response: {response[:300]!r}")
        return response
