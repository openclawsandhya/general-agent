# Testing Checklist - Production LM Studio Integration

This checklist verifies the full end-to-end integration between the React frontend, FastAPI backend, and LM Studio Mixtral model.

## Prerequisites

### 1. LM Studio Setup
- [ ] **LM Studio is installed** and running
- [ ] **Model Downloaded**: `mixtral-8x7b-instruct-v0.1` is downloaded
- [ ] **Model Loaded**: Model is loaded in LM Studio interface
- [ ] **Server Started**: Local inference server is running on `http://localhost:1234`
- [ ] **Port Accessible**: Port 1234 is not blocked by firewall

**Verification Command:**
```bash
curl http://localhost:1234/v1/models
```

**Expected Output:**
```json
{
  "data": [
    {
      "id": "mixtral-8x7b-instruct-v0.1",
      "object": "model",
      "created": 1234567890,
      ...
    }
  ]
}
```

---

## Backend Testing

### 2. Environment Configuration
- [ ] **`.env` file exists** in `backend/` directory
- [ ] **LLM_BASE_URL** is set to `http://localhost:1234/v1`
- [ ] **LLM_MODEL** is set to `mixtral-8x7b-instruct-v0.1`
- [ ] All other environment variables are configured

**Verification:**
```bash
cd backend
cat .env | grep LLM_
```

**Expected Output:**
```
LLM_BASE_URL=http://localhost:1234/v1
LLM_MODEL=mixtral-8x7b-instruct-v0.1
LLM_TIMEOUT=60
LLM_MAX_RETRIES=2
```

### 3. Python Dependencies
- [ ] **Virtual environment** is activated (if using venv)
- [ ] **Dependencies installed**: `pip install -r requirements.txt`
- [ ] **aiohttp installed** for async HTTP requests
- [ ] **python-dotenv installed** for env loading

**Verification:**
```bash
cd backend
pip list | grep -E "fastapi|aiohttp|dotenv|pydantic"
```

**Expected Output:**
```
aiohttp             3.9.1
fastapi             0.104.1
pydantic            2.5.0
python-dotenv       1.0.0
```

### 4. Backend Server Startup
- [ ] **Server starts** without errors
- [ ] **.env file loaded** (check startup logs)
- [ ] **LM Studio connection** verified on startup
- [ ] **Model verification** passes

**Start Command:**
```bash
cd backend
python api_server.py
```

**Expected Console Output:**
```
[LLM Health] ✓ LM Studio is reachable at http://localhost:1234/v1
[LLM Health] ✓ Model 'mixtral-8x7b-instruct-v0.1' is loaded and ready
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 5. Health Endpoint Test
- [ ] **GET /health** returns 200 OK
- [ ] **llm_available** is `true`
- [ ] **model** matches `mixtral-8x7b-instruct-v0.1`
- [ ] **model_loaded** is `true`
- [ ] **orchestrator_ready** is `true`

**Test Command:**
```bash
curl http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "llm_available": true,
  "model": "mixtral-8x7b-instruct-v0.1",
  "model_loaded": true,
  "orchestrator_ready": true,
  "timestamp": "2024-01-15T10:30:00.123456"
}
```

### 6. Message Endpoint Test
- [ ] **POST /agent/message** accepts requests
- [ ] **Request validation** works (400 for invalid data)
- [ ] **LLM generates response** from Mixtral
- [ ] **Response includes** `session_id`, `reply`, `status`
- [ ] **Execution time** is logged in backend console
- [ ] **Structured logging** outputs JSON

**Test Command:**
```bash
curl -X POST http://localhost:8000/agent/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, what is your name?",
    "mode": "chat",
    "session_id": "test-session-123"
  }'
```

**Expected Response:**
```json
{
  "session_id": "test-session-123",
  "reply": "Hello! I am Mixtral, an AI assistant...",
  "status": "success",
  "metadata": {
    "mode": "chat",
    "model": "mixtral-8x7b-instruct-v0.1"
  }
}
```

**Expected Backend Log:**
```
[LLM Client] Generating response for 1 messages
[API] ✓ Request processed successfully in 2.34s
```

### 7. Error Handling Test
- [ ] **Connection error** handled gracefully
- [ ] **Timeout error** returns structured JSON error
- [ ] **Invalid JSON** returns 422 validation error
- [ ] **Global exception handler** catches unexpected errors

**Test Command (with LM Studio stopped):**
```bash
# Stop LM Studio server first
curl -X POST http://localhost:8000/agent/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Test",
    "mode": "chat",
    "session_id": "test"
  }'
