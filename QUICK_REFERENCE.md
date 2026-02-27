# QUICK REFERENCE GUIDE
# SANDHYA.AI - Autonomous Browser Automation Agent

---

## 🚀 QUICK START

### Start the System (3 Steps)

**1. Start LM Studio**
```bash
# Open LM Studio GUI
# Load model (e.g., Mistral 7B)
# Click "Start Server" → localhost:1234
```

**2. Start Backend**
```bash
cd backend
uvicorn api_server:app --reload
# Running at http://localhost:8000
```

**3. Start Frontend**
```bash
cd frontend
npm run dev
# Running at http://localhost:5173
```

---

## 📦 PROJECT STRUCTURE

```
general-agent/
├── backend/              # Python FastAPI backend
│   ├── api_server.py    # REST API entry point
│   ├── orchestrator.py  # Central control engine
│   ├── autonomous_controller.py  # Autonomous loop
│   ├── planner.py       # Action planning
│   ├── action_executor.py  # Action execution
│   ├── page_analyzer.py # Page observation
│   ├── browser_controller.py  # Playwright wrapper
│   ├── llm_client.py    # LM Studio client
│   └── models/schemas.py  # Data models
│
└── frontend/             # React TypeScript frontend
    ├── src/
    │   ├── App.tsx      # Root component
    │   ├── pages/Index.tsx  # Main chat UI
    │   └── components/  # UI components
    └── package.json
```

---

## 🎯 THREE OPERATION MODES

### 1. Chat Mode
**Trigger:** Questions, greetings, explanations
```
User: "What is Python?"
Bot: "Python is a high-level programming language..."
```

### 2. Controlled Automation
**Trigger:** Action keywords (open, search, click)
```
User: "Search Google for AI tutorials"
Bot: "I'll execute: 1. Open Google 2. Search 'AI tutorials'. Proceed? (yes/no)"
User: "yes"
Bot: "✓ Completed!"
```

### 3. Autonomous Goal
**Trigger:** Research/exploration keywords (find best, compare, analyze)
```
User: "Find and compare top 3 Python courses"
Bot: "🚀 Starting autonomous execution...
     📍 Step 1/10: Opening Google...
     📍 Step 2/10: Searching courses...
     ...
     ✅ Goal achieved! Summary: ..."
```

---

## 🔧 KEY COMPONENTS

### Backend Components

| Component | Purpose | Key Method |
|-----------|---------|------------|
| **api_server.py** | REST API server | `POST /agent/message` |
| **orchestrator.py** | Intent routing & control | `handle_message()` |
| **autonomous_controller.py** | Autonomous reasoning loop | `run_goal()` |
| **planner.py** | HybridPlanner + multi-step planning | `generate_plan()`, `replan_next_action()` |
| **action_executor.py** | Execute actions on page | `execute(decision, page)` |
| **page_analyzer.py** | Observe page state | `analyze_page()` |
| **browser_controller.py** | Playwright wrapper | `click()`, `fill_input()`, `scroll()` |
| **llm_client.py** | LM Studio integration | `generate_response()` |

### Frontend Components

| Component | Purpose |
|-----------|---------|
| **App.tsx** | Root with routing & providers |
| **Index.tsx** | Main chat interface |
| **ChatMessage.tsx** | Display messages with markdown |
| **ChatComposer.tsx** | Message input with send button |
| **ModeSwitcher.tsx** | Switch between chat/controlled/autonomous |
| **TelemetryPanel.tsx** | System metrics display |
| **SettingsModal.tsx** | Configuration dialog |

---

## 📡 API ENDPOINTS

### POST /agent/message
**Unified message endpoint**

**Request:**
```json
{
  "message": "Search for Python tutorials",
  "session_id": "optional-session-id"
}
```

**Response:**
```json
{
  "reply": "I'll search for Python tutorials...",
  "session_id": "session_12345",
  "mode": "controlled_automation"
}
```

### GET /health
**Health check**

