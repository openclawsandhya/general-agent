# COMPREHENSIVE PROJECT DOCUMENTATION
# SANDHYA.AI - Autonomous Browser Automation Agent

**Version:** 2.0.0  
**Last Updated:** February 26, 2026  
**Project Type:** Production-Ready AI Agent with Browser Automation  

---

## 📑 TABLE OF CONTENTS

1. [Executive Summary](#executive-summary)
2. [System Architecture](#system-architecture)
3. [Backend Components](#backend-components)
4. [Frontend Components](#frontend-components)
5. [Data Models & Schemas](#data-models--schemas)
6. [API Endpoints](#api-endpoints)
7. [Configuration & Setup](#configuration--setup)
8. [Project Structure](#project-structure)
9. [Dependencies](#dependencies)
10. [Workflows & Use Cases](#workflows--use-cases)
11. [Testing & Debugging](#testing--debugging)
12. [Security & Best Practices](#security--best-practices)

---

## 1. EXECUTIVE SUMMARY

### 1.1 What is SANDHYA.AI?

SANDHYA.AI is a **production-grade autonomous browser automation agent** that combines:
- 🤖 **Local LLM Integration** (via LM Studio)
- 🌐 **Browser Automation** (via Playwright)
- 🧠 **Autonomous Goal Execution** (LLM-driven reasoning loops)
- ✅ **Human-in-the-Loop Approval** (controlled automation)
- 💬 **Natural Language Interface** (conversational AI)

### 1.2 Key Capabilities

#### Three Operation Modes:

1. **Chat Mode** 
   - Natural language conversation
   - Q&A, explanations, code generation
   - Context-aware responses using local LLM

2. **Controlled Automation Mode**
   - Human-approved browser automation
   - Step-by-step task execution
   - Plan generation → approval → execution workflow

3. **Autonomous Goal Mode**
   - Fully autonomous task completion
   - Continuous observe → decide → act loop
   - Intelligent re-planning on failures
   - Safety constraints (loop detection, max iterations)

### 1.3 Technology Stack

**Backend:**
- FastAPI (REST API server)
- Playwright (browser automation)
- LM Studio API (local LLM inference)
- Pydantic (data validation)
- Asyncio (async/await concurrency)

**Frontend:**
- React 18.3 + TypeScript
- Vite (build tool)
- Tailwind CSS (styling)
- shadcn/ui (component library)
- TanStack Query (data fetching)
- React Router v6 (routing)

### 1.4 Business Value

- ✅ Automates repetitive web tasks (search, extraction, form filling)
- ✅ Provides conversational interface for complex automation
- ✅ Ensures safety with human approval workflow
- ✅ Adapts dynamically to changing page states
- ✅ Scalable via REST API for multi-user support
- ✅ Runs 100% locally (privacy-first, no cloud dependencies)

---

## 2. SYSTEM ARCHITECTURE

### 2.1 High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     FRONTEND (React + TypeScript)               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Components: Chat, Sidebar, Telemetry, Settings          │  │
│  │  Pages: Index (main chat interface)                      │  │
│  │  State: React hooks, TanStack Query                      │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP/REST API
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  BACKEND (FastAPI + Python)                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              API Server (api_server.py)                  │  │
│  │  • /agent/message - Unified message endpoint             │  │
│  │  • /health - Health check                                │  │
│  │  • Session management                                    │  │
│  └────────────────────┬─────────────────────────────────────┘  │
│                       │                                         │
│  ┌────────────────────▼─────────────────────────────────────┐  │
│  │         AgentOrchestrator (orchestrator.py)              │  │
│  │  • Intent Detection (chat/controlled/autonomous)         │  │
│  │  • Conversation Context Management                       │  │
│  │  • Approval Workflow Coordination                        │  │
│  │  • Execution Safety Enforcement                          │  │
│  └─────┬──────────────┬──────────────┬─────────────────────┘  │
│        │              │              │                         │
│        ▼              ▼              ▼                         │
│  ┌─────────┐  ┌──────────────┐  ┌──────────────────────┐     │
│  │  Chat   │  │ Controlled   │  │   Autonomous         │     │
│  │  Mode   │  │ Automation   │  │   Goal Mode          │     │
│  └────┬────┘  └──────┬───────┘  └──────┬───────────────┘     │
│       │              │                  │                      │
│       │      ┌───────▼──────────────────▼────────┐            │
│       │      │    Planner (planner.py)           │            │
│       │      │  • Multi-step plan generation     │            │
│       │      │  • LLM-driven decision making     │            │
│       │      └───────┬────────────────────────────┘            │
│       │              │                                         │
│       │      ┌───────▼────────────────────────────┐           │
│       │      │   Executor (executor.py)           │           │
│       │      │  • Sequential action execution     │           │
│       │      │  • Retry logic                     │           │
│       │      └───────┬────────────────────────────┘           │
│       │              │                                         │
│       ▼      ┌───────▼────────────────────────────┐           │
│  ┌──────────────────────────────────────────────┐ │           │
│  │     LLM Client (llm_client.py)               │ │           │
│  │  • LM Studio API integration                 │ │           │
│  │  • OpenAI-compatible API client              │ │           │
│  │  • Health checks                             │ │           │
│  └──────────────────────────────────────────────┘ │           │
│                                                    │           │
│  ┌────────────────────────────────────────────────▼─────────┐ │
│  │       BrowserController (browser_controller.py)          │ │
│  │  • Playwright browser management                         │ │
│  │  • Action primitives (click, type, scroll, navigate)     │ │
│  └──────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              EXTERNAL DEPENDENCIES                              │
│  • LM Studio (http://localhost:1234) - Local LLM inference     │
│  • Chromium Browser (via Playwright) - Browser automation      │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Core Design Principles

1. **Separation of Concerns**
   - API layer (FastAPI) ← Business logic (Orchestrator) ← Execution (Planner/Executor)
   - Each component has single responsibility

2. **Intent-Based Routing**
   - Automatic detection of user intent (chat vs automation vs autonomous)
   - No user-selected modes - system decides based on message content

3. **Safety First**
   - Human approval required for controlled automation
   - Max iterations limit (10 steps) for autonomous mode
   - Loop detection and drift detection
   - Error handling at every layer

4. **Stateful Sessions**
   - Per-session orchestrators maintain conversation context
   - Session-based browser instances
   - History tracking for intelligent re-planning

5. **Async/Await Architecture**
   - Non-blocking I/O for browser operations
   - Concurrent LLM calls and page analysis
   - Streaming responses for real-time feedback

---

## 3. BACKEND COMPONENTS

### 3.1 API Server (`api_server.py`)

**Purpose:** FastAPI server exposing REST endpoints for frontend communication.

**Key Features:**
- CORS middleware for frontend integration
- Session management (per-session orchestrators)
- Startup/shutdown lifecycle management
- Health checks for LLM and browser

**Endpoints:**

```python
POST /agent/message
Request: { "message": str, "session_id": str? }
Response: { "reply": str, "session_id": str, "mode": str? }
Description: Main unified message endpoint - routes to chat/automation/autonomous

GET /health
Response: { "status": str, "llm_available": bool, "orchestrator_ready": bool }
Description: Health check for all system components
```

**Startup Flow:**
1. Initialize LLM client (http://localhost:1234/v1)
2. Initialize browser controller (headless Chromium)
3. Initialize planner (LLM-based plan generation)
4. Initialize executor (action execution)
5. Initialize autonomous controller (reasoning loop)
6. Store in `app.state` for global access

**Session Management:**
- Creates per-session `AgentOrchestrator` instances
- Maintains session-specific conversation history
- Stores in `orchestrators: dict` keyed by `session_id`

---

### 3.2 Orchestrator (`orchestrator.py`)

**Purpose:** Central control engine that routes messages to appropriate execution modes.

**Core Responsibilities:**
1. **Intent Detection** - Classify message as chat/controlled/autonomous
2. **Conversation Management** - Maintain context and history
3. **Approval Workflow** - Coordinate human approval for plans
4. **Safety Enforcement** - Loop detection, drift detection, max iterations
5. **Status Updates** - Conversational feedback during execution

**Intent Detection Logic:**

```python
def detect_intent(message: str) -> IntentMode:
    # Check for autonomous keywords ("find best", "research", "explore")
    if any(keyword in message for keyword in AUTONOMOUS_KEYWORDS):
        return IntentMode.AUTONOMOUS_GOAL
    
    # Check for automation keywords ("open", "search", "click")
    if any(keyword in message for keyword in AUTOMATION_KEYWORDS):
        return IntentMode.CONTROLLED_AUTOMATION
    
    # Default to chat
    return IntentMode.CHAT
```

**Execution Flow:**

```
User Message
    ↓
detect_intent()
    ↓
┌───────────────────┬───────────────────┬──────────────────┐
│ Chat Mode         │ Controlled Mode   │ Autonomous Mode  │
├───────────────────┼───────────────────┼──────────────────┤
│ handle_chat()     │ handle_controlled│ handle_autonomous│
│   ↓               │   ↓               │   ↓              │
│ LLM response      │ generate_plan()   │ run_goal_loop()  │
│                   │   ↓               │   ↓              │
│                   │ await_approval()  │ observe→decide   │
│                   │   ↓               │   ↓              │
│                   │ execute_plan()    │ act→repeat       │
└───────────────────┴───────────────────┴──────────────────┘
```

**Safety Constraints:**

```python
MAX_ITERATIONS = 10  # Max steps in autonomous mode
MAX_DUPLICATE_ACTIONS = 2  # Max times to repeat same action
NAVIGATION_DRIFT_THRESHOLD = 3  # Max navigation attempts before abort
MEMORY_WINDOW_SIZE = 20  # Steps tracked for loop detection
```

---

### 3.3 Autonomous Controller (`autonomous_controller.py`)

**Purpose:** Implements the observe → decide → act loop for autonomous goal completion.

**Architecture:**

```
┌──────────────────────────────────────────────────────────┐
│         AutonomousAgentController                        │
├──────────────────────────────────────────────────────────┤
│  Components:                                             │
│  • PageAnalyzer - Observes current page state           │
│  • HybridPlanner - Decides next action (rules + LLM)    │
│  • ActionExecutor - Executes actions against page       │
│  • LLMClient - Fallback planning                        │
├──────────────────────────────────────────────────────────┤
│  State:                                                  │
│  • _execution_history: List[ActionDecision]            │
│  • _failure_history: List[FailedAction]                │
│  • _conversation_history: List[Message]                │
│  • _scroll_count: int (loop detection)                  │
│  • _no_progress_counter: int (stagnation detection)     │
└──────────────────────────────────────────────────────────┘
```

**Main Loop (`run_goal`):**

```python
async def run_goal(user_goal: str, max_steps: int = 20):
    for step_num in range(max_steps):
        # 1. OBSERVE: Analyze current page
        observation = await self.analyzer.analyze_page()
        
        # 2. CHECK COMPLETION: Is goal achieved?
        if await self._is_goal_complete(goal, observation):
            return success_report
        
        # 3. DETECT LOOPS: Check for repetitive behavior
        if self._is_repetitive_loop(observation):
            return loop_detected_report
        
        # 4. DECIDE: Get next action from planner
        decision = await self.planner.replan_next_action(
            goal=user_goal,
            page_state=observation,
            history=self._execution_history,
            failures=self._failure_history
        )
        
        # 5. ACT: Execute the action
        result = await self.executor.execute(decision, self.page)
        
        # 6. RECORD: Track execution for re-planning
        self._execution_history.append({
            "step": step_num,
            "decision": decision,
            "result": result,
            "timestamp": datetime.now()
        })
        
        if result["status"] == "failed":
            self._failure_history.append(...)
        
        await asyncio.sleep(STEP_DELAY)
    
    return max_steps_reached_report
```

**Intelligent Re-Planning:**
- Passes entire `execution_history` and `failure_history` to planner on each step
- Planner uses history to avoid repeating failed actions
- Enables learning from mistakes and alternative approaches

**Safety Features:**
1. **Loop Detection** - Detects repetitive actions (e.g., scrolling 5 times without progress)
2. **Stagnation Detection** - Tracks steps without progress toward goal
3. **Failure Rate Tracking** - Monitors success/failure ratio
4. **Max Iterations** - Hard limit to prevent infinite loops

---

### 3.4 Planner (`planner.py`)

**Purpose:** Converts user goals into structured action plans.

**Two Planner Types:**

#### 3.4.1 Planner (Multi-Step Planning)

Generates complete action plans for controlled automation:

```python
class Planner:
    def generate_plan(request: str) -> ActionPlan:
        # Prompt LLM to generate JSON plan
        # Returns: ActionPlan with List[ActionStep]
```

**Example Plan:**
```json
{
  "steps": [
    {"action": "open_url", "value": "https://google.com"},
    {"action": "search", "value": "Python tutorials"},
    {"action": "click", "selector": "a.result:first-child"},
    {"action": "extract_text", "selector": ".content"}
  ],
  "reasoning": "Search for Python tutorials and extract content"
}
```

#### 3.4.2 HybridPlanner (Autonomous Decision Making)

Decides single next action based on current state:

```python
class HybridPlanner:
    def replan_next_action(
        goal: str,
        page_state: Dict,
        history: List[Dict],
        failures: List[Dict]
    ) -> ActionDecision:
        # 1. Try deterministic rules first
        # 2. Fallback to LLM if rules don't match
        # 3. Return ActionDecision
```

**Decision Process:**
1. **Deterministic Rules** (fast, reliable)
   - If URL contains "search" → look for search box
   - If inputs visible → fill relevant inputs
   - If buttons match goal keywords → click button

2. **LLM Fallback** (intelligent, flexible)
   - Prompt LLM with goal, page state, history
   - Parse JSON response into ActionDecision

**ActionDecision Structure:**
```python
@dataclass
class ActionDecision:
    thought: str  # Reasoning
    action: str  # click, type, scroll, wait, navigate, finish
    target_selector: Optional[str]  # CSS selector
    input_text: Optional[str]  # Text for type action
    confidence: float  # 0.0-1.0
    explanation: str  # Why this action
    timestamp: str  # ISO timestamp
```

---

### 3.5 Action Executor (`action_executor.py`)

**Purpose:** Executes ActionDecision objects against live browser page.

**Supported Actions:**
- `click` - Click element by selector
- `type` - Type text into input field
- `read` - Extract text from page
- `scroll` - Scroll up/down
- `wait` - Wait for duration
- `navigate` - Navigate to URL
- `finish` - Mark goal complete

**Execution Features:**
1. **Retry Logic** - 2 attempts per action
2. **Fallback Strategies** - Multiple selector strategies for clicks
3. **Network Idle Waiting** - Waits for page load after navigation
4. **Timeout Protection** - 5 second timeout per action

**Example Execution:**

```python
async def execute(decision: ActionDecision, page: Page):
    start_time = datetime.now()
    
    # Route to action handler
    if decision.action == "click":
        result = await self._execute_click(decision, page)
    elif decision.action == "type":
        result = await self._execute_type(decision, page)
    # ... other actions
    
    # Return structured result
    return {
        "status": "success|failed|completed",
        "action": decision.action,
        "selector": decision.target_selector,
        "details": "Descriptive message",
        "timestamp": ISO_timestamp,
        "duration_ms": elapsed_time
    }
```

---

### 3.6 Page Analyzer (`page_analyzer.py`)

**Purpose:** Observes current browser page and returns structured data for reasoning.

**Analysis Output:**

```python
{
    "url": "https://example.com/page",
    "title": "Page Title",
    "main_text_summary": "First 800 chars of visible text...",
    "headings": ["Heading 1", "Heading 2", ...],  # h1, h2, h3
    "links": [
        {"text": "Link text", "selector": "a#link-1"},
        ...
    ],  # Max 20 links
    "buttons": [
        {"text": "Button text", "selector": "button.submit"},
        ...
    ],  # Max 10 buttons
    "inputs": [
        {
            "name": "email",
            "type": "text",
            "selector": "input#email",
            "placeholder": "Enter email"
        },
        ...
    ],  # Max 10 inputs
    "analysis_timestamp": "2026-02-26T10:30:00"
}
```

**Key Methods:**

```python
async def analyze_page() -> Dict:
    # Main entry point - returns full page analysis

async def _extract_text_content(page) -> str:
    # Extracts visible text, excludes scripts/styles

async def _extract_links(page) -> List[Dict]:
    # Finds clickable links with meaningful text

async def _extract_buttons(page) -> List[Dict]:
    # Finds buttons and submit inputs

async def _extract_inputs(page) -> List[Dict]:
    # Finds input fields with metadata

async def _is_visible(element) -> bool:
    # Checks if element is actually visible to user
```

---

### 3.7 Browser Controller (`browser_controller.py`)

**Purpose:** Playwright wrapper for browser automation primitives.

**Browser Management:**
```python
async def start():  # Starts Chromium browser
async def stop():   # Closes browser
```

**Action Primitives:**

```python
async def open_url(url: str) -> str
    # Navigates to URL, ensures https://

async def search(query: str, search_engine: str = "google") -> str
    # Performs search on Google/Bing

async def click(selector: str) -> str
    # Clicks element by CSS selector

async def fill_input(selector: str, value: str) -> str
    # Fills input field with text

async def scroll(direction: str = "down", amount: int = 3) -> str
    # Scrolls page up/down

async def extract_text(selector: Optional[str] = None) -> str
    # Extracts visible text from page or element

async def wait(duration_ms: int) -> str
    # Waits for specified duration

async def navigate_back() -> str
    # Goes back in browser history
```

**Configuration:**
- `headless: bool` - Run in headless mode (default: True)
- `timeout_ms: int` - Default timeout for operations (default: 30000)

---

### 3.8 LLM Client (`llm_client.py`)

**Purpose:** Integrates with LM Studio for local LLM inference.

**API Compatibility:**
- OpenAI-compatible API endpoint
- Chat completions format
- No API key required (local server)

**Configuration:**
```python
base_url: str = "http://localhost:1234/v1"
model: str = "mistral-7b-instruct"
timeout: int = 60  # seconds
```

**Main Methods:**

```python
def generate_response(
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 1024
) -> str:
    # Sends chat completion request to LM Studio
    # Returns generated text

def health_check() -> bool:
    # Checks if LM Studio is running
    # Returns True if accessible
```

**Request Format:**
```python
{
    "model": "mistral-7b-instruct",
    "messages": [
        {"role": "system", "content": "System prompt"},
        {"role": "user", "content": "User message"}
    ],
    "temperature": 0.7,
    "max_tokens": 1024,
    "top_p": 0.95
}
```

---

### 3.9 LLM Planner (`llm_planner.py`)

**Purpose:** Pure LLM-based planner for autonomous decision making.

**Alternative to HybridPlanner:**
- HybridPlanner: Deterministic rules + LLM fallback
- LLMPlanner: Pure LLM-based decisions (more flexible, slower)

**Usage:**
```python
planner = LLMPlanner(
    model_name="local-model",
    api_base="http://localhost:1234/v1",
    temperature=0.2  # Lower for determinism
)

decision = await planner.replan_next_action(
    goal="Find Python tutorial",
    page_state=observation,
    history=execution_history,
    failures=failure_history
)
```

**Prompt Engineering:**
- System prompt defines available actions and JSON format
- User prompt includes goal, page state, and recent history
- Returns structured JSON parsed into ActionDecision

---

### 3.10 Executor (`executor.py`)

**Purpose:** Executes multi-step ActionPlan objects sequentially.

**Execution Flow:**
```python
async def execute(plan: ActionPlan) -> str:
    results = []
    
    for step in plan.steps:
        # Send status update
        await self._send_status(f"Executing {step.action}...")
        
        # Execute with retry
        result = await self._execute_step_with_retry(step)
        results.append(result)
    
    return final_summary_message
```

**Features:**
- Sequential execution (one step at a time)
- Retry logic (1 retry per step)
- Status callbacks for real-time updates
- Error aggregation and reporting

**Step Execution:**
```python
async def _execute_step(step: ActionStep) -> str:
    if step.action == ActionType.OPEN_URL:
        return await self.browser.open_url(step.value)
    elif step.action == ActionType.SEARCH:
        return await self.browser.search(step.value)
    elif step.action == ActionType.CLICK:
        return await self.browser.click(step.selector)
    # ... other actions
```

---

### 3.11 Data Models (`models/schemas.py`)

**Purpose:** Pydantic models for request/response validation and data structures.

**Key Models:**

```python
class IntentType(str, Enum):
    CHAT = "chat"
    AUTOMATION = "automation"

class ActionType(str, Enum):
    OPEN_URL = "open_url"
    SEARCH = "search"
    CLICK = "click"
    SCROLL = "scroll"
    EXTRACT_TEXT = "extract_text"
    WAIT = "wait"
    FILL_INPUT = "fill_input"
    NAVIGATE_BACK = "navigate_back"

class ActionStep(BaseModel):
    action: ActionType
    value: Optional[str] = None
    selector: Optional[str] = None
    duration_ms: Optional[int] = None
    description: Optional[str] = None

class ActionPlan(BaseModel):
    steps: List[ActionStep]
    reasoning: Optional[str] = None

class MessageRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class MessageResponse(BaseModel):
    response: str
    intent: IntentType
    plan: Optional[ActionPlan] = None
    session_id: Optional[str] = None

class StreamingMessage(BaseModel):
    type: str  # "status", "response", "progress"
    content: str
    is_final: bool = False
```

---

### 3.12 Configuration (`config.py`)

**Purpose:** Centralized configuration using Pydantic Settings.

**Settings:**

```python
class Settings(BaseSettings):
    # Server
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = False
    
    # LLM Configuration
    LLM_BASE_URL: str = "http://localhost:1234/v1"
    LLM_MODEL: str = "mistral-7b-instruct"
    LLM_TIMEOUT: int = 60
    LLM_TEMPERATURE: float = 0.7
    
    # Browser Configuration
    BROWSER_HEADLESS: bool = True
    BROWSER_TIMEOUT_MS: int = 30000
    BROWSER_AUTO_RETRY: bool = True
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"
    
    # Session
    SESSION_TIMEOUT_MINUTES: int = 30
```

**Environment Variables:**
- Reads from `.env` file if present
- Can be overridden with environment variables

---

### 3.13 Logger (`utils/logger.py`)

**Purpose:** Centralized logging configuration.

**Features:**
- Console handler (INFO level)
- File handler (DEBUG level) → `logs/agent.log`
- Structured log format with timestamps, module names, function names

**Usage:**
```python
from utils.logger import get_logger

logger = get_logger(__name__)
logger.info("Info message")
logger.debug("Debug message")
logger.error("Error message", exc_info=True)
```

---

## 4. FRONTEND COMPONENTS

### 4.1 Application Structure

**Framework:** React 18.3 + TypeScript + Vite

**Directory Structure:**
```
frontend/src/
├── App.tsx                 # Root component with routing
├── main.tsx               # Entry point
├── index.css             # Global styles
├── pages/
│   ├── Index.tsx         # Main chat interface
│   └── NotFound.tsx      # 404 page
├── components/
│   ├── AppHeader.tsx     # Top navigation bar
│   ├── AppSidebar.tsx    # Left sidebar navigation
│   ├── ChatComposer.tsx  # Message input component
│   ├── ChatMessage.tsx   # Message display component
│   ├── ModeSwitcher.tsx  # Mode selection (chat/controlled/autonomous)
│   ├── TelemetryPanel.tsx # Right panel for metrics
│   ├── SettingsModal.tsx  # Settings dialog
│   ├── NavLink.tsx        # Sidebar link component
│   └── ui/               # shadcn/ui components (40+ components)
├── hooks/
│   ├── use-mobile.tsx    # Mobile detection hook
│   └── use-toast.ts      # Toast notification hook
└── lib/
    └── utils.ts          # Utility functions (cn, etc.)
```

### 4.2 App.tsx (Root Component)

**Purpose:** Application root with routing and providers.

```tsx
const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Index />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);
```

**Providers:**
- **QueryClientProvider** - TanStack Query for data fetching
- **TooltipProvider** - Radix UI tooltip context
- **BrowserRouter** - React Router for navigation
- **Toaster/Sonner** - Toast notification systems

---

### 4.3 Index.tsx (Main Chat Interface)

**Purpose:** Primary user interface for agent interaction.

**State Management:**

```tsx
const [messages, setMessages] = useState<ChatMessageData[]>(initialMessages)
const [isLoading, setIsLoading] = useState(false)
const [activeNav, setActiveNav] = useState("chat")
const [mode, setMode] = useState<"chat" | "controlled" | "autonomous">("chat")
const [settingsOpen, setSettingsOpen] = useState(false)
```

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  AppSidebar  │  AppHeader                                   │
│              ├───────────────────────────────────────────────┤
│   • Chat     │                                               │
│   • History  │         Chat Messages                         │
│   • Settings │         (scrollable area)                     │
│              │                                               │
│              │                                               │
│              ├───────────────────────────────────────────────┤
│              │  Mode Switcher (chat/controlled/autonomous)  │
│              ├───────────────────────────────────────────────┤
│              │  Chat Composer (message input)               │
└──────────────┴───────────────────────────────────────────────┘
```

**Message Handling:**

```tsx
const handleSend = (content: string) => {
  // 1. Add user message to state
  const userMsg: ChatMessageData = {
    id: Date.now().toString(),
    role: "user",
    content,
    timestamp: new Date().toLocaleTimeString()
  }
  setMessages(prev => [...prev, userMsg])
  
  // 2. Show loading indicator
  setIsLoading(true)
  
  // 3. Send to backend (simulated in demo)
  // In production: fetch("/agent/message", { method: "POST", body: JSON.stringify({ message: content }) })
  
  // 4. Add assistant response
  setTimeout(() => {
    const assistantMsg: ChatMessageData = { ... }
    setMessages(prev => [...prev, assistantMsg])
    setIsLoading(false)
  }, 1500)
}
```

---

### 4.4 AppHeader.tsx

**Purpose:** Top navigation bar with branding and settings.

**Features:**
- SANDHYA.AI branding
- Settings button
- Responsive design

```tsx
export function AppHeader({ onSettingsClick }: Props) {
  return (
    <header className="border-b px-6 py-4 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <Bot className="h-6 w-6 text-primary" />
        <h1 className="text-xl font-semibold">SANDHYA.AI</h1>
      </div>
      <Button variant="ghost" onClick={onSettingsClick}>
        <Settings className="h-5 w-5" />
      </Button>
    </header>
  )
}
```

---

### 4.5 AppSidebar.tsx

**Purpose:** Left sidebar for navigation.

**Navigation Items:**
- 💬 Chat
- 📜 History
- 🔧 Settings

```tsx
export function AppSidebar({ activeItem, onItemClick, onSettingsClick }: Props) {
  return (
    <aside className="w-64 border-r bg-muted/30 flex flex-col">
      <div className="p-4 border-b">
        <h2 className="font-semibold">Navigation</h2>
      </div>
      <nav className="flex-1 p-4">
        <NavLink
          icon={MessageSquare}
          label="Chat"
          active={activeItem === "chat"}
          onClick={() => onItemClick("chat")}
        />
        <NavLink
          icon={History}
          label="History"
          active={activeItem === "history"}
          onClick={() => onItemClick("history")}
        />
      </nav>
      <div className="p-4 border-t">
        <Button variant="outline" onClick={onSettingsClick}>
          <Settings className="mr-2 h-4 w-4" />
          Settings
        </Button>
      </div>
    </aside>
  )
}
```

---

### 4.6 ChatMessage.tsx

**Purpose:** Displays individual chat messages with markdown support.

**Features:**
- User vs Assistant styling
- Markdown rendering (bold, code blocks, lists)
- Syntax highlighting for code
- Timestamp display

```tsx
export function ChatMessage({ message }: Props) {
  const isUser = message.role === "user"
  
  return (
    <div className={cn(
      "flex gap-3",
      isUser ? "flex-row-reverse" : "flex-row"
    )}>
      {/* Avatar */}
      <Avatar>
        {isUser ? <User /> : <Bot />}
      </Avatar>
      
      {/* Message bubble */}
      <div className={cn(
        "rounded-lg px-4 py-2 max-w-[80%]",
        isUser ? "bg-primary text-primary-foreground" : "bg-muted"
      )}>
        <ReactMarkdown>{message.content}</ReactMarkdown>
        <span className="text-xs opacity-70">{message.timestamp}</span>
      </div>
    </div>
  )
}
```

**TypingIndicator Component:**
```tsx
export function TypingIndicator() {
  return (
    <div className="flex gap-1 items-center">
      <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" />
      <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce delay-100" />
      <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce delay-200" />
    </div>
  )
}
```

---

### 4.7 ChatComposer.tsx

**Purpose:** Message input component with send functionality.

**Features:**
- Textarea with auto-resize
- Send button (Enter to send, Shift+Enter for newline)
- Loading state disables input
- Placeholder text

```tsx
export function ChatComposer({ onSend, isLoading }: Props) {
  const [input, setInput] = useState("")
  
  const handleSend = () => {
    if (!input.trim() || isLoading) return
    onSend(input.trim())
    setInput("")
  }
  
  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }
  
  return (
    <div className="px-6 pb-6">
      <div className="flex gap-2">
        <Textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your message..."
          disabled={isLoading}
          rows={3}
        />
        <Button onClick={handleSend} disabled={isLoading || !input.trim()}>
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}
```

---

### 4.8 ModeSwitcher.tsx

**Purpose:** Toggle between chat/controlled/autonomous modes.

**Modes:**
- 💬 **Chat** - Conversational AI
- 🎯 **Controlled** - Approved automation
- 🤖 **Autonomous** - Full autonomy

```tsx
export function ModeSwitcher({ mode, onChange }: Props) {
  return (
    <div className="flex gap-2 bg-muted rounded-lg p-1">
      <Button
        variant={mode === "chat" ? "default" : "ghost"}
        onClick={() => onChange("chat")}
        size="sm"
      >
        <MessageSquare className="h-4 w-4 mr-2" />
        Chat
      </Button>
      <Button
        variant={mode === "controlled" ? "default" : "ghost"}
        onClick={() => onChange("controlled")}
        size="sm"
      >
        <Target className="h-4 w-4 mr-2" />
        Controlled
      </Button>
      <Button
        variant={mode === "autonomous" ? "default" : "ghost"}
        onClick={() => onChange("autonomous")}
        size="sm"
      >
        <Zap className="h-4 w-4 mr-2" />
        Autonomous
      </Button>
    </div>
  )
}
```

---

### 4.9 TelemetryPanel.tsx

**Purpose:** Right-side panel for system metrics and telemetry.

**Displayed Metrics:**
- LLM status (connected/disconnected)
- Browser status (active/inactive)
- Current mode
- Actions executed
- Response time

```tsx
export function TelemetryPanel() {
  return (
    <aside className="w-80 border-l bg-muted/20 p-6">
      <h3 className="font-semibold mb-4">System Telemetry</h3>
      
      <div className="space-y-4">
        <TelemetryItem label="LLM Status" value="Connected" status="success" />
        <TelemetryItem label="Browser" value="Active" status="success" />
        <TelemetryItem label="Mode" value="Chat" status="info" />
        <TelemetryItem label="Actions" value="12" status="info" />
        <TelemetryItem label="Avg Response" value="1.2s" status="success" />
      </div>
    </aside>
  )
}
```

---

### 4.10 SettingsModal.tsx

**Purpose:** Settings dialog for configuration.

**Settings Categories:**
- LLM Configuration (API URL, model name, temperature)
- Browser Settings (headless mode, timeout)
- Safety Constraints (max iterations, loop detection)

```tsx
export function SettingsModal({ open, onClose }: Props) {
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Settings</DialogTitle>
        </DialogHeader>
        
        <Tabs defaultValue="llm">
          <TabsList>
            <TabsTrigger value="llm">LLM</TabsTrigger>
            <TabsTrigger value="browser">Browser</TabsTrigger>
            <TabsTrigger value="safety">Safety</TabsTrigger>
          </TabsList>
          
          <TabsContent value="llm">
            <Form>
              <FormField label="API URL" />
              <FormField label="Model Name" />
              <FormField label="Temperature" />
            </Form>
          </TabsContent>
          
          {/* Other tabs */}
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}
```

---

### 4.11 UI Components (shadcn/ui)

**Complete Component Library:**

The frontend includes 40+ production-ready UI components from shadcn/ui:

- **Layout:** Card, Sheet, Sidebar, Separator, ScrollArea
- **Forms:** Input, Textarea, Select, Checkbox, Switch, RadioGroup, Slider
- **Navigation:** Tabs, Menubar, NavigationMenu, Breadcrumb, Pagination
- **Overlays:** Dialog, AlertDialog, Drawer, Popover, HoverCard, Tooltip
- **Feedback:** Alert, Toast, Progress, Skeleton
- **Data Display:** Table, Badge, Avatar, Accordion
- **Interactive:** Button, Toggle, DropdownMenu, ContextMenu, Command
- **Charts:** Chart components (via Recharts)

All components are:
- ✅ Fully typed with TypeScript
- ✅ Accessible (ARIA compliant)
- ✅ Customizable with Tailwind CSS
- ✅ Dark mode compatible

---

## 5. DATA MODELS & SCHEMAS

### 5.1 Request/Response Models

**AgentMessageRequest:**
```json
{
  "message": "Search for Python tutorials",
  "session_id": "session_abc123"
}
```

**AgentMessageResponse:**
```json
{
  "reply": "I'll search for Python tutorials. Let me generate a plan...",
  "session_id": "session_abc123",
  "mode": "controlled_automation"
}
```

### 5.2 Action Models

**ActionPlan:**
```json
{
  "steps": [
    {
      "action": "open_url",
      "value": "https://google.com",
      "description": "Open Google"
    },
    {
      "action": "search",
      "value": "Python tutorials",
      "description": "Search for Python tutorials"
    }
  ],
  "reasoning": "Search strategy to find Python tutorials"
}
```

**ActionDecision (Autonomous):**
```json
{
  "thought": "I need to click the search button to submit the query",
  "action": "click",
  "target_selector": "button[type='submit']",
  "input_text": null,
  "confidence": 0.95,
  "explanation": "Submit button is visible and matches goal intent",
  "timestamp": "2026-02-26T10:30:00Z"
}
```

### 5.3 Page Observation Model

**PageState:**
```json
{
  "url": "https://google.com/search?q=python",
  "title": "python - Google Search",
  "main_text_summary": "Search results for python programming...",
  "headings": ["Python Programming", "Learn Python"],
  "links": [
    {
      "text": "Python.org",
      "selector": "a[href='https://python.org']"
    }
  ],
  "buttons": [
    {
      "text": "Search",
      "selector": "button.search-btn"
    }
  ],
  "inputs": [
    {
      "name": "q",
      "type": "text",
      "selector": "input[name='q']",
      "placeholder": "Search"
    }
  ],
  "analysis_timestamp": "2026-02-26T10:30:00Z"
}
```

---

## 6. API ENDPOINTS

### 6.1 POST /agent/message

**Description:** Main unified message endpoint for all interactions.

**Request:**
```json
POST /agent/message
Content-Type: application/json

{
  "message": "Search for AI research papers",
  "session_id": "optional-session-id"
}
```

**Response (Chat Mode):**
```json
{
  "reply": "AI research papers cover topics like machine learning, neural networks...",
  "session_id": "session_12345",
  "mode": "chat"
}
```

**Response (Controlled Mode - Approval Needed):**
```json
{
  "reply": "I've created a plan to search for AI research papers:\n\n1. Open Google\n2. Search 'AI research papers'\n3. Click first result\n\nShall I proceed? (Reply 'yes' or 'no')",
  "session_id": "session_12345",
  "mode": "controlled_automation"
}
```

**Response (Autonomous Mode - In Progress):**
```json
{
  "reply": "🚀 Starting autonomous goal execution...\n📍 Step 1/10: Opening browser...\n✅ Navigating to Google...",
  "session_id": "session_12345",
  "mode": "autonomous_goal"
}
```

### 6.2 GET /health

**Description:** Health check for system components.

**Request:**
```
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "llm_available": true,
  "orchestrator_ready": true
}
```

---

## 7. CONFIGURATION & SETUP

### 7.1 Prerequisites

**Required Software:**

1. **Python 3.10+**
   ```bash
   python --version  # Should be 3.10 or higher
   ```

2. **Node.js 18+** (for frontend)
   ```bash
   node --version  # Should be 18 or higher
   ```

3. **LM Studio** (for local LLM)
   - Download: https://lmstudio.ai
   - Start LM Studio
   - Load a model (e.g., Mistral 7B Instruct)
   - Start local server on http://localhost:1234

4. **Playwright Browsers**
   ```bash
   playwright install chromium
   ```

### 7.2 Backend Setup

**Step 1: Install Dependencies**
```bash
cd backend
pip install -r requirements.txt
```

**Step 2: Install Playwright Browsers**
```bash
playwright install chromium
```

**Step 3: Configure Environment (Optional)**
```bash
cp .env.example .env
# Edit .env with your settings
```

**Example .env:**
```bash
LLM_BASE_URL=http://localhost:1234/v1
LLM_MODEL=mistral-7b-instruct
BROWSER_HEADLESS=true
LOG_LEVEL=INFO
```

**Step 4: Start Backend Server**
```bash
uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
```

**Verify:**
- Backend running at http://localhost:8000
- API docs at http://localhost:8000/docs
- Health check at http://localhost:8000/health

### 7.3 Frontend Setup

**Step 1: Install Dependencies**
```bash
cd frontend
npm install
```

**Step 2: Start Development Server**
```bash
npm run dev
```

**Verify:**
- Frontend running at http://localhost:5173
- Auto-reloads on code changes

**Step 3: Build for Production**
```bash
npm run build
# Output in dist/ folder
```

### 7.4 Running Everything

**Terminal 1: LM Studio**
```bash
# Start LM Studio GUI
# Load model (e.g., Mistral 7B Instruct)
# Click "Start Server" (port 1234)
```

**Terminal 2: Backend**
```bash
cd backend
uvicorn api_server:app --reload
```

**Terminal 3: Frontend**
```bash
cd frontend
npm run dev
```

**Access Application:**
- Open browser: http://localhost:5173
- Start chatting!

---

## 8. PROJECT STRUCTURE

### 8.1 Complete Directory Tree

```
general-agent/
│
├── backend/                          # Python backend
│   ├── action_executor.py           # Action execution layer
│   ├── agent_controller.py          # Autonomous reasoning loop (LEGACY)
│   ├── agent_core.py                # Core automation agent (LEGACY)
│   ├── api_server.py                # FastAPI REST API server
│   ├── approval_manager.py          # Human approval workflow (LEGACY)
│   ├── autonomous_controller.py     # NEW autonomous controller
│   ├── browser_controller.py        # Playwright browser wrapper
│   ├── chat_responder.py            # Chat mode handler (LEGACY)
│   ├── config.py                    # Centralized configuration
│   ├── examples.py                  # Usage examples
│   ├── executor.py                  # Plan executor
│   ├── intent_router.py             # Intent classification (LEGACY)
│   ├── llm_client.py                # LM Studio API client
│   ├── llm_planner.py               # LLM-based planner
│   ├── orchestrator.py              # NEW unified orchestrator
│   ├── page_analyzer.py             # Page state analyzer
│   ├── planner.py                   # HybridPlanner + multi-step planner
│   ├── requirements.txt             # Python dependencies
│   ├── test_autonomous_agent.py     # Test script
│   ├── __init__.py                  # Package init
│   │
│   ├── models/                      # Data models
│   │   ├── schemas.py              # Pydantic models
│   │   └── __init__.py
│   │
│   ├── utils/                       # Utilities
│   │   ├── logger.py               # Logging configuration
│   │   └── __init__.py
│   │
│   ├── docs/                        # Backend documentation
│   │   ├── AGENT_CORE.md
│   │   ├── AUTONOMOUS_AGENT.md
│   │   ├── IMPLEMENTATION_SUMMARY.md
│   │   ├── QUICK_START.md
│   │   └── README.md
│   │
│   └── .env.example                 # Environment template
│
├── frontend/                         # React frontend
│   ├── src/
│   │   ├── App.tsx                  # Root component
│   │   ├── main.tsx                 # Entry point
│   │   ├── index.css                # Global styles
│   │   ├── vite-env.d.ts            # Vite type definitions
│   │   │
│   │   ├── pages/
│   │   │   ├── Index.tsx            # Main chat page
│   │   │   └── NotFound.tsx         # 404 page
│   │   │
│   │   ├── components/
│   │   │   ├── AppHeader.tsx
│   │   │   ├── AppSidebar.tsx
│   │   │   ├── ChatComposer.tsx
│   │   │   ├── ChatMessage.tsx
│   │   │   ├── ModeSwitcher.tsx
│   │   │   ├── NavLink.tsx
│   │   │   ├── SettingsModal.tsx
│   │   │   ├── TelemetryPanel.tsx
│   │   │   │
│   │   │   └── ui/                  # shadcn/ui components (40+)
│   │   │       ├── accordion.tsx
│   │   │       ├── alert-dialog.tsx
│   │   │       ├── alert.tsx
│   │   │       ├── avatar.tsx
│   │   │       ├── badge.tsx
│   │   │       ├── button.tsx
│   │   │       ├── card.tsx
│   │   │       ├── dialog.tsx
│   │   │       ├── input.tsx
│   │   │       ├── select.tsx
│   │   │       ├── tabs.tsx
│   │   │       ├── textarea.tsx
│   │   │       ├── toast.tsx
│   │   │       └── ... (35+ more)
│   │   │
│   │   ├── hooks/
│   │   │   ├── use-mobile.tsx
│   │   │   └── use-toast.ts
│   │   │
│   │   ├── lib/
│   │   │   └── utils.ts             # Utility functions
│   │   │
│   │   └── test/
│   │       ├── example.test.ts
│   │       └── setup.ts
│   │
│   ├── public/
│   │   ├── favicon.ico
│   │   ├── placeholder.svg
│   │   └── robots.txt
│   │
│   ├── package.json                 # NPM dependencies
│   ├── package-lock.json
│   ├── bun.lockb                    # Bun lockfile
│   ├── tsconfig.json                # TypeScript config
│   ├── tsconfig.app.json
│   ├── tsconfig.node.json
│   ├── vite.config.ts               # Vite configuration
│   ├── vitest.config.ts             # Vitest testing config
│   ├── tailwind.config.ts           # Tailwind CSS config
│   ├── postcss.config.js            # PostCSS config
│   ├── components.json              # shadcn/ui config
│   ├── eslint.config.js             # ESLint config
│   ├── index.html                   # HTML entry point
│   ├── .gitignore
│   └── README.md
│
├── logs/                             # Application logs
│   └── agent.log
│
├── .gitignore
├── pyrightconfig.json               # Pyright type checking config
├── COMPLETE_PROJECT_DOCUMENTATION_FOR_CHATGPT.md
└── README.md
```

### 8.2 Key File Descriptions

**Backend Core Files:**
- `api_server.py` - FastAPI server, entry point
- `orchestrator.py` - Central control, intent routing
- `autonomous_controller.py` - Autonomous reasoning loop
- `planner.py` - HybridPlanner + multi-step planning
- `action_executor.py` - Action execution layer
- `page_analyzer.py` - Page observation
- `browser_controller.py` - Playwright wrapper
- `llm_client.py` - LM Studio integration

**Frontend Core Files:**
- `App.tsx` - Root component with routing
- `pages/Index.tsx` - Main chat interface
- `components/ChatMessage.tsx` - Message display
- `components/ChatComposer.tsx` - Message input
- `components/ModeSwitcher.tsx` - Mode selection

**Configuration Files:**
- `backend/config.py` - Backend configuration
- `frontend/vite.config.ts` - Vite build config
- `frontend/tailwind.config.ts` - Tailwind styling
- `.env` - Environment variables

---

## 9. DEPENDENCIES

### 9.1 Backend Dependencies

**Core Framework:**
```
fastapi==0.104.1          # REST API framework
uvicorn[standard]==0.24.0 # ASGI server
```

**Data Validation:**
```
pydantic==2.5.0           # Data validation
pydantic-settings==2.1.0  # Settings management
```

**Browser Automation:**
```
playwright==1.40.0        # Browser automation
```

**HTTP & Utilities:**
```
requests==2.31.0          # HTTP client for LLM
python-multipart==0.0.6   # File upload support
```

**Total:** 7 direct dependencies

### 9.2 Frontend Dependencies

**Core Framework:**
```
react==18.3.1             # UI framework
react-dom==18.3.1         # React DOM rendering
react-router-dom==6.30.1  # Routing
```

**Build Tools:**
```
vite==5.4.19              # Build tool & dev server
@vitejs/plugin-react-swc==3.11.0  # React plugin
typescript==5.8.3         # TypeScript support
```

**UI Library:**
```
@radix-ui/*               # 25+ Radix UI primitives
lucide-react==0.462.0     # Icon library
tailwindcss==3.4.17       # CSS framework
shadcn/ui components      # Pre-built UI components
```

**State Management:**
```
@tanstack/react-query==5.83.0  # Data fetching & caching
react-hook-form==7.61.1        # Form management
zod==3.25.76                   # Schema validation
```

**Utilities:**
```
clsx==2.1.1               # Conditional class names
tailwind-merge==2.6.0     # Merge Tailwind classes
date-fns==3.6.0           # Date utilities
```

**Total:** 60+ dependencies (including dev dependencies)

---

## 10. WORKFLOWS & USE CASES

### 10.1 Chat Mode Workflow

**Use Case:** User asks a question about programming.

```
User: "What is async/await in Python?"
  ↓
orchestrator.detect_intent() → CHAT
  ↓
orchestrator.handle_chat()
  ↓
llm_client.generate_response()
  ↓
Assistant: "Async/await in Python enables asynchronous programming..."
```

**Code Flow:**
```python
# orchestrator.py
async def handle_message(user_message: str):
    intent = self.detect_intent(user_message)  # → CHAT
    
    if intent == IntentMode.CHAT:
        response = await self._handle_chat(user_message)
        return response

async def _handle_chat(message: str):
    # Build context from conversation history
    context = self._build_context()
    
    # Generate response via LLM
    response = self.llm_client.generate_response(
        prompt=message,
        system_prompt="You are a helpful assistant...",
        temperature=0.7
    )
    
    # Add to history
    self.conversation_history.append({
        "role": "user",
        "content": message
    })
    self.conversation_history.append({
        "role": "assistant",
        "content": response
    })
    
    return response
```

---

### 10.2 Controlled Automation Workflow

**Use Case:** User requests browser automation with approval.

```
User: "Search for Python tutorials on Google"
  ↓
orchestrator.detect_intent() → CONTROLLED_AUTOMATION
  ↓
planner.generate_plan()
  ↓
orchestrator.await_approval()
  ↓
User: "yes"
  ↓
executor.execute(plan)
  ↓
Assistant: "✓ Completed: Searched Google for Python tutorials"
```

**Step-by-Step:**

1. **Plan Generation:**
```python
plan = planner.generate_plan("Search for Python tutorials")
# Returns:
# {
#   "steps": [
#     {"action": "open_url", "value": "https://google.com"},
#     {"action": "search", "value": "Python tutorials"}
#   ]
# }
```

2. **Approval Request:**
```python
approval_message = (
    "I'll execute these steps:\n"
    "1. Open Google\n"
    "2. Search for 'Python tutorials'\n"
    "\nProceed? (yes/no)"
)
# Store plan as pending
self.pending_plan = plan
return approval_message
```

3. **User Approval:**
```
User: "yes"
```

4. **Execution:**
```python
result = await executor.execute(self.pending_plan)
# Executes each step sequentially
# Returns: "✓ All 2 steps completed successfully!"
```

---

### 10.3 Autonomous Goal Workflow

**Use Case:** User sets a goal, agent operates autonomously.

```
User: "Find and summarize the top 3 Python courses"
  ↓
orchestrator.detect_intent() → AUTONOMOUS_GOAL
  ↓
autonomous_controller.run_goal()
  ↓
Loop: observe → decide → act (max 10 iterations)
  ↓
Assistant: "✅ Goal achieved! Found 3 Python courses: ..."
```

**Detailed Loop:**

```python
async def run_goal(goal: str, max_steps: int = 10):
    for step in range(max_steps):
        # 1. OBSERVE: Analyze current page
        observation = await page_analyzer.analyze_page()
        # Returns: {url, title, links, buttons, inputs, text}
        
        # 2. CHECK COMPLETION: Is goal achieved?
        if await self._is_goal_complete(goal, observation):
            return success_report
        
        # 3. DECIDE: What action to take next?
        decision = await planner.replan_next_action(
            goal=goal,
            page_state=observation,
            history=self._execution_history,
            failures=self._failure_history
        )
        # Returns: ActionDecision with action, selector, reasoning
        
        # 4. ACT: Execute the action
        result = await action_executor.execute(decision, page)
        
        # 5. RECORD: Track for learning
        self._execution_history.append({
            "step": step,
            "decision": decision,
            "result": result
        })
        
        if result["status"] == "failed":
            self._failure_history.append({...})
        
        await asyncio.sleep(1.0)  # Step delay
    
    return max_iterations_report
```

**Example Execution:**

```
Step 1: Observe → URL: about:blank
        Decide → navigate to google.com
        Act → Navigated to https://google.com

Step 2: Observe → URL: google.com, inputs: [search box]
        Decide → type "Python courses" into search box
        Act → Typed successfully

Step 3: Observe → URL: google.com/search, links: [10 results]
        Decide → click first result
        Act → Clicked, navigated to coursera.com

Step 4: Observe → URL: coursera.com/python
        Decide → read course information
        Act → Extracted text

Step 5: Observe → Same URL
        Decide → navigate back to search results
        Act → Navigated back

Step 6: Observe → URL: google.com/search
        Decide → click second result
        Act → Clicked, navigated to udemy.com

... (continues until goal complete or max steps)
```

---

### 10.4 Error Handling & Recovery

**Scenario: Click fails (element not found)**

```
Step 3: Decide → click button#enroll
        Act → Failed: Element not visible
        Record → Add to failure_history

Step 4: Decide → (planner sees failure in history)
                 Alternative: scroll down to find button
        Act → Scrolled down
        
Step 5: Decide → retry click button#enroll
        Act → Success!
```

**Scenario: Loop detected (scrolling 5 times)**

```
Step 8: scroll down
Step 9: scroll down
Step 10: scroll down
Step 11: scroll down
Step 12: scroll down
↓
Loop Detection: Same action repeated 5 times
↓
Abort: "Detected repetitive loop, stopping to avoid infinite cycle"
```

---

## 11. TESTING & DEBUGGING

### 11.1 Backend Testing

**Manual Testing:**

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test chat message
curl -X POST http://localhost:8000/agent/message \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, how are you?"}'

# Test automation request
curl -X POST http://localhost:8000/agent/message \
  -H "Content-Type: application/json" \
  -d '{"message": "Open Google and search for AI"}'
```

**Unit Testing (Planned):**

```python
# test_planner.py
def test_intent_detection():
    assert detect_intent("Hello") == IntentMode.CHAT
    assert detect_intent("Open Google") == IntentMode.CONTROLLED
    assert detect_intent("Find best courses") == IntentMode.AUTONOMOUS

def test_plan_generation():
    plan = planner.generate_plan("Search for Python")
    assert len(plan.steps) > 0
    assert plan.steps[0].action == ActionType.OPEN_URL
```

**Integration Testing:**

```python
# test_autonomous_agent.py
async def test_autonomous_goal():
    controller = AutonomousAgentController(...)
    result = await controller.run_goal("Find Wikipedia article on AI")
    
    assert result["final_status"] == "completed"
    assert "AI" in result["summary"]
```

### 11.2 Frontend Testing

**Component Tests (Vitest):**

```bash
npm run test
```

```typescript
// example.test.ts
import { render, screen } from '@testing-library/react'
import { ChatMessage } from '@/components/ChatMessage'

test('renders user message', () => {
  const message = {
    id: '1',
    role: 'user',
    content: 'Hello',
    timestamp: '10:30 AM'
  }
  
  render(<ChatMessage message={message} />)
  expect(screen.getByText('Hello')).toBeInTheDocument()
})
```

### 11.3 Debugging

**Enable Debug Logging:**

```python
# backend/utils/logger.py
logger.setLevel(logging.DEBUG)
```

**View Logs:**

```bash
tail -f logs/agent.log
```

**Browser DevTools:**

```python
# Run browser in non-headless mode
browser_controller = BrowserController(headless=False)
```

**LLM Request/Response Logging:**

```python
# llm_client.py
logger.debug(f"Sending prompt: {prompt}")
logger.debug(f"Received response: {response}")
```

---

## 12. SECURITY & BEST PRACTICES

### 12.1 Security Considerations

**1. Local Execution**
- ✅ LLM runs locally (LM Studio) - no data sent to cloud
- ✅ Browser automation runs locally
- ✅ API server runs locally (default: localhost:8000)

**2. Input Validation**
- ✅ Pydantic models validate all API inputs
- ✅ CSS selector sanitization in browser operations
- ✅ URL validation before navigation

**3. Safety Constraints**
- ✅ Max iterations limit (prevents infinite loops)
- ✅ Timeout protection (5-30 seconds per operation)
- ✅ Human approval required (controlled mode)
- ✅ Loop detection (prevents repetitive actions)

**4. Error Handling**
- ✅ Try-except blocks at every layer
- ✅ Graceful degradation on LLM failures
- ✅ Browser crash recovery
- ✅ Network timeout handling

### 12.2 Best Practices

**Backend:**

1. **Use Type Hints**
```python
async def execute(decision: ActionDecision, page: Page) -> Dict[str, Any]:
    ...
```

2. **Async/Await Properly**
```python
# Good
result = await browser.click(selector)

# Bad (blocks event loop)
result = browser.click(selector)  # Missing await
```

3. **Handle Errors Gracefully**
```python
try:
    result = await risky_operation()
except TimeoutError:
    logger.warning("Operation timed out, retrying...")
    result = await retry_operation()
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    return error_response()
```

4. **Log Appropriately**
```python
logger.debug("Detailed info for debugging")
logger.info("Important events")
logger.warning("Recoverable issues")
logger.error("Serious errors", exc_info=True)
```

**Frontend:**

1. **Type Safety**
```typescript
interface ChatMessageData {
  id: string
  role: "user" | "assistant"
  content: string
  timestamp: string
}
```

2. **Error Boundaries**
```tsx
<ErrorBoundary fallback={<ErrorMessage />}>
  <App />
</ErrorBoundary>
```

3. **Loading States**
```tsx
{isLoading ? <Spinner /> : <Content />}
```

4. **Accessibility**
```tsx
<button aria-label="Send message" disabled={isLoading}>
  <Send />
</button>
```

### 12.3 Performance Optimization

**Backend:**

1. **Use Connection Pooling**
```python
# Reuse browser instance across requests
app.state.browser_controller = BrowserController()
```

2. **Cache LLM Responses** (if deterministic)
```python
@lru_cache(maxsize=100)
def get_plan_for_request(request: str) -> ActionPlan:
    ...
```

3. **Async I/O**
```python
# Concurrent operations
results = await asyncio.gather(
    page_analyzer.analyze(),
    llm_client.generate_response()
)
```

**Frontend:**

1. **Code Splitting**
```typescript
const SettingsModal = lazy(() => import('./SettingsModal'))
```

2. **Memoization**
```tsx
const expensiveValue = useMemo(() => computeValue(data), [data])
```

3. **Virtual Scrolling** (for long message lists)
```tsx
<VirtualList items={messages} renderItem={renderMessage} />
```

---

## 🎉 CONCLUSION

This documentation provides a **complete reference** for the SANDHYA.AI autonomous browser automation agent project. 

**Key Takeaways:**

✅ **Production-ready** architecture with FastAPI + React  
✅ **Three operation modes** (chat, controlled, autonomous)  
✅ **Intelligent reasoning** using local LLM (LM Studio)  
✅ **Browser automation** via Playwright  
✅ **Safety-first** design with human approval and constraints  
✅ **100% local** execution (privacy-first)  

**Next Steps:**

1. ✅ **Setup Complete** - Follow configuration guide above
2. ✅ **Start Building** - Use code examples as templates
3. ✅ **Extend** - Add custom actions, planners, or UI components
4. ✅ **Deploy** - Docker containerization (future enhancement)

**Support:**
- Check existing documentation in `backend/docs/`
- Review code comments for implementation details
- Test with `test_autonomous_agent.py`

---

**Document Version:** 1.0.0  
**Last Updated:** February 26, 2026  
**Maintained By:** Agent Development Team  

**© 2026 SANDHYA.AI - All Rights Reserved**