```

**Expected Response:**
```json
{
  "detail": {
    "error": "LLM service unavailable",
    "message": "Failed to connect to LM Studio. Is it running?",
    "timestamp": "2024-01-15T10:35:00.123456"
  }
}
```

---

## Frontend Testing

### 8. Frontend Dependencies
- [ ] **Node.js** installed (v18+ recommended)
- [ ] **Dependencies installed**: `npm install`
- [ ] **api.ts** file exists in `frontend/src/lib/`
- [ ] **TypeScript** compiles without errors

**Verification:**
```bash
cd frontend
npm list | grep -E "react|typescript|vite"
```

### 9. Frontend Dev Server
- [ ] **Dev server starts**: `npm run dev`
- [ ] **No compilation errors**
- [ ] **Accessible** at `http://localhost:5173` (or configured port)

**Start Command:**
```bash
cd frontend
npm run dev
```

**Expected Output:**
```
VITE v5.4.19  ready in 324 ms

➜  Local:   http://localhost:5173/
➜  Network: use --host to expose
```

### 10. API Client Integration
- [ ] **api.ts** exports `sendMessage`, `checkHealth`
- [ ] **TypeScript types** defined (MessageRequest, MessageResponse, HealthResponse)
- [ ] **Timeout handling** (60s default)
- [ ] **Error handling** with structured errors

**Verification:** Open browser dev console and check for import errors

### 11. Chat UI - Backend Communication
- [ ] **Send message** from chat input
- [ ] **Loading indicator** appears while waiting
- [ ] **Backend API called** (check Network tab)
- [ ] **Response displayed** in chat area
- [ ] **Toast notification** shown on success
- [ ] **Error toast** shown on failure

**Test Steps:**
1. Open `http://localhost:5173` in browser
2. Open DevTools (F12) → Network tab
3. Type "Hello" in chat input
4. Click Send button
5. Verify:
   - POST request to `http://localhost:8000/agent/message`
   - Response status 200
   - Response body contains `reply` field
   - Message appears in chat UI
   - Toast shows "Message sent"

### 12. Telemetry Panel - Live Updates
- [ ] **TelemetryPanel** visible on right side
- [ ] **Health polling** active (every 5 seconds)
- [ ] **Backend Status** shows "healthy"
- [ ] **LLM Server** shows "Connected"
- [ ] **Model** displays `mixtral-8x7b-instruct-v0.1`
- [ ] **Model Loaded** shows "Yes"
- [ ] **Refresh icon** animates during fetch
- [ ] **Last updated timestamp** updates every 5s

**Test Steps:**
1. Open browser with backend running
2. Watch TelemetryPanel for 15 seconds
3. Verify status updates automatically
4. Stop backend server
5. Verify panel shows "Offline" status
6. Restart backend
7. Verify panel recovers to "Connected"

### 13. Error Boundary
- [ ] **ErrorBoundary** wraps entire app in `main.tsx`
- [ ] **Try Again** button works
- [ ] **Reload Page** button works
- [ ] **Stack trace** shown in development mode

**Test Steps:**
1. Manually trigger an error (e.g., in ChatComposer throw new Error("test"))
2. Verify error boundary catches it
3. Verify "Try Again" button resets state
4. Remove test error

### 14. CORS Configuration
- [ ] **No CORS errors** in browser console
- [ ] **OPTIONS preflight** succeeds (check Network tab)
- [ ] **All HTTP methods** allowed (GET, POST, etc.)

**Verification:**
Check browser console for errors like:
```
❌ Access to fetch at 'http://localhost:8000/agent/message' from origin 
'http://localhost:5173' has been blocked by CORS policy
```

**Expected:** No CORS errors

---

## Integration Testing

### 15. Full End-to-End Flow
- [ ] **User sends message** → Frontend
- [ ] **Frontend calls** → Backend API
- [ ] **Backend calls** → LM Studio Mixtral
- [ ] **Mixtral generates** → Response
- [ ] **Backend returns** → Frontend
- [ ] **Frontend displays** → User sees reply

**Test Scenario:**
```
User Input: "Explain recursion in simple terms"
Expected: Mixtral-generated explanation appears in chat
```

### 16. Multi-Turn Conversation
- [ ] **First message** processed correctly
- [ ] **Follow-up message** maintains context
- [ ] **Session tracking** works (session_id passed)
- [ ] **Message history** preserved in UI

**Test Scenario:**
```
Message 1: "What is Python?"
Message 2: "Give me an example"
Expected: Message 2 context-aware response
```

### 17. Mode Switching
- [ ] **Chat mode** works
- [ ] **Controlled mode** sends correct mode parameter
- [ ] **Autonomous mode** sends correct mode parameter
- [ ] **Backend receives** mode in request
- [ ] **Telemetry shows** current mode