**Response:**
```json
{
  "status": "healthy",
  "llm_available": true,
  "orchestrator_ready": true
}
```

---

## 🧠 AUTONOMOUS LOOP

```
1. OBSERVE
   └─► page_analyzer.analyze_page()
       └─► Returns: {url, title, links, buttons, inputs, text}

2. CHECK COMPLETION
   └─► _is_goal_complete(goal, observation)
       └─► Returns: True if goal achieved

3. DETECT LOOPS
   └─► _is_repetitive_loop(observation)
       └─► Returns: True if same action repeated 5+ times

4. DECIDE
   └─► planner.replan_next_action(goal, page_state, history, failures)
       └─► Returns: ActionDecision {action, selector, reasoning}

5. ACT
   └─► executor.execute(decision, page)
       └─► Returns: {status, details, duration_ms}

6. RECORD
   └─► Add to execution_history
   └─► If failed, add to failure_history

7. REPEAT (max 10 iterations)
```

---

## ⚙️ CONFIGURATION

### Backend (.env)
```bash
LLM_BASE_URL=http://localhost:1234/v1
LLM_MODEL=mistral-7b-instruct
BROWSER_HEADLESS=true
LOG_LEVEL=INFO
```

### Frontend (environment)
```typescript
const API_BASE_URL = "http://localhost:8000"
```

---

## 📊 DATA MODELS

### ActionDecision (Autonomous Mode)
```python
{
  "thought": "Need to click search button",
  "action": "click",  # click, type, scroll, wait, navigate, finish
  "target_selector": "button[type='submit']",
  "input_text": null,
  "confidence": 0.95,
  "explanation": "Submit button visible and matches intent",
  "timestamp": "2026-02-26T10:30:00Z"
}
```

### ActionPlan (Controlled Mode)
```python
{
  "steps": [
    {"action": "open_url", "value": "https://google.com"},
    {"action": "search", "value": "Python tutorials"},
    {"action": "click", "selector": "a.result:first"}
  ],
  "reasoning": "Search strategy for tutorials"
}
```

### PageState (Observation)
```python
{
  "url": "https://google.com",
  "title": "Google",
  "main_text_summary": "Search the web...",
  "headings": ["Google Search"],
  "links": [{"text": "Gmail", "selector": "a#gmail"}],
  "buttons": [{"text": "Search", "selector": "button.search"}],
  "inputs": [{"name": "q", "type": "text", "selector": "input[name='q']"}]
}
```

---

## 🛠️ COMMON TASKS

### Add New Browser Action

**1. Update ActionType enum** (`models/schemas.py`)
```python
class ActionType(str, Enum):
    SCREENSHOT = "screenshot"  # Add new action
```

**2. Add executor method** (`action_executor.py`)
```python
async def _execute_screenshot(self, decision, page, start_time):
    await page.screenshot(path="screenshot.png")
    return self._success_result(decision, "Screenshot saved", start_time)
```

**3. Add router** (`action_executor.py`)
```python
if action == "screenshot":
    result = await self._execute_screenshot(decision, page, start_time)
```

### Add New Frontend Component

```tsx
// components/MyComponent.tsx
export function MyComponent({ prop }: Props) {
  return <div>{prop}</div>
}

// pages/Index.tsx
import { MyComponent } from "@/components/MyComponent"

<MyComponent prop="value" />
```

### Add Custom Planner Logic

**HybridPlanner** (`planner.py`)
```python
async def replan_next_action(self, goal, page_state, history, failures):
    # Add custom rule
    if "login" in goal.lower() and self._has_login_form(page_state):
        return ActionDecision(
            action="type",
            target_selector="input[type='email']",
            input_text=user_email,
            ...
        )
    
    # Fallback to LLM
    return await self._llm_decide(goal, page_state, history)
```

---

## 🐛 DEBUGGING

### Enable Debug Logging
```python
# utils/logger.py
logger.setLevel(logging.DEBUG)
```

