import json
from typing import Dict, Any

from backend.prompts.reasoning_wrapper_prompt import REASONING_WRAPPER_PROMPT
from backend.prompts.reasoning_agents_prompt import (
    PLANNER_AGENT_PROMPT,
    CRITIC_AGENT_PROMPT,
    REFINER_AGENT_PROMPT,
)

class ReasoningWrapper:
    """
    Cognitive planning layer that performs:
    Planner → Critic → Refiner reasoning loop
    before returning a final executable plan.
    """

    def __init__(self, llm_client):
        self.llm = llm_client

    async def generate_validated_plan(
        self,
        goal: str,
        tools: Dict[str, Any],
        context: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        context = context or {}

        planner_plan = await self._call_planner(goal, tools, context)
        critique = await self._call_critic(goal, planner_plan)
        refined_plan = await self._call_refiner(goal, planner_plan, critique)

        return refined_plan

    async def _call_planner(self, goal, tools, context):
        prompt = f"""
{PLANNER_AGENT_PROMPT}

Goal:
{goal}

Available Tools:
{json.dumps(tools, indent=2)}

Context:
{json.dumps(context, indent=2)}

Return ONLY JSON plan.
"""
        response = await self.llm.complete(prompt)
        return self._safe_json(response)

    async def _call_critic(self, goal, plan):
        prompt = f"""
{CRITIC_AGENT_PROMPT}

Goal:
{goal}

Planner Plan:
{json.dumps(plan, indent=2)}
"""
        response = await self.llm.complete(prompt)
        return self._safe_json(response)

    async def _call_refiner(self, goal, original_plan, critique):
        prompt = f"""
{REFINER_AGENT_PROMPT}

Goal:
{goal}

Original Plan:
{json.dumps(original_plan, indent=2)}

Critic Issues:
{json.dumps(critique, indent=2)}

Return ONLY final improved executable JSON plan.
"""
        response = await self.llm.complete(prompt)
        return self._safe_json(response)

    def _safe_json(self, text: str) -> Dict[str, Any]:
        try:
            return json.loads(text)
        except Exception:
            return {
                "mode": "chat",
                "goal": "JSON parsing failure",
                "plan": [],
                "message": "Model returned invalid JSON",
            }