**Test Steps:**
1. Send message in Chat mode
2. Switch to Controlled mode
3. Send another message
4. Verify `/agent/message` request includes `"mode": "controlled"`

### 18. Error Recovery
- [ ] **Network error** shows user-friendly message
- [ ] **Timeout error** handled gracefully
- [ ] **Backend restart** → Frontend recovers
- [ ] **LM Studio restart** → Health check detects

**Test Scenario:**
1. Stop backend mid-conversation
2. Try to send message
3. Verify error toast appears
4. Restart backend
5. Send message again
6. Verify it works

### 19. Performance
- [ ] **First message** completes in <10s (Mixtral 8x7B)
- [ ] **Follow-up messages** respond quickly
- [ ] **UI remains responsive** during generation
- [ ] **No memory leaks** after 10+ messages

### 20. Logging and Observability
- [ ] **Backend logs** are structured JSON
- [ ] **Timestamps** on all logs
- [ ] **Frontend console logs** show API calls
- [ ] **Error logs** include stack traces

**Backend Log Example:**
```json
{
  "timestamp": "2024-01-15T10:40:00.123Z",
  "level": "INFO",
  "message": "Request processed successfully",
  "execution_time": 2.34,
  "session_id": "abc-123"
}
```

---

## Production Hardening Verification

### 21. Security
- [ ] **No API keys** in frontend code
- [ ] **Environment variables** not exposed to client
- [ ] **Input validation** on backend (Pydantic)
- [ ] **Error messages** don't leak sensitive info

### 22. Reliability
- [ ] **Retry logic** works (2 attempts in llm_client.py)
- [ ] **Graceful degradation** when LM Studio unavailable
- [ ] **Health monitoring** detects issues
- [ ] **Timeout protection** prevents hangs

### 23. User Experience
- [ ] **Loading states** clear and visible
- [ ] **Error messages** actionable ("Check LM Studio is running")
- [ ] **Success feedback** via toasts
- [ ] **Responsive UI** (no blocking)

---

## Regression Testing

### 24. Existing Features Still Work
- [ ] **Sidebar navigation** functional
- [ ] **Settings modal** opens/closes
- [ ] **Theme switching** works (if implemented)
- [ ] **Message formatting** (markdown, code blocks)

---

## Final Validation

### ✅ All Systems Go Checklist

**Before deployment, verify:**
- [ ] ✓ LM Studio running with Mixtral loaded
- [ ] ✓ Backend health endpoint returns all green
- [ ] ✓ Frontend builds without errors (`npm run build`)
- [ ] ✓ Full conversation flow works end-to-end
- [ ] ✓ Error handling tested and working
- [ ] ✓ Telemetry panel shows live data
- [ ] ✓ No console errors or warnings
- [ ] ✓ All TypeScript compilation clean
- [ ] ✓ All logs structured and readable

---

## Troubleshooting Common Issues

### Issue 1: "LLM service unavailable"
**Symptoms:** Backend returns 503, health check fails
**Solutions:**
1. Check LM Studio is running
2. Verify model is loaded (not just downloaded)
3. Test `curl http://localhost:1234/v1/models`
4. Check firewall/antivirus blocking port 1234

### Issue 2: CORS errors in browser
**Symptoms:** Frontend can't connect to backend
**Solutions:**
1. Verify backend CORS middleware configured
2. Check frontend API URL is correct
3. Ensure backend is running on expected port (8000)

### Issue 3: "Model not loaded"
**Symptoms:** Health check shows `model_loaded: false`
**Solutions:**
1. In LM Studio, click "Load Model" button
2. Wait for model to fully load (can take 30-60s)
3. Verify enough RAM available (Mixtral 8x7B needs ~8GB+)

### Issue 4: Timeout errors
**Symptoms:** Requests fail after 60s
**Solutions:**
1. Increase `LLM_TIMEOUT` in .env
2. Reduce max tokens in prompt
3. Check system resources (CPU/RAM)

### Issue 5: Frontend not updating TelemetryPanel
**Symptoms:** Panel shows "Checking..." or stale data
**Solutions:**
1. Check browser console for fetch errors
2. Verify health endpoint accessible
3. Check React component useEffect is running

---

## Success Criteria

**✅ Integration is complete when:**
1. User can send message in frontend
2. Backend receives request and calls LM Studio
3. Mixtral generates relevant response
4. Response appears in frontend chat UI
5. TelemetryPanel shows live backend status
6. Errors are handled gracefully with user feedback
7. Full conversation flow works without manual intervention

**🎉 Production Ready!**
