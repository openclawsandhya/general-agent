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
    """Supported agent actions — browser, filesystem, code, and web research."""

    # ---- Browser Automation ----
    OPEN_URL = "open_url"
    SEARCH = "search"
    CLICK = "click"
    SCROLL = "scroll"
    EXTRACT_TEXT = "extract_text"
    WAIT = "wait"
    FILL_INPUT = "fill_input"
    NAVIGATE_BACK = "navigate_back"
    TYPE = "type"                       # alias for fill_input (SANDHYA spec)
    EXTRACT_CONTENT = "extract_content" # web-based content extraction
    PRESS_KEY = "press_key"             # keyboard key press (Enter, Escape…)
    GET_PAGE_INFO = "get_page_info"     # get current URL + title
    SCREENSHOT = "screenshot"           # capture full-page screenshot

    # ---- File System ----
    CREATE_FILE = "create_file"
    READ_FILE = "read_file"
    LIST_FILES = "list_files"
    DELETE_FILE = "delete_file"

    # ---- Code Execution ----
    RUN_PYTHON = "run_python"
    RUN_SHELL = "run_shell"

    # ---- Web Research ----
    SEARCH_WEB = "search_web"


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


class ExecutionReport(BaseModel):
    """Report of an automation execution."""
    success: bool
    steps_completed: int
    total_steps: int
    execution_message: str
    reasoning: str
    details: Optional[str] = None


# ============================================================================
# SANDHYA.AI Autonomous Goal Models
# ============================================================================

class GoalStep(BaseModel):
    """
    A single step in a SANDHYA.AI autonomous goal plan.

    Format matches the system prompt JSON spec:
      {"step": 1, "action": "tool_name", "parameters": {...}}
    """
    step: int = Field(1, description="Step number")
    action: str = Field(..., description="Tool name to execute")
    parameters: dict = Field(default_factory=dict, description="Tool parameters")
    description: Optional[str] = Field(None, description="Human-readable step description")

    class Config:
        extra = "allow"


class GoalPlan(BaseModel):
    """
    A structured autonomous execution plan returned by the GoalPlanner.

    Generated from SANDHYA_SYSTEM_PROMPT responses.
    Supports new deliberation format (planner→critic→refiner) as well as
    legacy format (flat 'plan' key).
    """
    mode: str = Field("controlled_automation", description="chat | controlled_automation")
    goal: str = Field("", description="Interpreted user goal")
    plan: List[GoalStep] = Field(default_factory=list, description="Ordered execution steps (final)")
    message: str = Field("", description="User-friendly plan summary")
    deliberation: Optional[dict] = Field(
        None,
        description="Multi-agent deliberation payload: planner_plan, critic_feedback, refined_plan"
    )

    class Config:
        extra = "allow"


class AutonomousRunReport(BaseModel):
    """Final report after an autonomous goal execution loop."""
    goal: str
    mode: str
    completed: bool
    iterations: int
    steps_executed: int
    final_message: str
    validation_reason: str = ""
    task_id: str = ""

    class Config:
        use_enum_values = True
