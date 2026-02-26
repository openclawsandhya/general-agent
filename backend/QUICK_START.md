# Trial Generalized Automation Agent - Quick Start Guide

## What You Have

A production-ready backend for a browser automation agent that combines:
- **Conversational AI** (using local LLM via LM Studio)
- **Browser Automation** (using Playwright)
- **Human-in-the-loop Approval** (user must approve before automation executes)

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                      FastAPI Server                           │
│                    (api_server.py)                            │
└─────────────────────┬──────────────────────────────────────────┘
                      │
┌─────────────────────▼──────────────────────────────────────────┐
│              AutomationAgent (agent_core.py)                   │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  • Intent Detection (Chat vs Automation)               │  │
│  │  • Conversation Management                             │  │
│  │  • Approval Workflow                                   │  │
│  │  • History Tracking                                    │  │
│  └─────────────────────────────────────────────────────────┘  │
└────────┬───────────────────┬─────────────────────┬────────────┘
         │                   │                     │
    ┌────▼────┐  ┌──────────▼────────┐  ┌────────▼────────┐
    │LLMClient │  │   Planner         │  │  Executor      │
    │(Chat)    │  │(Generate Plans)   │  │(Execute Plans) │
    └──────────┘  └───────────────────┘  └────────┬────────┘
                                                   │
                                          ┌────────▼─────────┐
                                          │BrowserController │
                                          │ (Playwright)     │
                                          └──────────────────┘
```

## Prerequisites

1. **Python 3.9+**
2. **LM Studio** running locally (for chat functionality)
3. **Playwright browsers** installed

## Installation & Setup

### 1. Install Dependencies

```bash
cd c:\Users\SNS\Desktop\general agent\backend

