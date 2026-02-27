# Quick Start Guide - Production Setup

## Prerequisites Check

Before starting, ensure you have:
- ✓ LM Studio installed
- ✓ Mixtral-8x7b-instruct-v0.1 model downloaded
- ✓ Python 3.10+ installed
- ✓ Node.js 18+ installed
- ✓ Git repository cloned

---

## Step-by-Step Startup

### 1️⃣ Start LM Studio (Port 1234)

**Actions:**
1. Open LM Studio application
2. Navigate to "Models" tab
3. Locate `mixtral-8x7b-instruct-v0.1`
4. Click "Load Model" button
5. Wait for model to fully load (30-60 seconds)
6. Click "Start Server" (Local Server tab)
7. Server should start on `http://localhost:1234`

**Verify:**
```bash
curl http://localhost:1234/v1/models
```

**Expected Output:**
```json
{
  "data": [
    {
      "id": "mixtral-8x7b-instruct-v0.1",
      ...
    }
  ]
}
```

---

### 2️⃣ Start Backend (Port 8000)

**Open new terminal:**
```bash
cd "C:\Users\SNS\Desktop\autonomous agent build\general-agent\backend"

# Activate virtual environment (if using)
# Windows:
# .\venv\Scripts\activate
# Linux/Mac:
# source venv/bin/activate

# Install dependencies (first time only)
pip install -r requirements.txt

# Verify .env file exists
dir .env  # Windows
# ls -la .env  # Linux/Mac

# Start server
python api_server.py
```

**Expected Console Output:**
```
INFO:     Started server process
[LLM Health] ✓ LM Studio is reachable at http://localhost:1234/v1
[LLM Health] ✓ Model 'mixtral-8x7b-instruct-v0.1' is loaded and ready
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**Verify:**
```bash
# Open new terminal
curl http://localhost:8000/health
```

**Expected:**
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

---

### 3️⃣ Start Frontend (Port 5173)

**Open new terminal:**
```bash
cd "C:\Users\SNS\Desktop\autonomous agent build\general-agent\frontend"

# Install dependencies (first time only)
npm install

# Start dev server
npm run dev
```

**Expected Console Output:**
```
VITE v5.4.19  ready in 324 ms

➜  Local:   http://localhost:5173/
➜  Network: use --host to expose
➜  press h + enter to show help
```

**Open Browser:**
Navigate to `http://localhost:5173`

---

## Verification Steps

### ✅ Visual Verification (Frontend)

**1. Check TelemetryPanel (Right Side)**
- Backend Status: **healthy** (green dot)
- LLM Server: **Connected** (green)
- Model: **mixtral-8x7b-instruct-v0.1**
- Model Loaded: **Yes**
- Orchestrator: **Ready**

**2. Send Test Message**
- Type in chat input: `"Hello, what is 2+2?"`
- Click Send button
- Watch for:
  - Loading indicator appears
  - Response from Mixtral displays
  - Green success toast appears
  - TelemetryPanel updates (Steps Taken +1)

### ✅ Backend Terminal Logs

Should see logs like:
```
[LLM Client] Generating response for 1 messages
[API] ✓ Request processed successfully in 2.34s
```

### ✅ Browser Console (F12)

Should see logs like:
```
[Telemetry] Health status: {status: "healthy", llm_available: true, ...}
[API] Sending message: {message: "Hello, what is 2+2?", mode: "chat"}
[API] Response received: {reply: "2+2 equals 4", status: "success"}
```

---

## Common Startup Issues

### Issue 1: Backend shows "LLM service unavailable"

**Symptoms:**
```
[LLM Health] ✗ Failed to connect to LM Studio
```

**Solutions:**
1. Check LM Studio is running
2. Verify server is started (port 1234)
3. Test manually: `curl http://localhost:1234/v1/models`
4. Check model is loaded (not just downloaded)

---

### Issue 2: Frontend can't connect to backend

**Symptoms:**
- TelemetryPanel shows "Offline"
- CORS errors in browser console
- Messages fail to send

**Solutions:**
1. Verify backend is running: `curl http://localhost:8000/health`
2. Check port 8000 not blocked
3. Look for errors in backend terminal
4. Restart backend server

---

### Issue 3: "Model not loaded" in health check

**Symptoms:**
```json
{
  "model_loaded": false
}
```

