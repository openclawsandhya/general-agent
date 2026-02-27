"""
SANDHYA.AI — Fully Autonomous General-Purpose Execution Agent
"""

__version__ = "3.0.0"
__author__ = "SANDHYA.AI Development Team"

from .llm_client import LLMClient, create_llm_client
from .intent_router import IntentRouter
from .planner import Planner, GoalPlanner
from .browser_controller import BrowserController
from .executor import Executor, AutonomousGoalExecutor
from .memory import MemoryManager
from .validation_agent import ValidationAgent
from .system_prompt import SANDHYA_SYSTEM_PROMPT
from .utils.logger import get_logger

__all__ = [
    "LLMClient",
    "create_llm_client",
    "IntentRouter",
    "Planner",
    "GoalPlanner",
    "BrowserController",
    "Executor",
    "AutonomousGoalExecutor",
    "MemoryManager",
    "ValidationAgent",
    "SANDHYA_SYSTEM_PROMPT",
    "get_logger",
]