pip install -r requirements.txt
playwright install chromium
```

### 2. Start LM Studio

```
1. Download LM Studio from https://lmstudio.ai
2. Load a model (e.g., Mistral 7B Instruct)
3. Start the local API server (default: http://localhost:1234)
```

Verify LM Studio is running:
```bash
curl http://localhost:1234/v1/models
```

### 3. Start the Agent Server

```bash
python api_server.py
```

Server runs on `http://localhost:8000`
API Documentation: `http://localhost:8000/docs`

## Usage Examples

### Example 1: Chat Request (No Automation)

```bash
curl -X POST http://localhost:8000/agent/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is machine learning?"
  }'
```

**Response:**
```json
{
  "response": "Machine learning is a field of artificial intelligence...",
  "intent": "chat",
  "session_id": "uuid-here"
}
```

### Example 2: Automation Request (With Approval)

**Step 1: Send automation request**
```bash
curl -X POST http://localhost:8000/agent/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Search for best free Python course",
    "session_id": "my-session-1"
  }'
```

**Response:**
```json
{
  "response": "I will perform the following steps:\n\n1. Open Google\n2. Search for 'best free Python course'\n3. Click first result\n\nReasoning: Opening Google and searching for course information.\n\n🔔 Shall I proceed? (yes/no)",
  "intent": "automation",
  "plan": {
    "steps": [
      {"action": "open_url", "value": "https://google.com",  ...},
      {"action": "search", "value": "best free Python course", ...},
      {"action": "click", "value": "click_first_result", ...}
    ]
  },
  "session_id": "my-session-1"
}
```

**Step 2: Approve execution**
```bash
curl -X POST http://localhost:8000/agent/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "yes",
    "session_id": "my-session-1"
  }'
```

**Response:**
```json
{
  "response": "✅ Automation completed successfully!\n\n✓ All 3 steps completed successfully!\n\n📋 Plan reasoning: Opening Google and searching for course information.\n\n📊 Execution: 3/3 steps completed",
  "intent": "automation",
  "session_id": "my-session-1"
}
```

### Example 3: Multiple Sessions

```bash
# Session 1
curl -X POST http://localhost:8000/agent/message \
  -d '{"message": "What is Docker?", "session_id": "user-1"}'

# Session 2 (different user)
curl -X POST http://localhost:8000/agent/message \
  -d '{"message": "What is Kubernetes?", "session_id": "user-2"}'

# Get session 1 history
curl http://localhost:8000/sessions/user-1/history
```

## Core Modules

| Module | Purpose |
|--------|---------|
| `api_server.py` | FastAPI REST API server |
| `agent_core.py` | Core orchestration logic (AutomationAgent) |
| `intent_router.py` | Intent detection (chat vs automation) |
| `llm_client.py` | LM Studio integration |
| `planner.py` | Converts requests to action plans |
| `browser_controller.py` | Playwright automation |
| `executor.py` | Executes action plans |
| `models/schemas.py` | Pydantic models/schemas |
| `utils/logger.py` | Logging configuration |

## API Endpoints

### Main Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/agent/message` | Send message, get response |
| POST | `/agent/message/stream` | Streaming variant (SSE) |
| GET | `/health` | Health check |

### Session Management

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/sessions/{session_id}` | Get session info |
| GET | `/sessions/{session_id}/history` | Get conversation history |
| DELETE | `/sessions/{session_id}` | Delete session |

### Browser Control

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/browser/start` | Start browser |
| GET | `/browser/stop` | Stop browser |

## Message Schema

### Request

```python
{
  "message": str,              # User message (required)
  "session_id": str            # Session ID (optional, auto-generated)
}
```

### Response

```python
{
  "response": str,             # Agent response (conversational)
  "intent": "chat" | "automation",  # Detected intent
  "plan": ActionPlan | None,   # Action plan if automation
  "session_id": str            # Session ID
}
```

## Automation Actions

The agent supports these browser actions:

| Action | Parameters | Example |
|--------|-----------|---------|
| `open_url` | `value` (URL) | Open Google |
| `search` | `value` (query) | Search for Python |
| `click` | `selector` | Click button |
| `click_first_result` | None | Click first search result |
| `scroll` | `value` (up/down), `amount` | Scroll down 3 times |
| `extract_text` | `selector` (optional) | Get page text |
| `fill_input` | `selector`, `value` | Type in input |
| `wait` | `duration_ms` | Wait 2000ms |
| `navigate_back` | None | Go back |

## Conversation Flow Examples

### Example 1: Multi-turn Chat

```
User: What is Python?
Agent: Python is a high-level programming language [...]

User: Give me pros and cons
Agent: Pros: Easy to learn, large ecosystem [...]
              Uses previous context to respond
```

### Example 2: Automation with Rejection

```
User: Search for data science courses
Agent: "I will perform these steps:
         1. Open Google
         2. Search for data science courses
         3. Click first result
         Shall I proceed?"

User: No, search for machine learning instead
Agent: "Automation cancelled. How else can I help?"

User: Search for machine learning courses  
Agent: "I will perform these steps:
         1. Open Google
         2. Search for machine learning courses
         3. Click first result
         Shall I proceed?"

User: Yes
Agent: "✓ All 3 steps completed successfully!"
```

## Configuration

Edit `api_server.py` to change:

```python
llm_client = LLMClient(
    base_url="http://localhost:1234/v1",  # LM Studio endpoint
    model="mistral-7b-instruct"            # Model name
)

browser_controller = BrowserController(
    headless=True,      # Run browser in headless mode
    timeout_ms=30000    # Timeout for operations
)
```

Or use `.env` file:
```
LLM_BASE_URL=http://localhost:1234/v1
LLM_MODEL=mistral-7b-instruct
BROWSER_HEADLESS=true
BROWSER_TIMEOUT_MS=30000
```

## Examples

### Run All Demos

```bash
python examples.py
```

### Run Specific Demo

```bash
# Direct agent usage (most comprehensive)
python examples.py --programmatic

# REST API with approval flow
python examples.py --api

# Streaming responses
python examples.py --stream
```

## Logging

Logs are written to:
- **Console**: INFO level
- **File**: `logs/agent.log` (DEBUG level)

View logs:
```bash
tail -f logs/agent.log
```

## Troubleshooting

### LLM not responding

**Error:** "Failed to connect to LM Studio at http://localhost:1234"

**Fix:**
```bash
# Check LM Studio is running
curl http://localhost:1234/v1/models

# Or restart LM Studio with API enabled
```

### Browser automation fails

**Error:** "Timeout opening URL"

**Fix:**
```bash
# Check internet connection
ping google.com

# Increase timeout:
browser_controller = BrowserController(timeout_ms=60000)
```

### "Session not found"

**Error:** Trying to access non-existent session

**Fix:**
```bash
# Sessions auto-expire after inactivity
# Create new session: don't include session_id in first request
```

## Production Deployment

### 1. Use Production ASGI Server

```bash
pip install gunicorn
gunicorn api_server:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 2. Add Environment Configuration

```bash
export LLM_BASE_URL=http://localhost:1234/v1
export BROWSER_HEADLESS=true
python api_server.py
```

### 3. Add Authentication

```python
from fastapi.security import HTTPBearer
auth = HTTPBearer()

@app.post("/agent/message")
async def message_endpoint(
    request: MessageRequest,
    credentials: HTTPAuthCredentials = Depends(auth)
):
    # Verify credentials
    ...
```

### 4. Monitor Health

```bash
# Periodic health check
while true; do
  curl -s http://localhost:8000/health | jq .
  sleep 30
done
```

### 5. Set Up Logging

```bash
# Send logs to centralized system
# (Sentry, ELK, CloudWatch, etc.)
```

## Integration with Frontend

The frontend (Lovable app) should:

1. **Send messages** to `POST /agent/message`
2. **Poll for session updates** via `GET /sessions/{session_id}`
3. **Handle intent in UI**:
   - intent="chat" → Display as chatbot response
   - intent="automation" → Show plan + approval buttons
4. **Stream responses** using `POST /agent/message/stream` (SSE)

### Example Frontend Integration

```javascript
// Send message
const response = await fetch('http://localhost:8000/agent/message', {
  method: 'POST',
  body: JSON.stringify({
    message: userInput,
    session_id: sessionId
  })
});

const data = await response.json();

if (data.intent === 'automation') {
  // Show plan and approval buttons
  showPlan(data.plan);
  showApprovalButtons("yes", "no");
} else {
  // Show chat response
  displayMessage(data.response);
}
```

## Files Structure

```
backend/
├── api_server.py              # FastAPI server
├── agent_core.py              # Core orchestration ⭐
├── intent_router.py           # Intent detection
├── llm_client.py              # LM Studio client
├── planner.py                 # Plan generation
├── browser_controller.py       # Playwright wrapper
├── executor.py                # Plan execution
├── config.py                  # Configuration
├── examples.py                # Usage examples
├── requirements.txt           # Dependencies
├── models/
│   ├── __init__.py
│   └── schemas.py             # Pydantic models
├── utils/
│   ├── __init__.py
│   └── logger.py              # Logging
├── logs/                      # Log files
│   └── agent.log
├── README.md                  # Main documentation
├── AGENT_CORE.md              # Agent core docs
└── QUICK_START.md             # This file
```

## Next Steps

1. ✅ Start LM Studio
2. ✅ Install dependencies
3. ✅ Start API server
4. ✅ Test with examples
5. ⭐ Build frontend (Lovable app)
6. ⭐ Deploy to production

## Support

For issues or questions:
1. Check `logs/agent.log`
2. Review `README.md` and `AGENT_CORE.md`
3. Run `python examples.py` to verify setup
4. Check LM Studio is running: `curl http://localhost:1234/v1/models`

---

**Happy automating! 🚀**
