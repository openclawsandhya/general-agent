"""
Validation Agent for SANDHYA.AI.

After each autonomous execution loop, sends the goal, executed steps,
and collected results back to the LLM and asks:
  "Is the goal fully completed? If not, generate the next plan."

This creates a self-improving autonomous loop:
  Plan → Execute → Validate → Re-plan (if needed) → Repeat

ValidationResult:
  completed          bool     — True if goal is satisfied
  completion_pct     int      — 0-100
  reason             str      — LLM explanation
  missing_steps      list     — steps still needed
  next_plan          list     — [{step, action, parameters}, ...]
"""

import json
import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from .system_prompt import VALIDATION_PROMPT_TEMPLATE
from .llm_client import LLMClient
from .utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of goal completion validation."""
    completed: bool
    completion_pct: int = 0
    reason: str = ""
    missing_steps: List[str] = field(default_factory=list)
    next_plan: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def needs_continuation(self) -> bool:
        """True when the goal is incomplete and there are next steps."""
        return not self.completed and bool(self.next_plan)


class ValidationAgent:
    """
    LLM-backed validator that evaluates whether a goal has been achieved.

    Usage:
        agent = ValidationAgent(llm_client)
        result = await agent.validate(goal, steps_summary, results_summary)
        if result.needs_continuation:
            run next_plan ...
    """

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
        logger.info("[ValidationAgent] Initialized")

    async def validate(
        self,
        goal: str,
        steps_summary: str,
        results_summary: str,
    ) -> ValidationResult:
        """
        Ask the LLM whether the goal is complete and what (if any) remains.

        Args:
            goal:            The original user goal string.
            steps_summary:   Formatted string of all executed steps.
            results_summary: Formatted string of collected results.

        Returns:
            ValidationResult with completion status and optional next plan.
        """
        prompt = VALIDATION_PROMPT_TEMPLATE.format(
            goal=goal,
            steps_summary=steps_summary,
            results_summary=results_summary,
        )

        logger.info(f"[ValidationAgent] Validating goal: {goal[:80]!r}")
        logger.debug(f"[ValidationAgent] Steps:\n{steps_summary[:500]}")

        try:
            raw = await self.llm.generate_response(
                prompt=prompt,
                system_prompt=(
                    "You are a strict goal completion validator. "
                    "Respond ONLY with valid JSON. No extra text."
                ),
                temperature=0.1,   # low temperature → consistent evaluation
                max_tokens=400,
            )

            logger.debug(f"[ValidationAgent] Raw response: {raw[:300]!r}")

            if raw.startswith("LLM_ERROR"):
                logger.warning(f"[ValidationAgent] LLM error during validation: {raw}")
                return ValidationResult(
                    completed=False,
                    reason=f"Validation skipped — LLM error: {raw}",
                )

            return self._parse_validation(raw)

        except Exception as e:
            logger.error(f"[ValidationAgent] Exception: {e}", exc_info=True)
            return ValidationResult(
                completed=False,
                reason=f"Validation failed with exception: {e}",
            )

    def _parse_validation(self, raw: str) -> ValidationResult:
        """Parse LLM JSON response into a ValidationResult."""
        data = self._extract_json(raw)

        if data is None:
            logger.warning("[ValidationAgent] Could not parse JSON, defaulting to incomplete")
            return ValidationResult(
                completed=False,
                reason="Could not parse validation response.",
            )

        completed = bool(data.get("completed", False))
        pct = int(data.get("completion_percentage", 100 if completed else 0))
        reason = str(data.get("reason", ""))
        missing = data.get("missing_steps", [])
        if not isinstance(missing, list):
            missing = []

        raw_plan = data.get("next_plan", [])
        if not isinstance(raw_plan, list):
            raw_plan = []

        # Normalise next_plan entries
        next_plan = []
        for item in raw_plan:
            if isinstance(item, dict) and "action" in item:
                next_plan.append({
                    "step": item.get("step", len(next_plan) + 1),
                    "action": item["action"],
                    "parameters": item.get("parameters", {}),
                })

        result = ValidationResult(
            completed=completed,
            completion_pct=pct,
            reason=reason,
            missing_steps=missing,
            next_plan=next_plan,
        )

        logger.info(
            f"[ValidationAgent] result: completed={completed} "
            f"pct={pct} next_steps={len(next_plan)}"
        )
        return result

    def _extract_json(self, text: str) -> Optional[dict]:
        """Extract first valid JSON object from a string."""
        # Remove markdown code fences if present
        text = re.sub(r"```(?:json)?", "", text).strip()

        # Try whole string first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Find first {...} block
        pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        for match in re.finditer(pattern, text, re.DOTALL):
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                continue
        return None
