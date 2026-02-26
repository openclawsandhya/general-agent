"""
Trial Generalized Automation Agent Backend
"""

__version__ = "1.0.0"
__author__ = "Agent Development Team"

from .llm_client import LLMClient, create_llm_client
from .intent_router import IntentRouter
from .planner import Planner
from .browser_controller import BrowserController
from .executor import Executor
from .utils.logger import get_logger

__all__ = [
    "LLMClient",
    "create_llm_client",
    "IntentRouter",
    "Planner",
    "BrowserController",
    "Executor",
    "get_logger",
]