**Solutions:**
1. In LM Studio, click "Load Model" button
2. Wait 30-60 seconds for model to load
3. Check system has enough RAM (8GB+ for Mixtral 8x7B)
4. Refresh backend health endpoint

---

## Quick Commands Reference

### Backend
```bash
# Start backend
cd backend
python api_server.py

# Check health
curl http://localhost:8000/health

# Test message endpoint
curl -X POST http://localhost:8000/agent/message \
  -H "Content-Type: application/json" \
  -d '{"message": "Test", "mode": "chat", "session_id": "test-123"}'
```

### Frontend
```bash
# Start frontend
cd frontend
npm run dev

# Build for production
npm run build

# Run tests
npm test
```

### LM Studio
```bash
# Check models
curl http://localhost:1234/v1/models

# Test inference directly
curl -X POST http://localhost:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mixtral-8x7b-instruct-v0.1",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

---

## Full System Status Check

**Run in order:**

1. **LM Studio**
   ```bash
   curl http://localhost:1234/v1/models
   ```
   ✅ Should return model list

2. **Backend**
   ```bash
   curl http://localhost:8000/health
   ```
   ✅ Should return `"status": "healthy"`

3. **Frontend**
   - Open http://localhost:5173 in browser
   ✅ Should load without errors

4. **End-to-End**
   - Send message in chat UI
   ✅ Should get response from Mixtral

---

## Shutting Down

**In reverse order:**

1. **Stop Frontend** - Press `Ctrl+C` in frontend terminal
2. **Stop Backend** - Press `Ctrl+C` in backend terminal  
3. **Stop LM Studio** - Click "Stop Server" in LM Studio app

---

## Environment Files Check

### Backend `.env` File
Location: `backend/.env`

Must contain:
```env
LLM_BASE_URL=http://localhost:1234/v1
LLM_MODEL=mixtral-8x7b-instruct-v0.1
LLM_TIMEOUT=60
LLM_MAX_RETRIES=2
```

### Frontend `.env` File (Optional)
Location: `frontend/.env`

Can contain:
```env
VITE_API_BASE_URL=http://localhost:8000
```

---

## Success Indicators

### ✅ Everything Working When:

**Backend Terminal:**
```
[LLM Health] ✓ Model 'mixtral-8x7b-instruct-v0.1' is loaded and ready
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Frontend TelemetryPanel:**
```
Backend: healthy ● (green)
LLM Server: Connected
Model: mixtral-8x7b-instruct-v0.1
Model Loaded: Yes
```

**Chat UI:**
- Send message → Get response
- No errors in console
- Success toast appears

---

## Troubleshooting Flowchart

```
Message fails to send?
│
├─ TelemetryPanel shows "Offline"?
│  ├─ YES → Backend not running
│  │         → Start backend (Step 2)
│  │
│  └─ NO → Check browser console for errors
│           ├─ CORS error → Backend CORS misconfigured
│           └─ Timeout → LM Studio slow/not responding
│
├─ Backend logs "LLM service unavailable"?
│  └─ YES → LM Studio not running or model not loaded
│            → Check Step 1
│
└─ 500 Internal Server Error?
   └─ Check backend terminal for Python errors
      → Check all dependencies installed
```

---

## Performance Expectations

**Normal Response Times:**
- Health check: **<100ms**
- First message: **3-7 seconds** (Mixtral model load)
- Follow-up messages: **2-5 seconds**
- TelemetryPanel refresh: **5 seconds** (automatic)

**System Requirements:**
- RAM: 8GB+ (for Mixtral 8x7B)
- CPU: Multi-core recommended
- Disk: 15GB+ (for model storage)
- Network: Localhost only (no internet required)

---

## Next Steps After Startup

1. **Test basic chat** - Send simple question
2. **Switch modes** - Try Chat, Controlled, Autonomous
3. **Monitor telemetry** - Watch status updates
4. **Test error handling** - Stop backend, try sending
5. **Review testing checklist** - See `TESTING_CHECKLIST.md`

---

## Support Files

- **IMPLEMENTATION_SUMMARY.md** - Complete implementation details
- **TESTING_CHECKLIST.md** - Comprehensive testing guide
- **COMPREHENSIVE_DOCUMENTATION.md** - Full codebase docs

---

**🚀 System Ready!**

Once all three components show green status, you have a fully functional production-grade LLM application running locally.