### View Live Logs
```bash
tail -f logs/agent.log
```

### Non-Headless Browser (Visual Debugging)
```python
# browser_controller.py
browser_controller = BrowserController(headless=False)
```

### Test LLM Connection
```python
from llm_client import LLMClient

client = LLMClient()
print(client.health_check())  # Should return True
```

### Test Browser Actions
```python
from browser_controller import BrowserController

async def test():
    browser = BrowserController(headless=False)
    await browser.start()
    await browser.open_url("https://google.com")
    await asyncio.sleep(5)
    await browser.stop()

asyncio.run(test())
```

---

## 🚨 TROUBLESHOOTING

### LLM Not Connecting
**Problem:** Health check fails
**Solution:**
1. Ensure LM Studio is running
2. Check server is on port 1234
3. Verify `LLM_BASE_URL=http://localhost:1234/v1`

### Browser Timeout
**Problem:** Actions timeout
**Solution:**
1. Increase timeout: `BROWSER_TIMEOUT_MS=60000`
2. Check network connection
3. Run non-headless to see what's happening

### Loop Detection Triggering
**Problem:** Autonomous mode stops early
**Solution:**
1. Check if same action repeating
2. Adjust `LOOP_DETECTION_WINDOW` threshold
3. Improve planner decision logic

### Frontend Not Connecting to Backend
**Problem:** API requests fail
**Solution:**
1. Check backend is running (http://localhost:8000)
2. Verify CORS settings in `api_server.py`
3. Check browser console for errors

---

## 📈 PERFORMANCE TIPS

### Backend
- **Reuse browser instances** (don't create new browser per request)
- **Use connection pooling** for LLM client
- **Cache deterministic LLM responses**
- **Async/await properly** (don't block event loop)

### Frontend
- **Code split** large components
- **Memoize** expensive computations
- **Virtual scroll** for long message lists
- **Debounce** user input

---

## 🔐 SECURITY CHECKLIST

- ✅ All data processed locally (no cloud)
- ✅ Input validation (Pydantic models)
- ✅ CSS selector sanitization
- ✅ URL validation before navigation
- ✅ Human approval for controlled automation
- ✅ Max iteration limits (prevent infinite loops)
- ✅ Timeout protection (prevent freezes)
- ✅ Error handling at every layer

---

## 📚 USEFUL COMMANDS

### Backend
```bash
# Start server
uvicorn api_server:app --reload

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Run tests
python test_autonomous_agent.py
```

### Frontend
```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Build for production
npm run build

# Run tests
npm run test

# Lint code
npm run lint
```

---

## 🎓 LEARNING PATH

**Beginner:**
1. ✅ Understand three operation modes
2. ✅ Explore chat mode (simplest)
3. ✅ Test controlled automation with approval
4. ✅ Read `orchestrator.py` to see routing logic

**Intermediate:**
5. ✅ Understand autonomous loop in `autonomous_controller.py`
6. ✅ Study `planner.py` HybridPlanner logic
7. ✅ Explore `page_analyzer.py` observation system
8. ✅ Add custom browser actions

**Advanced:**
9. ✅ Implement custom planner strategies
10. ✅ Add new intent detection rules
11. ✅ Optimize LLM prompts for better decisions
12. ✅ Build custom frontend components

---

## 📞 SUPPORT RESOURCES

**Documentation:**
- `COMPREHENSIVE_DOCUMENTATION.md` - Full technical reference
- `COMPLETE_PROJECT_DOCUMENTATION_FOR_CHATGPT.md` - Original docs
- `backend/docs/` - Individual component docs

**Code Examples:**
- `backend/examples.py` - Usage examples
- `backend/test_autonomous_agent.py` - Test script

**API Docs:**
- http://localhost:8000/docs - Interactive API documentation (when server running)

---

**Last Updated:** February 26, 2026  
**Version:** 2.0.0  
**Quick Reference Version:** 1.0.0
