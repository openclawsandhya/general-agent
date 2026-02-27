"""
Autonomous goal-driven agent controller.

Implements a continuous reasoning and acting loop that:
1. Observes current browser state
2. Asks LLM what to do next to achieve goal
3. Executes next actions
4. Evaluates progress
5. Repeats until goal achieved or max iterations reached

This enables fully autonomous goal accomplishment beyond single-plan execution.
"""

import json
import re
from typing import Callable, List, Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field

from .models.schemas import ActionPlan, ActionStep, ActionType
from .browser_controller import BrowserController
from .executor import Executor
from .llm_client import LLMClient
from .utils.logger import get_logger


logger = get_logger(__name__)


@dataclass
class GoalCompletionReport:
    """Report on goal completion attempt."""
    goal: str
    completed: bool
    iterations: int
    final_state: Dict[str, Any]
    actions_taken: List[str] = field(default_factory=list)
    reason: str = ""


class AutonomousAgentController:
    """
    Autonomous agent that runs goal-driven loops until completion.
    
    The agent observes state, decides actions via LLM, executes them,
    and evaluates progress in a continuous loop.
    """
    
    def __init__(
        self,
        browser_controller: BrowserController,
        executor: Executor,
        llm_client: LLMClient,
        max_iterations: int = 10,
    ):
        """
        Initialize autonomous agent controller.
        
        Args:
            browser_controller: Browser automation controller
            executor: Plan executor
            llm_client: LLM for reasoning
            max_iterations: Maximum loop iterations before timeout
        """
        self.browser = browser_controller
        self.executor = executor
        self.llm = llm_client
        self.max_iterations = max_iterations
        
        self.status_callback: Optional[Callable[[str], None]] = None
        self.iteration_count = 0
        self.previous_observations: List[Dict[str, Any]] = []
        
        logger.info(
            f"AutonomousAgentController initialized "
            f"(max_iterations={max_iterations})"
        )
    
    def set_status_callback(self, callback: Callable[[str], None]) -> None:
        """
        Set callback for status updates.
        
        Args:
            callback: Function to call with status messages
        """
        self.status_callback = callback
    
    async def run_goal(self, goal: str) -> str:
        """
        Execute autonomous goal loop.
        
        Main entry point that runs the agent until goal is achieved
        or max iterations reached.
        
        Args:
            goal: Goal to achieve (natural language)
            
        Returns:
            Completion report message
        """
        logger.info(f"Starting autonomous goal loop: {goal}")
        
        try:
            # Start browser if not running
            if not self.browser.page:
                await self._send_status("🚀 Starting browser...")
                await self.browser.start()
            
            actions_taken = []
            final_observation = None
            
            # Main loop
            for iteration in range(self.max_iterations):
                self.iteration_count = iteration + 1
                
                await self._send_status(
                    f"📍 Step {self.iteration_count}/{self.max_iterations}: "
                    f"Analyzing current state..."
                )
                
                # 1. Observe current state
                observation = await self._observe_state()
                final_observation = observation
                
                if "error" in observation:
                    logger.error(f"Error observing state: {observation['error']}")
                    await self._send_status(
                        f"⚠️ Error observing state, stopping."
                    )
                    break
                
                # Log current state
                logger.debug(
                    f"Iteration {self.iteration_count}: "
                    f"URL={observation.get('url')}, "
                    f"Title={observation.get('title', '')[:50]}"
                )
                
                # 2. Check if goal is complete
                goal_complete = await self._is_goal_complete(goal, observation)
                if goal_complete:
                    await self._send_status("✅ Goal achieved!")
                    
                    report = GoalCompletionReport(
                        goal=goal,
                        completed=True,
                        iterations=self.iteration_count,
                        final_state=observation,
                        actions_taken=actions_taken,
                        reason="Goal completed successfully"
                    )
                    return self._format_completion_report(report)
                
                # 3. Check for repetitive loops
                if self._is_repetitive_loop(observation):
                    await self._send_status(
                        "🔄 Detected repetitive loop, stopping to avoid infinite cycle."
                    )
                    
                    report = GoalCompletionReport(
                        goal=goal,
                        completed=False,
                        iterations=self.iteration_count,
                        final_state=observation,
                        actions_taken=actions_taken,
                        reason="Repetitive loop detected"
                    )
                    return self._format_completion_report(report)
                
                # 4. Decide next actions
                await self._send_status(
                    "🤔 Reasoning about next steps..."
                )
                
                plan = await self._decide_next_actions(goal, observation)
                
                if not plan or not plan.steps:
                    await self._send_status(
                        "🛑 No more actions suggested by reasoning loop."
                    )
                    
                    report = GoalCompletionReport(
                        goal=goal,
                        completed=False,
                        iterations=self.iteration_count,
                        final_state=observation,
                        actions_taken=actions_taken,
                        reason="No more actions available"
                    )
                    return self._format_completion_report(report)
                
                # 5. Execute actions
                action_desc = self._describe_actions(plan)
                await self._send_status(
                    f"⚡ Executing: {action_desc}"
                )
                
                try:
                    result = await self.executor.execute(plan)
                    actions_taken.append(action_desc)
                    
                    logger.info(f"Execution result: {result}")
                    
                except Exception as e:
                    logger.error(f"Execution failed: {e}")
                    await self._send_status(f"❌ Action failed: {str(e)}")
                    actions_taken.append(f"FAILED: {action_desc}")
            
            # Max iterations reached
            await self._send_status(
                f"⏱️  Max iterations ({self.max_iterations}) reached."
            )
            
            report = GoalCompletionReport(
                goal=goal,
                completed=False,
                iterations=self.iteration_count,
                final_state=final_observation or {},
                actions_taken=actions_taken,
                reason=f"Max iterations ({self.max_iterations}) reached"
            )
            return self._format_completion_report(report)
        
        except Exception as e:
            logger.error(f"Error in autonomous loop: {e}", exc_info=True)
            await self._send_status(f"💥 Critical error: {str(e)}")
            
            report = GoalCompletionReport(
                goal=goal,
                completed=False,
                iterations=self.iteration_count,
                final_state={},
                reason=f"Critical error: {str(e)}"
            )
            return self._format_completion_report(report)
    
    async def _observe_state(self) -> Dict[str, Any]:
        """
        Collect current browser state.
        
        Returns:
            Dictionary with:
            - url: Current page URL
            - title: Page title
            - text: Visible page text (summarized)
            - timestamp: When observation was taken
        """
        try:
            logger.debug("Observing browser state...")
            
            url = await self.browser.get_current_url()
            title = await self.browser.get_title()
            text = await self.browser.extract_text()
            
            # Summarize text (limit to 1500 chars to avoid token bloat)
            text_summary = text[:1500] if text else ""
            
            observation = {
                "url": url,
                "title": title,
                "text": text_summary,
                "timestamp": datetime.now().isoformat(),
            }
            
            logger.debug(f"Observed state: URL={url}, Title={title[:50]}")
            
            return observation
        
        except Exception as e:
            logger.error(f"Error observing state: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def _decide_next_actions(
        self,
        goal: str,
        observation: Dict[str, Any],
    ) -> Optional[ActionPlan]:
        """
        Use LLM to decide next actions toward goal.
        
        Args:
            goal: Goal to achieve
            observation: Current browser state observation
            
        Returns:
            ActionPlan with next steps or None if error
        """
        logger.info(f"Deciding next actions for goal: {goal}")
        
        system_prompt = """You are an autonomous browser automation agent.
Your task is to decide the NEXT STEPS to take to achieve the given goal.

Available actions:
- open_url: Open a URL. Needs 'value' (the URL)
- search: Search a query. Needs 'value' (search term)
- click: Click an element. Needs 'selector' (CSS selector)
- click_first_result: Click first search result. No parameters.
- scroll: Scroll page. Needs 'value' ('up' or 'down') and optionally 'amount'
- extract_text: Extract page text. Optional 'selector'
- fill_input: Fill input field. Needs 'selector' and 'value'
- wait: Wait duration. Needs 'duration_ms'
- navigate_back: Go back. No parameters.

IMPORTANT:
1. Return ONLY valid JSON, no other text
2. Decide 1-3 practical next steps
3. If goal already achieved, return empty steps array
4. Be specific about CSS selectors

JSON Format:
{
  "steps": [
    {"action": "action_name", "value": "...", "description": "..."},
    ...
  ],
  "reasoning": "Why these steps will help achieve the goal"
}"""

        user_prompt = f"""GOAL: {goal}

CURRENT BROWSER STATE:
- URL: {observation.get('url')}
- Page Title: {observation.get('title')}
- Visible Text on Page:
{observation.get('text')}

---

What are the NEXT STEPS to take toward the goal?
Return JSON with 'steps' array and 'reasoning' string."""

        try:
            response = self.llm.generate_response_sync(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.4,
                max_tokens=1024
            )
            
            logger.debug(f"LLM response: {response[:200]}")
            
            # Extract JSON from response
            plan_dict = self._extract_json(response)
            
            if not plan_dict:
                logger.warning("Failed to extract JSON from LLM response")
                return None
            
            if "steps" not in plan_dict:
                logger.warning("LLM response missing 'steps' key")
                return None
            
            # Convert to ActionPlan
            steps = []
            for step_data in plan_dict.get("steps", []):
                try:
                    action_name = step_data.get("action", "wait")
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
                    continue
            
            plan = ActionPlan(
                steps=steps,
                reasoning=plan_dict.get("reasoning", "")
            )
            
            logger.info(f"Generated plan with {len(plan.steps)} steps")
            return plan
        
        except Exception as e:
            logger.error(f"Error deciding actions: {e}", exc_info=True)
            return None
    
    async def _is_goal_complete(
        self,
        goal: str,
        observation: Dict[str, Any],
    ) -> bool:
        """
        Check if goal has been achieved.
        
        Args:
            goal: Goal to check
            observation: Current browser state
            
        Returns:
            True if goal complete, False otherwise
        """
        logger.debug(f"Checking if goal complete: {goal}")
        
        system_prompt = """You are evaluating if a goal has been achieved.
Look at the current browser state and determine if the goal is complete.

Respond with EXACTLY one word:
- "yes" if goal is achieved
- "no" if goal is not yet achieved"""

        user_prompt = f"""GOAL: {goal}

CURRENT BROWSER STATE:
- URL: {observation.get('url')}
- Page Title: {observation.get('title')}
- Page Text (first 500 chars):
{observation.get('text', '')[:500]}

---

Is the goal achieved? Answer only with 'yes' or 'no'."""

        try:
            response = self.llm.generate_response_sync(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.1,  # Low temperature for consistency
                max_tokens=10
            )
            
            is_complete = "yes" in response.lower()
            logger.debug(f"Goal completion check: {is_complete}")
            
            return is_complete
        
        except Exception as e:
            logger.error(f"Error checking goal completion: {e}")
            return False
    
    def _is_repetitive_loop(self, observation: Dict[str, Any]) -> bool:
        """
        Detect if agent is stuck in a repetitive loop.
        
        Uses simple heuristic: check if last N observations have same URL.
        
        Args:
            observation: Current observation
            
        Returns:
            True if repetitive loop detected
        """
        current_url = observation.get("url", "")
        
        # Check if last 3 observations have same URL
        if len(self.previous_observations) >= 3:
            recent = self.previous_observations[-3:]
            same_urls = sum(
                1 for obs in recent
                if obs.get("url") == current_url
            )
            
            if same_urls >= 3:
                logger.warning("Repetitive loop detected")
                return True
        
        # Store observation
        self.previous_observations.append(observation)
        
        # Keep only last 10 observations
        if len(self.previous_observations) > 10:
            self.previous_observations = self.previous_observations[-10:]
        
        return False
    
    def _extract_json(self, text: str) -> Optional[dict]:
        """
        Extract JSON from text.
        
        Args:
            text: Text potentially containing JSON
            
        Returns:
            Parsed JSON dict or None
        """
        # Try to find JSON object in text
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, text, re.DOTALL)
        
        for match in reversed(matches):  # Try from end first
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
        
        # Try parsing entire text
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None
    
    def _describe_actions(self, plan: ActionPlan) -> str:
        """
        Create human-readable description of actions.
        
        Args:
            plan: ActionPlan to describe
            
        Returns:
            Description string
        """
        if not plan.steps:
            return "No actions"
        
        descriptions = []
        for step in plan.steps[:3]:  # Limit to first 3
            if step.description:
                descriptions.append(step.description)
            else:
                action_name = step.action.replace("_", " ").title()
                if step.value:
                    descriptions.append(f"{action_name}: {step.value}")
                else:
                    descriptions.append(action_name)
        
        result = " → ".join(descriptions)
        if len(plan.steps) > 3:
            result += f" (+ {len(plan.steps) - 3} more)"
        
        return result
    
    async def _send_status(self, message: str) -> None:
        """
        Send status update via callback or logging.
        
        Args:
            message: Status message
        """
        if self.status_callback:
            self.status_callback(message)
        else:
            logger.info(f"Status: {message}")
    
    def _format_completion_report(self, report: GoalCompletionReport) -> str:
        """
        Format goal completion report for user.
        
        Args:
            report: GoalCompletionReport object
            
        Returns:
            Formatted report string
        """
        lines = []
        
        # Header
        if report.completed:
            lines.append("✅ GOAL ACHIEVED!\n")
        else:
            lines.append("⚠️ GOAL NOT COMPLETED\n")
        
        # Summary
        lines.append(f"Goal: {report.goal}")
        lines.append(f"Iterations: {report.iterations}/{self.max_iterations}")
        lines.append(f"Reason: {report.reason}")
        
        # Final state
        if report.final_state:
            lines.append(f"\nFinal State:")
            lines.append(f"  URL: {report.final_state.get('url', 'N/A')}")
            lines.append(f"  Title: {report.final_state.get('title', 'N/A')}")
        
        # Actions taken
        if report.actions_taken:
            lines.append(f"\nActions Taken: {len(report.actions_taken)}")
            for i, action in enumerate(report.actions_taken[:5], 1):
                lines.append(f"  {i}. {action}")
            if len(report.actions_taken) > 5:
                lines.append(f"  ... and {len(report.actions_taken) - 5} more")
        
        return "\n".join(lines)
    
    def get_iteration_count(self) -> int:
        """Get current iteration count."""
        return self.iteration_count
    
    def reset(self) -> None:
        """Reset controller state for new goal."""
        self.iteration_count = 0
        self.previous_observations = []
        logger.info("Controller reset")
