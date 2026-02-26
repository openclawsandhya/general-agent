"""
Data models and schemas for the Agent API.
"""

from enum import Enum
from typing import List, Optional, Any
from pydantic import BaseModel, Field


class IntentType(str, Enum):
    """Classification of user intent."""
    CHAT = "chat"
    AUTOMATION = "automation"


class ActionType(str, Enum):
    """Supported browser automation actions."""
    OPEN_URL = "open_url"
    SEARCH = "search"
    CLICK = "click"
    SCROLL = "scroll"
    EXTRACT_TEXT = "extract_text"
    WAIT = "wait"
    FILL_INPUT = "fill_input"
    NAVIGATE_BACK = "navigate_back"


class ActionStep(BaseModel):
    """Single step in an automation plan."""
    action: ActionType
    value: Optional[str] = None
    selector: Optional[str] = None
    duration_ms: Optional[int] = None
    description: Optional[str] = Field(
        None, 
        description="Human-readable description of the action"
    )

    class Config:
        use_enum_values = True


class ActionPlan(BaseModel):
    """Structured plan for browser automation."""
    steps: List[ActionStep]
    reasoning: Optional[str] = Field(
        None,
        description="Why these steps were chosen"
    )

    class Config:
        use_enum_values = True


class MessageRequest(BaseModel):
    """User message to the agent."""
    message: str = Field(..., description="User message")
    session_id: Optional[str] = Field(None, description="Session ID for context")


class MessageResponse(BaseModel):
    """Agent response to user."""
    response: str
    intent: IntentType
    plan: Optional[ActionPlan] = None
    session_id: Optional[str] = None

    class Config:
        use_enum_values = True


class StreamingMessage(BaseModel):
    """Streaming message chunk."""
    type: str  # "status", "response", "progress"
    content: str
    is_final: bool = False

    class Config:
        use_enum_values = True


class AgentConfig(BaseModel):
    """Configuration for the agent."""
    llm_base_url: str = Field(
        default="http://localhost:1234/v1",
        description="LM Studio API endpoint"
    )
    llm_model: str = Field(
        default="mistral-7b-instruct",
        description="Model name for the LLM"
    )
    auto_retry: bool = Field(
        default=True,
        description="Automatically retry failed actions"
    )
    timeout_seconds: int = Field(
        default=30,
        description="Timeout for browser operations"
    )
    headless_mode: bool = Field(
        default=True,
        description="Run browser in headless mode"
    )
