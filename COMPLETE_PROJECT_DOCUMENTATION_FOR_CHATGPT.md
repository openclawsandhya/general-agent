# COMPLETE PROJECT DOCUMENTATION FOR CHATGPT ASSISTANCE
# General Autonomous Browser Automation Agent

**Generated:** February 26, 2026  
**Purpose:** Comprehensive documentation for ChatGPT to understand and assist with this project

---

## TABLE OF CONTENTS

1. [Project Overview](#project-overview)
2. [System Architecture](#system-architecture)
3. [Technology Stack](#technology-stack)
4. [Project Structure](#project-structure)
5. [Core Components Deep Dive](#core-components-deep-dive)
6. [Data Models & Schemas](#data-models--schemas)
7. [API Endpoints](#api-endpoints)
8. [Workflows & Use Cases](#workflows--use-cases)
9. [Configuration](#configuration)
10. [Installation & Setup](#installation--setup)
11. [Testing](#testing)
12. [Dependencies](#dependencies)
13. [Code Examples](#code-examples)
14. [Troubleshooting](#troubleshooting)
15. [Future Enhancements](#future-enhancements)

---

## PROJECT OVERVIEW

### What This Project Does

This is a **production-ready autonomous browser automation agent** that combines:
- **Conversational AI** (via local LLM through LM Studio)
- **Browser Automation** (via Playwright)
- **Autonomous Goal Execution** (LLM-driven reasoning loop)
- **Human-in-the-Loop Approval** (for controlled automation)

### Key Features

✅ **Three Operation Modes:**
1. **Chat Mode** - Natural conversation using LLM
2. **Controlled Automation** - Human-approved browser automation
3. **Autonomous Goal Mode** - Self-guided goal achievement with continuous reasoning

✅ **Intelligent Architecture:**
- Intent detection (automatic routing)
- Session management
- Conversation history
- Safety constraints & loop detection
- Real-time status updates

✅ **Production-Ready:**
- FastAPI REST API
- Async/await for concurrency
- Comprehensive error handling
- Structured logging
- Type validation (Pydantic)
- CORS support

### Business Value

- **Automates repetitive web tasks** (search, data extraction, form filling)
- **Provides conversational interface** for complex automation
- **Requires human approval** for sensitive actions (safety)
- **Adapts dynamically** to changing page states
- **Scales** via REST API for multi-user support

---

## SYSTEM ARCHITECTURE

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client (Frontend)                        │
│                    (React/Lovable/Any UI)                       │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP/REST
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Server                             │
│                       (api_server.py)                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │          AgentOrchestrator (orchestrator.py)             │  │
│  │  • Intent Detection                                      │  │
│  │  • Session Management                                    │  │
│  │  • Approval Workflow                                     │  │
│  └──────────────────┬───────────────────────────────────────┘  │
└─────────────────────┼───────────────────────────────────────────┘
                      │
      ┌───────────────┼───────────────┐
      │               │               │
      ▼               ▼               ▼
┌──────────┐   ┌──────────────┐   ┌─────────────────────┐
│  Chat    │   │ Controlled   │   │   Autonomous        │
│  Mode    │   │ Automation   │   │   Goal Mode         │
└────┬─────┘   └──────┬───────┘   └──────┬──────────────┘
     │                │                   │
     ▼                ▼                   ▼
┌──────────┐   ┌────────────────┐   ┌──────────────────────┐
│LLMClient │   │ Planner        │   │AutonomousController  │
│          │   │ +              │   │  • Observe Loop      │
│          │   │ Executor       │   │  • Reason (LLM)      │
│          │   │ +              │   │  • Act               │
│          │   │ Browser        │   │  • Repeat            │
└──────────┘   └────────────────┘   └──────────────────────┘
     │                │                        │
     └────────────────┼────────────────────────┘
                      ▼
         ┌────────────────────────────┐
         │     BrowserController      │
         │      (Playwright)          │
         └────────────────────────────┘
                      │
                      ▼
         ┌────────────────────────────┐
         │      Chromium Browser      │
         └────────────────────────────┘
```

### Component Relationships

```
AutomationAgent (agent_core.py)
├── Uses: Planner (plan generation)
├── Uses: Executor (plan execution)
├── Uses: LLMClient (chat responses)
└── Manages: Conversation history, pending plans, approval workflow

AutonomousAgentController (agent_controller.py)
├── Uses: BrowserController (state observation)
├── Uses: Executor (action execution)
├── Uses: LLMClient (reasoning & goal completion)
└── Implements: Observe → Reason → Act loop

AgentOrchestrator (orchestrator.py)
├── Uses: AutomationAgent (controlled mode)
├── Uses: AutonomousAgentController (autonomous mode)
├── Uses: LLMClient (chat mode)
└── Routes: Chat vs Automation vs Autonomous

BrowserController (browser_controller.py)
├── Uses: Playwright
└── Provides: Browser actions (open, click, type, scroll, etc.)

Executor (executor.py)
├── Uses: BrowserController
└── Executes: Sequential action plans

Planner (planner.py)
├── Uses: LLMClient
└── Generates: Structured ActionPlan from natural language

PageAnalyzer (page_analyzer.py)
├── Uses: Playwright Page
└── Extracts: Structured page state (links, buttons, inputs, text)

HybridPlanner (planner.py)
├── Uses: LLMClient (fallback)
├── Uses: PageAnalyzer
└── Decides: Next action with deterministic rules + LLM

LLMPlanner (llm_planner.py)
├── Uses: LM Studio API (OpenAI-compatible)
└── Decides: Next action purely via LLM reasoning

ChatResponder (chat_responder.py)
├── Uses: LLMClient
└── Generates: Human-friendly explanations

ApprovalManager (approval_manager.py)
├── Uses: ChatResponder
└── Manages: High-risk action approvals
```

---

## TECHNOLOGY STACK

### Backend Technologies

| Category | Technology | Version | Purpose |
|----------|-----------|---------|---------|
| **Language** | Python | 3.9+ | Core language |
| **Web Framework** | FastAPI | 0.104.1 | REST API server |
| **ASGI Server** | Uvicorn | 0.24.0 | Production server |
| **Browser Automation** | Playwright | 1.40.0 | Headless browser control |
| **Data Validation** | Pydantic | 2.5.0 | Model validation |
| **HTTP Client** | Requests | 2.31.0 | External API calls |
| **LLM Provider** | LM Studio | N/A | Local LLM inference |
| **Async** | asyncio | Built-in | Concurrent operations |

### External Dependencies

- **LM Studio** (http://localhost:1234) - Local LLM server (OpenAI-compatible API)
- **Chromium** - Browser for Playwright automation

### Development Tools

- **Logging** - Python logging module
- **Type Hints** - Python type annotations
- **Dataclasses** - Python dataclasses for structured data

---

## PROJECT STRUCTURE

### Directory Layout

```
general-agent/
│
├── backend/                          # All backend code
│   │
│   ├── 🎯 Core Modules (Main Logic)
│   │   ├── api_server.py            # FastAPI server & endpoints
│   │   ├── agent_core.py            # AutomationAgent (controlled mode)
│   │   ├── agent_controller.py      # (Legacy) Early autonomous controller
│   │   ├── autonomous_controller.py # ⭐ AutonomousAgentController (new)
│   │   ├── orchestrator.py          # ⭐ AgentOrchestrator (routing layer)
│   │   ├── planner.py               # Planner & HybridPlanner
│   │   ├── llm_planner.py           # LLMPlanner (pure LLM decisions)
│   │   ├── executor.py              # Executor (basic plan execution)
│   │   ├── action_executor.py       # ActionExecutor (advanced execution)
│   │   ├── browser_controller.py     # BrowserController (Playwright)
│   │   ├── page_analyzer.py         # PageAnalyzer (state extraction)
│   │   ├── llm_client.py            # LLMClient (LM Studio API)
│   │   ├── intent_router.py         # IntentRouter (classification)
│   │   ├── chat_responder.py        # ChatResponder (explanations)
│   │   ├── approval_manager.py      # ApprovalManager (safety)
│   │   └── config.py                # Configuration settings
│   │
│   ├── 📦 Python Packages
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── schemas.py           # Pydantic models
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── logger.py            # Logging setup
│   │
│   ├── 📚 Documentation
│   │   ├── README.md                # Main documentation
│   │   ├── AGENT_CORE.md            # AutomationAgent docs
│   │   ├── AUTONOMOUS_AGENT.md      # Autonomous controller docs
│   │   ├── IMPLEMENTATION_SUMMARY.md# Complete implementation guide
│   │   └── QUICK_START.md           # Getting started guide
│   │
│   ├── 🔧 Configuration
│   │   ├── requirements.txt         # Python dependencies
│   │   └── pyrightconfig.json       # Type checker config
│   │
│   └── 🧪 Testing (Optional)
│       ├── test_autonomous_agent.py # Unit tests
│       └── examples.py              # Usage examples
│
├── logs/                             # Log files (auto-created)
│   └── agent.log
│
└── COMPLETE_PROJECT_DOCUMENTATION_FOR_CHATGPT.md  # ⭐ This file
```

### File Purposes

| File | Lines | Primary Responsibility |
|------|-------|------------------------|
| **api_server.py** | 529 | FastAPI server, endpoints, startup/shutdown |
| **orchestrator.py** | 782 | Route messages to chat/automation/autonomous modes |
| **autonomous_controller.py** | 685 | Autonomous observe→reason→act loop |
| **agent_core.py** | 540 | Controlled automation with approval |
| **planner.py** | 1543 | Plan generation (Planner, HybridPlanner, ActionDecision) |
| **llm_planner.py** | ~350 | Pure LLM-based planning |
| **action_executor.py** | 632 | Execute actions against Playwright page |
| **executor.py** | ~150 | Simple sequential plan execution |
| **browser_controller.py** | ~400 | Playwright wrapper for browser control |
| **page_analyzer.py** | 571 | Extract structured page state |
| **llm_client.py** | ~150 | LM Studio API client |
| **chat_responder.py** | 613 | Generate explanations |
| **approval_manager.py** | 522 | Safety approval workflow |
| **schemas.py** | ~120 | Pydantic data models |
| **logger.py** | ~80 | Logging configuration |
| **config.py** | ~50 | Application settings |

---

## CORE COMPONENTS DEEP DIVE

### 1. AgentOrchestrator (orchestrator.py)

**Role:** Central routing engine for all user interactions

**Responsibilities:**
- Detect intent (chat vs automation vs autonomous)
- Route to appropriate mode
- Manage conversation history
- Handle approval workflow
- Enforce safety constraints

**Key Methods:**
```python
async def handle_message(message: str) -> str
    """Main entry point"""

def detect_intent(message: str) -> IntentMode
    """Classify user message"""

async def _handle_chat_mode(message: str) -> str
    """Process conversational chat"""

async def _handle_controlled_automation_mode(message: str) -> str
    """Generate plan and request approval"""

async def _handle_autonomous_goal_mode(message: str) -> str
    """Run autonomous goal loop"""

async def handle_approval(user_input: str) -> str
    """Process approval/rejection"""
```

**Intent Detection Keywords:**
- **Autonomous:** "find best", "research", "explore", "compare", "analyze"
- **Automation:** "open", "search", "click", "navigate", "extract"
- **Chat:** Everything else

**State Management:**
- `conversation_history` - All messages
- `pending_plan` - Plan awaiting approval
- `current_mode` - Active operation mode
- `_approval_pending` - Approval flag

---

### 2. AutonomousAgentController (autonomous_controller.py)

**Role:** Autonomous goal-driven agent with continuous reasoning loop

**Architecture:**
```
Loop (max_iterations):
  1. OBSERVE: Get current page state via PageAnalyzer
  2. CHECK: Ask LLM if goal is complete
     → If YES: Return success
  3. DETECT: Check for repetitive loops
     → If LOOP: Return failure
  4. REASON: Ask LLM/HybridPlanner what to do next
  5. EXECUTE: Run the decided action
  6. RECORD: Store in execution_history & failure_history
  7. REPEAT
```

**Key Features:**
- **True Re-planning:** Each iteration uses full history for decisions
- **Failure Tracking:** Separate history for failed actions
- **Safety Brains:** HybridPlanner as fallback for LLMPlanner
- **Loop Detection:** Prevents infinite loops
- **Execution History:** Complete audit trail

**Key Methods:**
```python
async def run_goal(goal: str, max_steps: int = 20) -> Dict[str, Any]
    """Main autonomous loop"""

async def _observe_page() -> Dict[str, Any]
    """Extract current page state"""

def _is_valid_decision(decision: dict) -> bool
    """Validate LLM decision"""

def _is_selector_safe(decision, page_state) -> bool
    """Check if selector exists"""
```

**Planner Modes:**
- `mode="deterministic"` → HybridPlanner (rules + LLM fallback)
- `mode="llm"` → LLMPlanner (pure LLM reasoning)

**History Tracking:**
```python
_execution_history: List[Dict]  # All actions taken
_failure_history: List[Dict]    # Failed actions only
```

---

### 3. AutomationAgent (agent_core.py)

**Role:** Controlled automation with human-in-the-loop approval

**Workflow:**
```
User: "Search for Python tutorials"
  ↓
Agent: Generates plan
  ↓
Agent: "I will: 1. Open Google, 2. Search, 3. Click first result. Proceed?"
  ↓
User: "yes"
  ↓
Agent: Executes plan
  ↓
Agent: "✅ All steps completed!"
```

**Key Methods:**
```python
async def handle_message(user_message: str) -> str
    """Main entry point"""

def _is_automation_request(message: str) -> bool
    """Intent detection (rule-based)"""

async def _handle_chat_request(user_message: str) -> str
    """Chat mode"""

async def _handle_automation_request(user_message: str) -> str
    """Generate plan and request approval"""

async def _handle_approval_response(user_message: str) -> str
    """Process approval"""

async def _execute_pending_plan(approval: bool) -> str
    """Execute if approved"""
```

**Approval Parsing:**
- **Affirmative:** "yes", "yeah", "ok", "proceed", "sure"
- **Negative:** "no", "cancel", "stop", "don't"

---

### 4. Planner & HybridPlanner (planner.py)

**Planner:** Converts natural language to structured ActionPlan

```python
class Planner:
    def generate_plan(request: str) -> ActionPlan
        """LLM generates plan with steps"""
```

**HybridPlanner:** Intelligent single-action decision maker

**Strategy:**
```
1. Try deterministic rules first (fast, reliable)
   - If search box visible + goal needs search → type in search
   - If relevant button visible → click it
   - Else: fall back to LLM

2. If deterministic fails → LLM reasoning
   - Pass goal, page_state, history to LLM
   - LLM decides next action

3. Validate decision (safety)
   - Check action is supported
   - Check selector exists in page_state
   - Check not in loop
```

**Key Methods:**
```python
async def replan_next_action(
    goal: str,
    page_state: Dict[str, Any],
    history: List[Dict],
    failures: List[Dict]
) -> ActionDecision
    """Decide next action with re-planning"""

def _try_deterministic_decision(...) -> Optional[ActionDecision]
    """Rule-based decision"""

async def _llm_decision(...) -> ActionDecision
    """LLM fallback"""
```

**ActionDecision Structure:**
```python
@dataclass
class ActionDecision:
    thought: str              # Reasoning
    action: str              # click, type, scroll, etc.
    target_selector: Optional[str]  # CSS selector
    input_text: Optional[str]       # Text for type action
    confidence: float        # 0.0-1.0
    explanation: str         # Why this action
    timestamp: str
```

---

### 5. LLMPlanner (llm_planner.py)

**Role:** Pure LLM-based action decision making

**How It Works:**
1. Build prompt with goal, page state, history
2. Call LM Studio API (OpenAI-compatible)
3. Parse JSON response
4. Validate action & selector
5. Return ActionDecision

**Fallback:** Safe scroll action if LLM fails

**Key Methods:**
```python
async def replan_next_action(...) -> ActionDecision
    """Main entry point"""

async def _call_llm(user_prompt: str) -> str
    """Call LM Studio API"""

def _parse_llm_response(response: str) -> Optional[Dict]
    """Extract JSON from response"""

def _validate_and_build_decision(...) -> ActionDecision
    """Validate LLM output"""

def _safe_fallback_decision(reason: str) -> ActionDecision
    """Return safe scroll action"""
```

---

### 6. ActionExecutor (action_executor.py)

**Role:** Execute individual ActionDecision against Playwright page

**Supported Actions:**
- **click** - Click element by selector
- **type** - Fill input field
- **read** - Extract text content
- **scroll** - Scroll page up/down
- **wait** - Pause execution
- **navigate** - Go to URL or back
- **finish** - Mark goal complete

**Execution Flow:**
```python
async def execute(decision: ActionDecision, page: Page) -> Dict[str, Any]
    """Execute action and return structured result"""

# Result structure:
{
    "status": "success|failed|completed",
    "action": str,
    "selector": str or None,
    "details": str,
    "timestamp": ISO timestamp,
    "duration_ms": float
}
```

**Safety Features:**
- Timeouts on all operations
- Retry logic for clicks
- Visibility checks
- Error handling

**Loop Detection:**
```python
def detect_action_loop(window_size: int = 5) -> bool
    """Check if repeating same actions"""
```

---

### 7. BrowserController (browser_controller.py)

**Role:** Playwright wrapper for browser automation

**Initialization:**
```python
browser = BrowserController(
    headless=True,      # Run without UI
    timeout_ms=30000    # 30 second timeout
)
```

**Key Methods:**
```python
async def start() -> None
    """Launch browser"""

async def stop() -> None
    """Close browser"""

async def open_url(url: str) -> str
    """Navigate to URL"""

async def search(query: str, search_engine="google") -> str
    """Perform search"""

async def click(selector: str) -> str
    """Click element"""

async def scroll(direction: str = "down", amount: int = 3) -> str
    """Scroll page"""

async def extract_text(selector: Optional[str] = None) -> str
    """Get text content"""

async def fill_input(selector: str, value: str) -> str
    """Fill input field"""

async def wait(duration_ms: int) -> str
    """Wait for duration"""

async def navigate_back() -> str
    """Go back"""

async def get_current_url() -> str
    """Get current URL"""

async def get_title() -> str
    """Get page title"""
```

---

### 8. PageAnalyzer (page_analyzer.py)

**Role:** Extract structured information from Playwright page

**Output Structure:**
```python
{
    "url": "https://example.com",
    "title": "Example Page",
    "main_text_summary": "First 800 chars of visible text...",
    "headings": ["Heading 1", "Heading 2", ...],
    "links": [
        {"text": "Link text", "selector": "#link-id"},
        ...
    ],
    "buttons": [
        {"text": "Button text", "selector": ".btn-class"},
        ...
    ],
    "inputs": [
        {
            "placeholder": "Enter email",
            "name": "email",
            "type": "email",
            "selector": "input[name='email']"
        },
        ...
    ],
    "analysis_timestamp": "2026-02-26T10:30:45"
}
```

**Key Methods:**
```python
async def analyze_page() -> Dict[str, Any]
    """Main analysis method"""

async def _extract_text_content(page) -> str
    """Get visible text"""

async def _extract_headings(page) -> List[str]
    """Get h1, h2, h3 texts"""

async def _extract_links(page) -> List[Dict]
    """Get clickable links"""

async def _extract_buttons(page) -> List[Dict]
    """Get buttons"""

async def _extract_inputs(page) -> List[Dict]
    """Get form inputs"""

async def _is_visible(element) -> bool
    """Check element visibility"""

async def _generate_selector(element) -> str
    """Generate CSS selector"""
```

**Limits (prevent data bloat):**
- MAX_LINKS = 20
- MAX_BUTTONS = 10
- MAX_INPUTS = 10
- TEXT_SUMMARY_LENGTH = 800

---

### 9. LLMClient (llm_client.py)

**Role:** Interface to LM Studio API

**Configuration:**
```python
llm = LLMClient(
    base_url="http://localhost:1234/v1",
    model="mistral-7b-instruct",
    timeout=60
)
```

**Key Methods:**
```python
def generate_response(
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 1024
) -> str
    """Generate LLM response"""

def health_check() -> bool
    """Check if LM Studio is running"""
```

**API Format (OpenAI-compatible):**
```python
POST http://localhost:1234/v1/chat/completions
{
    "model": "mistral-7b-instruct",
    "messages": [
        {"role": "system", "content": "..."},
        {"role": "user", "content": "..."}
    ],
    "temperature": 0.7,
    "max_tokens": 1024
}
```

---

### 10. ChatResponder (chat_responder.py)

**Role:** Generate human-friendly explanations for actions

**Methods:**
```python
async def explain_decision(
    goal: str,
    decision: ActionDecision,
    page_state: Dict[str, Any]
) -> str
    """Explain why action was chosen"""

async def explain_result(
    decision: ActionDecision,
    result: Dict[str, Any]
) -> str
    """Explain what happened"""

async def summarize_task(
    goal: str,
    result: Dict[str, Any],
    history: List[Dict]
) -> str
    """Final task summary"""
```

**Example Outputs:**
- Decision: "I found a button labeled 'Enroll' that matches your goal, so I'm clicking it."
- Result: "The click worked well and the page loaded successfully."
- Summary: "Great news! I successfully completed the task in 5 steps..."

---

### 11. ApprovalManager (approval_manager.py)

**Role:** Human-in-the-loop approval for high-risk actions

**High-Risk Detection:**
- Keywords: "buy", "purchase", "checkout", "submit", "enroll", "delete"
- Selectors: `.checkout`, `.submit`, `.buy-btn`, etc.
- Actions: Form submissions, external navigation

**Approval Levels:**
```python
class ApprovalLevel(Enum):
    NOT_REQUIRED = "not_required"  # Read, scroll, search
    RECOMMENDED = "recommended"    # Moderate risk
    REQUIRED = "required"          # High risk (shopping, etc.)
```

**Key Methods:**
```python
def assess_approval_need(goal: str, plan: ActionPlan) -> ApprovalLevel
    """Determine if approval needed"""

async def request_approval(goal: str, plan: ActionPlan) -> ApprovalRequest
    """Generate approval request"""

def parse_user_response(response: str) -> Optional[bool]
    """Parse yes/no response"""
```

---

## DATA MODELS & SCHEMAS

### Core Models (models/schemas.py)

#### IntentType
```python
class IntentType(str, Enum):
    CHAT = "chat"
    AUTOMATION = "automation"
```

#### ActionType
```python
class ActionType(str, Enum):
    OPEN_URL = "open_url"
    SEARCH = "search"
    CLICK = "click"
    SCROLL = "scroll"
    EXTRACT_TEXT = "extract_text"
    WAIT = "wait"
    FILL_INPUT = "fill_input"
    NAVIGATE_BACK = "navigate_back"
```

#### ActionStep
```python
class ActionStep(BaseModel):
    action: ActionType
    value: Optional[str] = None
    selector: Optional[str] = None
    duration_ms: Optional[int] = None
    description: Optional[str] = None
```

#### ActionPlan
```python
class ActionPlan(BaseModel):
    steps: List[ActionStep]
    reasoning: Optional[str] = None
```

#### MessageRequest
```python
class MessageRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
```

#### MessageResponse
```python
class MessageResponse(BaseModel):
    response: str
    intent: IntentType
    plan: Optional[ActionPlan] = None
    session_id: Optional[str] = None
```

#### ActionDecision (planner.py)
```python
@dataclass
class ActionDecision:
    thought: str
    action: str
    target_selector: Optional[str]
    input_text: Optional[str]
    confidence: float
    explanation: str
    timestamp: str
```

#### GoalCompletionReport (agent_controller.py)
```python
@dataclass
class GoalCompletionReport:
    goal: str
    completed: bool
    iterations: int
    final_state: Dict[str, Any]
    actions_taken: List[str]
    reason: str
```

---

## API ENDPOINTS

### Main Endpoints

#### POST /agent/message
Send message to agent and get response.

**Request:**
```json
{
  "message": "Search for Python tutorials",
  "session_id": "optional-uuid"
}
```

**Response:**
```json
{
  "reply": "I will perform these steps: 1. Open Google...",
  "session_id": "uuid",
  "mode": "controlled_automation"
}
```

#### POST /agent/message/stream
Streaming variant using Server-Sent Events.

**Response (SSE):**
```
data: {"type": "status", "content": "Processing..."}
data: {"type": "response", "content": "Done!", "is_final": true}
```

#### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "llm_available": true,
  "orchestrator_ready": true
}
```

### Session Management

#### GET /agent/history?session_id={id}
Get conversation history.

**Response:**
```json
{
  "session_id": "uuid",
  "history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "count": 4
}
```

#### GET /agent/session?session_id={id}
Get session information.

**Response:**
```json
{
  "session_id": "uuid",
  "current_mode": "chat",
  "conversation_turns": 5,
  "pending_approval": false,
  "timestamp": "2026-02-26T10:30:45"
}
```

#### POST /agent/reset
Reset session state.

**Request:**
```json
{"session_id": "uuid"}
```

**Response:**
```json
{
  "status": "success",
  "session_id": "uuid",
  "message": "Session state cleared."
}
```

### Browser Control

#### POST /browser/start
Manually start browser.

#### POST /browser/stop
Manually stop browser.

---

## WORKFLOWS & USE CASES

### Workflow 1: Chat Conversation

```
1. User: "What is machine learning?"
   ↓
2. Orchestrator.handle_message()
   ↓
3. detect_intent() → CHAT
   ↓
4. _handle_chat_mode()
   ↓
5. llm_client.generate_response()
   ↓
6. Return: "Machine learning is a field of AI..."
```

### Workflow 2: Controlled Automation (with Approval)

```
1. User: "Search for Python tutorials"
   ↓
2. Orchestrator.handle_message()
   ↓
3. detect_intent() → CONTROLLED_AUTOMATION
   ↓
4. _handle_controlled_automation_mode()
   ↓
5. planner.generate_plan()
   ↓
6. Return: "I will: 1. Open Google, 2. Search, 3. Click. Proceed?"
   ↓
7. User: "yes"
   ↓
8. Orchestrator.handle_approval()
   ↓
9. executor.execute(plan)
   ↓
10. Return: "✅ All 3 steps completed!"
```

### Workflow 3: Autonomous Goal Execution

```
1. User: "Find the best free Python course"
   ↓
2. Orchestrator.handle_message()
   ↓
3. detect_intent() → AUTONOMOUS_GOAL
   ↓
4. _handle_autonomous_goal_mode()
   ↓
5. autonomous_controller.run_goal()
   
   === LOOP STARTS (max 20 iterations) ===
   
   Iteration 1:
   - _observe_page() → {url, title, text}
   - HybridPlanner.replan_next_action()
     → Decision: search "best free Python course"
   - action_executor.execute()
     → Status: success
   - Record in execution_history
   
   Iteration 2:
   - _observe_page() → {url, title, text}
   - Check if goal complete? → No
   - HybridPlanner.replan_next_action()
     → Decision: click first result
   - action_executor.execute()
     → Status: success
   - Record in execution_history
   
   Iteration 3:
   - _observe_page() → {url, title, text}
   - Check if goal complete? → No
   - HybridPlanner.replan_next_action()
     → Decision: read page content
   - action_executor.execute()
     → Status: success
   - Record in execution_history
   
   Iteration 4:
   - _observe_page() → {url with course info}
   - Check if goal complete? → YES
   - Return success report
   
   === LOOP ENDS ===
   
6. Return report:
   {
     "goal": "Find the best free Python course",
     "completed": true,
     "iterations": 4,
     "final_state": {...},
     "actions_taken": ["search", "click", "read"],
     "summary": "Successfully found best free Python courses..."
   }
```

### Workflow 4: Re-planning on Failure

```
Iteration N:
- action_executor.execute(decision)
  → Result: failed (selector not found)
- Store in failure_history:
  {
    "step": N,
    "decision": {...},
    "execution": {"status": "failed", "details": "Selector not found"}
  }
  
Iteration N+1:
- HybridPlanner.replan_next_action(
    history=execution_history,  # All actions
    failures=failure_history     # Failed actions only
  )
- Planner sees failed selector in failures
- Decides alternative action (e.g., scroll to find element)
- Execute alternative
```

---

## CONFIGURATION

### Environment Variables (.env)

```bash
# LLM Configuration
LLM_BASE_URL=http://localhost:1234/v1
LLM_MODEL=mistral-7b-instruct
LLM_TIMEOUT=60
LLM_TEMPERATURE=0.7

# Browser Configuration
BROWSER_HEADLESS=true
BROWSER_TIMEOUT_MS=30000
BROWSER_AUTO_RETRY=true

# API Server
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=false

# Logging
LOG_LEVEL=INFO
LOG_DIR=logs

# Session
SESSION_TIMEOUT_MINUTES=30
```

### Configuration Class (config.py)

```python
class Settings(BaseSettings):
    # Server
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = False
    
    # LLM
    LLM_BASE_URL: str = "http://localhost:1234/v1"
    LLM_MODEL: str = "mistral-7b-instruct"
    LLM_TIMEOUT: int = 60
    LLM_TEMPERATURE: float = 0.7
    
    # Browser
    BROWSER_HEADLESS: bool = True
    BROWSER_TIMEOUT_MS: int = 30000
    BROWSER_AUTO_RETRY: bool = True
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"
    
    # Session
    SESSION_TIMEOUT_MINUTES: int = 30
```

### Constants

```python
# autonomous_controller.py
DEFAULT_MAX_STEPS = 20
STEP_DELAY = 1.0  # seconds
LOOP_DETECTION_WINDOW = 5

# action_executor.py
ACTION_TIMEOUT = 5.0  # seconds
CLICK_RETRY_ATTEMPTS = 2
SCROLL_AMOUNT = 3

# page_analyzer.py
MAX_LINKS = 20
MAX_BUTTONS = 10
MAX_INPUTS = 10
TEXT_SUMMARY_LENGTH = 800

# llm_planner.py
LLM_TIMEOUT = 15.0
DEFAULT_TEMPERATURE = 0.2

# orchestrator.py
MAX_ITERATIONS = 10
MAX_DUPLICATE_ACTIONS = 2
MEMORY_WINDOW_SIZE = 20
```

---

## INSTALLATION & SETUP

### Prerequisites

1. **Python 3.9+**
2. **LM Studio** (for LLM functionality)
3. **Playwright** (for browser automation)

### Step-by-Step Installation

#### 1. Clone/Navigate to Project
```bash
cd "c:\Users\sandh\OneDrive\Desktop\Autonomous agent\general-agent\backend"
```

#### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

**Dependencies:**
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
requests==2.31.0
playwright==1.40.0
python-multipart==0.0.6
```

#### 3. Install Playwright Browsers
```bash
playwright install chromium
```

#### 4. Setup LM Studio

1. Download from https://lmstudio.ai
2. Install and launch
3. Download a model (e.g., "Mistral 7B Instruct")
4. Start local server:
   - Click "Local Server" tab
   - Click "Start Server"
   - Verify it's running on http://localhost:1234

**Test LM Studio:**
```bash
curl http://localhost:1234/v1/models
```

#### 5. Create Logs Directory
```bash
mkdir logs
```

#### 6. Start the Server
```bash
python api_server.py
```

**Expected Output:**
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

#### 7. Verify Installation

**Health Check:**
```bash
curl http://localhost:8000/health
```

**Test Chat:**
```bash
curl -X POST http://localhost:8000/agent/message \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!"}'
```

---

## TESTING

### Unit Tests

**Example Test (test_autonomous_agent.py):**
```python
import pytest
from autonomous_controller import AutonomousAgentController

@pytest.mark.asyncio
async def test_autonomous_controller_initialization():
    controller = AutonomousAgentController(
        page=mock_page,
        mode="deterministic"
    )
    assert controller.mode == "deterministic"
    assert controller.planner is not None

@pytest.mark.asyncio
async def test_observe_page():
    controller = AutonomousAgentController(page=mock_page)
    observation = await controller._observe_page()
    
    assert "url" in observation
    assert "title" in observation
    assert "main_text_summary" in observation
```

### Manual Testing

**Test Chat Mode:**
```bash
curl -X POST http://localhost:8000/agent/message \
  -d '{"message": "What is Python?"}'
```

**Test Automation Mode:**
```bash
# Request
curl -X POST http://localhost:8000/agent/message \
  -d '{"message": "Search for machine learning tutorials", "session_id": "test1"}'

# Approve
curl -X POST http://localhost:8000/agent/message \
  -d '{"message": "yes", "session_id": "test1"}'
```

**Test Autonomous Mode:**
```bash
curl -X POST http://localhost:8000/agent/message \
  -d '{"message": "Find the best free React course"}'
```

### Integration Tests

Run example scripts:
```bash
python examples.py --programmatic
python examples.py --api
python examples.py --stream
```

---

## DEPENDENCIES

### Python Packages (requirements.txt)

```
fastapi==0.104.1          # Web framework
uvicorn[standard]==0.24.0 # ASGI server
pydantic==2.5.0           # Data validation
pydantic-settings==2.1.0  # Settings management
requests==2.31.0          # HTTP client
playwright==1.40.0        # Browser automation
python-multipart==0.0.6   # Form data parsing
```

### External Services

- **LM Studio** (http://localhost:1234) - Local LLM server
  - Compatible with any OpenAI-compatible API
  - Models: Mistral 7B, LLaMA 2, etc.

- **Chromium Browser** (via Playwright)
  - Installed with `playwright install chromium`

### System Requirements

- **OS:** Windows, macOS, Linux
- **RAM:** 4GB minimum, 8GB+ recommended (for LLM)
- **Disk:** 10GB (for LLM models)
- **Network:** Internet connection for browser automation

---

## CODE EXAMPLES

### Example 1: Direct Python Usage

```python
import asyncio
from llm_client import LLMClient
from planner import Planner
from executor import Executor
from browser_controller import BrowserController
from agent_core import AutomationAgent

async def main():
    # Initialize components
    llm = LLMClient()
    browser = BrowserController(headless=False)
    planner = Planner(llm)
    executor = Executor(browser)
    
    # Create agent
    agent = AutomationAgent(
        planner=planner,
        executor=executor,
        llm_client=llm
    )
    
    # Start browser
    await browser.start()
    
    # Chat
    response = await agent.handle_message("What is Python?")
    print(response)
    
    # Automation request
    response = await agent.handle_message("Search for Docker tutorials")
    print(response)  # Shows plan + approval request
    
    # Approve
    response = await agent.handle_message("yes")
    print(response)  # Shows execution result
    
    # Cleanup
    await browser.stop()

asyncio.run(main())
```

### Example 2: Autonomous Goal Execution

```python
from autonomous_controller import AutonomousAgentController
from page_analyzer import PageAnalyzer
from action_executor import ActionExecutor
from playwright.async_api import async_playwright

async def run_autonomous_goal():
    # Setup
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    page = await browser.new_page()
    
    # Create controller
    controller = AutonomousAgentController(
        page=page,
        analyzer=PageAnalyzer(page),
        executor=ActionExecutor(),
        mode="deterministic"  # or "llm"
    )
    
    # Run goal
    goal = "Find the top 3 free Python courses"
    result = await controller.run_goal(goal, max_steps=15)
    
    # Print result
    print(f"Goal: {result['goal']}")
    print(f"Status: {result['final_status']}")
    print(f"Steps: {result['steps_taken']}")
    print(f"Summary: {result['summary']}")
    
    # Cleanup
    await browser.close()

asyncio.run(run_autonomous_goal())
```

### Example 3: REST API Usage (JavaScript)

```javascript
// Send message
async function sendMessage(message, sessionId = null) {
  const response = await fetch('http://localhost:8000/agent/message', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message: message,
      session_id: sessionId
    })
  });
  
  const data = await response.json();
  return data;
}

// Chat mode
const chatResponse = await sendMessage("What is FastAPI?");
console.log(chatResponse.reply);

// Automation mode
const sessionId = "my-session-123";
const automationRequest = await sendMessage(
  "Search for Python tutorials",
  sessionId
);
console.log(automationRequest.reply);  // Plan + approval request

// Approve
const approvalResponse = await sendMessage("yes", sessionId);
console.log(approvalResponse.reply);  // Execution result
```

### Example 4: Streaming Response (JavaScript)

```javascript
async function streamMessage(message) {
  const response = await fetch('http://localhost:8000/agent/message/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message })
  });
  
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    
    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');
    
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));
        console.log(`[${data.type}] ${data.content}`);
        
        if (data.is_final) {
          return data.content;
        }
      }
    }
  }
}

// Usage
await streamMessage("Find best Python course");
// Output:
// [status] Processing your request...
// [status] Analyzing page...
// [progress] Step 1: Opening Google...
// [response] ✅ Found best Python courses!
```

---

## TROUBLESHOOTING

### Common Issues

#### 1. LLM Not Responding

**Error:**
```
Failed to connect to LM Studio at http://localhost:1234
```

**Solutions:**
- Check LM Studio is running: `curl http://localhost:1234/v1/models`
- Verify API server is enabled in LM Studio settings
- Try restarting LM Studio
- Check firewall settings

#### 2. Browser Automation Timeout

**Error:**
```
Timeout opening URL: https://example.com
```

**Solutions:**
```python
# Increase timeout
browser = BrowserController(timeout_ms=60000)

# Or check internet connection
ping example.com
```

#### 3. Playwright Not Installed

**Error:**
```
Executable doesn't exist at /path/to/chromium
```

**Solution:**
```bash
playwright install chromium
```

#### 4. Module Import Errors

**Error:**
```
ModuleNotFoundError: No module named 'fastapi'
```

**Solution:**
```bash
pip install -r requirements.txt
```

#### 5. Session Not Found

**Error:**
```
{"detail": "Session not found"}
```

**Cause:** Session expired or invalid session_id

**Solution:**
- Don't include `session_id` in first request
- System will auto-generate and return it

#### 6. Agent Stuck in Loop

**Symptoms:** Agent repeats same action multiple times

**Solutions:**
- Loop detection should catch this automatically
- Check `LOOP_DETECTION_WINDOW` setting
- Increase `max_steps` if task is complex
- Make goal more specific

#### 7. Invalid Action from LLM

**Error:**
```
Invalid action from LLM: unknown_action
```

**Cause:** LLM generated unsupported action

**Solution:** System falls back to safe scroll action automatically

#### 8. Port Already in Use

**Error:**
```
OSError: [Errno 48] Address already in use
```

**Solution:**
```bash
# Find process using port 8000
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill the process or use different port
uvicorn api_server:app --port 8001
```

---

## FUTURE ENHANCEMENTS

### Planned Features

1. **Multi-Browser Support**
   - Firefox, Safari, Edge
   - Mobile browser simulation

2. **Advanced Element Selection**
   - ML-based element identification
   - Visual element selection (screenshots)

3. **Workflow Persistence**
   - Save/load automation workflows
   - Template library
   - Workflow replay

4. **Enhanced Safety**
   - Sandbox mode for testing
   - Rollback on errors
   - Preview mode (show what would happen)

5. **Performance Optimization**
   - Parallel execution for independent actions
   - Browser instance pooling
   - Caching for repeated operations

6. **Extended Integrations**
   - Database storage (PostgreSQL)
   - Cloud deployment (AWS, Azure, GCP)
   - Webhook notifications
   - Third-party API integrations

7. **Analytics & Monitoring**
   - Execution metrics dashboard
   - Success/failure analytics
   - Performance tracking
   - Cost optimization insights

8. **User Interface**
   - Web UI (React/Vue)
   - Workflow builder (drag-and-drop)
   - Real-time execution visualization
   - Mobile app

9. **Advanced AI Features**
   - Multi-modal understanding (images, videos)
   - Natural language plan refinement
   - Adaptive learning from failures
   - Context-aware suggestions

10. **Enterprise Features**
    - Multi-tenancy
    - Role-based access control
    - Audit logs
    - Compliance reporting

---

## SUMMARY FOR CHATGPT

### What ChatGPT Should Know

1. **This is a production-ready autonomous browser automation system** with three modes:
   - Chat (conversational AI)
   - Controlled automation (with human approval)
   - Autonomous goal execution (self-guided)

2. **Key Components:**
   - **AgentOrchestrator** - Routes user messages
   - **AutonomousAgentController** - Autonomous reasoning loop
   - **AutomationAgent** - Controlled automation with approval
   - **Planner/HybridPlanner/LLMPlanner** - Decision making
   - **ActionExecutor** - Executes actions
   - **BrowserController** - Playwright wrapper
   - **PageAnalyzer** - Extracts page state

3. **Architecture Principles:**
   - Async/await throughout
   - Type safety (Pydantic, type hints)
   - Comprehensive error handling
   - Structured logging
   - Safety constraints (loop detection, approvals)

4. **Technologies:**
   - FastAPI (REST API)
   - Playwright (browser automation)
   - LM Studio (local LLM)
   - Pydantic (data validation)
   - Python asyncio (concurrency)

5. **When helping users:**
   - Understand the three operation modes
   - Know the difference between Planner, HybridPlanner, LLMPlanner
   - Be aware of the autonomous observe→reason→act loop
   - Understand human-in-the-loop approval workflow
   - Reference specific files and line numbers when possible

6. **Common User Questions:**
   - How to add new browser actions?
     → Extend BrowserController and ActionExecutor
   - How to customize intent detection?
     → Modify AgentOrchestrator.detect_intent()
   - How to change LLM behavior?
     → Adjust temperature, prompts in LLMClient
   - How to add safety checks?
     → Update ApprovalManager or add to AutonomousAgentController

---

**END OF DOCUMENTATION**

This document contains everything needed to understand, maintain, and extend this project. All code, architecture, workflows, and configurations have been documented comprehensively.
