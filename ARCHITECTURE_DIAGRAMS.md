# ARCHITECTURE DIAGRAMS
# SANDHYA.AI - Visual System Architecture

---

## 🏗️ SYSTEM ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│                         USER INTERFACE (Browser)                        │
│                     React + TypeScript + Tailwind CSS                   │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Index.tsx (Main Chat Page)                                      │  │
│  │  ┌──────────┐  ┌────────────┐  ┌─────────────────────────────┐  │  │
│  │  │ Sidebar  │  │  Messages  │  │  Telemetry Panel            │  │  │
│  │  │          │  │            │  │  • LLM Status               │  │  │
│  │  │ • Chat   │  │ User: ...  │  │  • Browser Status           │  │  │
│  │  │ • History│  │ Bot:  ...  │  │  • Current Mode             │  │  │
│  │  │ • Settings│ │            │  │  • Metrics                  │  │  │
│  │  └──────────┘  └────────────┘  └─────────────────────────────┘  │  │
│  │  ┌──────────────────────────────────────────────────────────────┐│  │
│  │  │  Mode Switcher: [ Chat | Controlled | Autonomous ]          ││  │
│  │  └──────────────────────────────────────────────────────────────┘│  │
│  │  ┌──────────────────────────────────────────────────────────────┐│  │
│  │  │  Chat Composer: [Type message...] [Send]                     ││  │
│  │  └──────────────────────────────────────────────────────────────┘│  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │
                              │ HTTP REST API
                              │ POST /agent/message
                              │ GET /health
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│                      BACKEND SERVER (FastAPI)                           │
│                       Python 3.10+ / Async                              │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  api_server.py - REST API Endpoints                              │  │
│  │  • POST /agent/message → route to orchestrator                   │  │
│  │  • GET /health → component health checks                         │  │
│  │  • Session management (per-user orchestrator instances)          │  │
│  └────────────────┬─────────────────────────────────────────────────┘  │
│                   │                                                     │
│                   ▼                                                     │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  orchestrator.py - Central Control Engine                        │  │
│  │  ┌────────────────────────────────────────────────────────────┐  │  │
│  │  │  handle_message(user_message)                              │  │  │
│  │  │    ↓                                                        │  │  │
│  │  │  detect_intent(message) → IntentMode                       │  │  │
│  │  │    • Check keywords (search, find, compare, etc.)          │  │  │
│  │  │    • Pattern matching (URLs, commands)                     │  │  │
│  │  │    • Returns: CHAT | CONTROLLED | AUTONOMOUS               │  │  │
│  │  └────────────────────────────────────────────────────────────┘  │  │
│  │                   │                                               │  │
│  │      ┌────────────┴────────────┬─────────────────┐              │  │
│  │      ▼                         ▼                 ▼              │  │
│  │  ┌──────────┐          ┌──────────────┐  ┌─────────────────┐   │  │
│  │  │   CHAT   │          │ CONTROLLED   │  │  AUTONOMOUS     │   │  │
│  │  │   MODE   │          │ AUTOMATION   │  │  GOAL MODE      │   │  │
│  │  └──────────┘          └──────────────┘  └─────────────────┘   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
┌──────────────────┐  ┌──────────────┐  ┌──────────────────────┐
│                  │  │              │  │                      │
│  LLM Client      │  │  Planner     │  │  Autonomous          │
│  (llm_client.py) │  │  (planner.py)│  │  Controller          │
│                  │  │              │  │  (autonomous_        │
│  • LM Studio API │  │ • HybridPlan │  │   controller.py)     │
│  • Health check  │  │ • MultiStep  │  │                      │
│  • Generate text │  │ • LLM-based  │  │ • Observe→Decide→Act │
│                  │  │              │  │ • Loop until goal    │
└────────┬─────────┘  └──────┬───────┘  └──────┬───────────────┘
         │                   │                 │
         │                   │                 │
         │                   ▼                 ▼
         │          ┌─────────────────┐ ┌──────────────────┐
         │          │   Executor      │ │  Page Analyzer   │
         │          │  (executor.py)  │ │ (page_analyzer.py│
         │          │                 │ │                  │
         │          │ • Execute plan  │ │ • Extract state  │
         │          │ • Retry logic   │ │ • Links, buttons │
         │          │ • Status updates│ │ • Text content   │
         │          └────────┬────────┘ └────────┬─────────┘
         │                   │                   │
         │                   ▼                   │
         │          ┌──────────────────────────┐ │
         │          │   Action Executor        │ │
         │          │  (action_executor.py)    │ │
         │          │                          │ │
         │          │ • Execute single action  │ │
         │          │ • Click, type, scroll    │ │
         │          │ • Retry on failure       │ │
         │          └────────┬─────────────────┘ │
         │                   │                   │
         │                   ▼                   ▼
         │          ┌────────────────────────────────────┐
         │          │   Browser Controller               │
         └──────────▶  (browser_controller.py)           │
                    │                                    │
                    │ • Playwright wrapper               │
                    │ • Browser lifecycle management     │
                    │ • Primitives: click, type, scroll  │
                    │ • Page navigation                  │
                    └────────┬───────────────────────────┘
                             │
                             ▼
                    ┌────────────────────┐
                    │  Playwright API    │
                    │  (Chromium)        │
                    └────────────────────┘
```

---

## 🔄 DATA FLOW DIAGRAMS

### 1. CHAT MODE FLOW

```
User Types: "What is Python?"
    │
    ▼
Frontend (Index.tsx)
    │ handleSend(message)
    ▼
fetch POST /agent/message { message: "What is Python?" }
    │
    ▼
Backend (api_server.py)
    │ message_endpoint()
    ▼
Orchestrator.handle_message()
    │
    ├─► detect_intent() → IntentMode.CHAT
    │
    └─► handle_chat()
        │
        ├─► Build conversation context
        │
        ├─► llm_client.generate_response()
        │   │
        │   └─► HTTP → LM Studio (localhost:1234)
        │       │ POST /v1/chat/completions
        │       │ { messages: [...], model: "mistral" }
        │       │
        │       └─► LM Studio (Local LLM)
        │           │ Inference on local model
        │           └─► Returns: "Python is a programming language..."
        │
        └─► Return response to user

Frontend receives response
    │
    └─► Display in ChatMessage component
```

---

### 2. CONTROLLED AUTOMATION FLOW

```
User Types: "Search Google for AI tutorials"
    │
    ▼
Frontend → POST /agent/message
    │
    ▼
Orchestrator.handle_message()
    │
    ├─► detect_intent() → IntentMode.CONTROLLED_AUTOMATION
    │   (Keywords: "search", "Google")
    │
    └─► handle_controlled()
        │
        ├─► CHECK: Is approval pending?
        │   ├─► NO → Generate new plan
        │   │   │
        │   │   ├─► planner.generate_plan("Search Google for AI tutorials")
        │   │   │   │
        │   │   │   ├─► Prompt LLM with system instructions
        │   │   │   │
        │   │   │   └─► LLM returns JSON:
        │   │   │       {
        │   │   │         "steps": [
        │   │   │           {"action": "open_url", "value": "https://google.com"},
        │   │   │           {"action": "search", "value": "AI tutorials"}
        │   │   │         ]
        │   │   │       }
        │   │   │
        │   │   ├─► Store as pending_plan
        │   │   │
        │   │   └─► Return: "I'll execute:\n 1. Open Google\n 2. Search 'AI tutorials'\n\nProceed? (yes/no)"
        │   │
        │   └─► YES → User replied to approval
        │       │
        │       ├─► Parse response (yes/no)
        │       │
        │       ├─► IF "yes":
        │       │   │
        │       │   └─► executor.execute(pending_plan)
        │       │       │
        │       │       ├─► FOR EACH step in plan:
        │       │       │   │
        │       │       │   ├─► Execute with retry
        │       │       │   │   │
        │       │       │   │   ├─► browser_controller.open_url("google.com")
        │       │       │   │   │   └─► playwright.page.goto()
        │       │       │   │   │
        │       │       │   │   └─► browser_controller.search("AI tutorials")
        │       │       │   │       └─► playwright.page.fill() + press Enter
        │       │       │   │
        │       │       │   └─► Send status updates
        │       │       │
        │       │       └─► Return: "✓ All 2 steps completed!"
        │       │
        │       └─► IF "no":
        │           └─► Clear pending_plan, return "Cancelled"
        │
        └─► Return result to frontend

Frontend displays result
```

---

### 3. AUTONOMOUS GOAL FLOW

```
User Types: "Find and compare top 3 Python courses"
    │
    ▼
Frontend → POST /agent/message
    │
    ▼
Orchestrator.handle_message()
    │
    ├─► detect_intent() → IntentMode.AUTONOMOUS_GOAL
    │   (Keywords: "find", "compare")
    │
    └─► handle_autonomous()
        │
        └─► autonomous_controller.run_goal("Find and compare top 3 Python courses")
            │
            ├─► Initialize: execution_history = [], failure_history = []
            │
            └─► FOR step = 0 to MAX_ITERATIONS (10):
                │
                ├─► 1. OBSERVE CURRENT STATE
                │   │
                │   └─► page_analyzer.analyze_page()
                │       │
                │       ├─► Extract page metadata (URL, title)
                │       ├─► Extract text content (visible text)
                │       ├─► Extract interactive elements:
                │       │   ├─► Links (text + CSS selector)
                │       │   ├─► Buttons (text + CSS selector)
                │       │   └─► Inputs (name, type, selector)
                │       │
                │       └─► Return PageState dict:
                │           {
                │             "url": "current page URL",
                │             "title": "page title",
                │             "links": [{text, selector}, ...],
                │             "buttons": [{text, selector}, ...],
                │             "inputs": [{name, type, selector}, ...]
                │           }
                │
                ├─► 2. CHECK GOAL COMPLETION
                │   │
                │   └─► _is_goal_complete(goal, observation)
                │       │
                │       ├─► Prompt LLM: "Is goal achieved given current state?"
                │       │
                │       └─► IF completed: RETURN success_report
                │
                ├─► 3. DETECT LOOPS
                │   │
                │   └─► _is_repetitive_loop(observation)
                │       │
                │       ├─► Check if URL hasn't changed (5+ steps)
                │       ├─► Check if same action repeated (5+ times)
                │       │
                │       └─► IF loop detected: RETURN loop_detected_report
                │
                ├─► 4. DECIDE NEXT ACTION
                │   │
                │   └─► planner.replan_next_action(
                │       │     goal=goal,
                │       │     page_state=observation,
                │       │     history=execution_history,
                │       │     failures=failure_history
                │       │   )
                │       │
                │       ├─► HybridPlanner tries deterministic rules:
                │       │   │
                │       │   ├─► IF URL is blank → navigate to search engine
                │       │   ├─► IF search box visible → type query
                │       │   ├─► IF relevant button → click button
                │       │   │
                │       │   └─► IF no rule matches → fallback to LLM
                │       │       │
                │       │       ├─► Prompt LLM with:
                │       │       │   • Goal
                │       │       │   • Current page state
                │       │       │   • Recent action history
                │       │       │   • Previous failures
                │       │       │
                │       │       └─► LLM returns JSON ActionDecision:
                │       │           {
                │       │             "action": "click",
                │       │             "target_selector": "a.course-link",
                │       │             "explanation": "Click first course link"
                │       │           }
                │       │
                │       └─► Return ActionDecision
                │
                ├─► 5. EXECUTE ACTION
                │   │
                │   └─► action_executor.execute(decision, page)
                │       │
                │       ├─► Route to action handler (click/type/scroll/etc.)
                │       │
                │       ├─► Execute with retries:
                │       │   │
                │       │   ├─► TRY 1: Execute action
                │       │   │   └─► IF timeout → TRY 2
                │       │   │
                │       │   └─► TRY 2: Execute action
                │       │       └─► IF fails → Return error
                │       │
                │       └─► Return result:
                │           {
                │             "status": "success|failed",
                │             "action": "click",
                │             "details": "Clicked element...",
                │             "duration_ms": 523
                │           }
                │
                ├─► 6. RECORD EXECUTION
                │   │
                │   ├─► Add to execution_history:
                │   │   {
                │   │     "step": step_number,
                │   │     "decision": ActionDecision,
                │   │     "result": execution_result,
                │   │     "timestamp": ISO_timestamp
                │   │   }
                │   │
                │   └─► IF result.status == "failed":
                │       └─► Add to failure_history:
                │           {
                │             "action": decision.action,
                │             "selector": decision.target_selector,
                │             "reason": result.error_message
                │           }
                │
                ├─► 7. SEND STATUS UPDATE
                │   │
                │   └─► status_callback(f"Step {step+1}/10: {decision.explanation}")
                │
                ├─► 8. WAIT (1 second between steps)
                │   │
                │   └─► await asyncio.sleep(1.0)
                │
                └─► 9. CONTINUE LOOP
                    │
                    └─► IF max_iterations reached:
                        └─► RETURN max_steps_report

Return final report to frontend:
{
  "goal": "Find and compare top 3 Python courses",
  "steps_taken": 8,
  "final_status": "completed",
  "summary": "Found 3 courses: Udemy Python, Coursera Python, ...",
  "execution_history": [...]
}
```

---

## 🧩 COMPONENT INTERACTION MATRIX

```
┌─────────────────────┬─────────┬─────────┬──────────┬──────────┬─────────┐
│ Component           │ LLM     │ Browser │ Planner  │ Executor │ Analyzer│
├─────────────────────┼─────────┼─────────┼──────────┼──────────┼─────────┤
│ Orchestrator        │ ✓ Uses  │ ✗       │ ✓ Uses   │ ✓ Uses   │ ✗       │
│ Chat Handler        │ ✓ Uses  │ ✗       │ ✗        │ ✗        │ ✗       │
│ Controlled Handler  │ ✗       │ ✗       │ ✓ Uses   │ ✓ Uses   │ ✗       │
│ Autonomous Handler  │ ✗       │ ✗       │ ✗        │ ✗        │ ✗       │
│ Autonomous Control  │ ✓ Uses  │ ✓ Uses  │ ✓ Uses   │ ✓ Uses   │ ✓ Uses  │
│ Planner (Multi)     │ ✓ Uses  │ ✗       │ ✗        │ ✗        │ ✗       │
│ Planner (Hybrid)    │ ✓ Uses  │ ✗       │ ✗        │ ✗        │ ✗       │
│ Executor            │ ✗       │ ✓ Uses  │ ✗        │ ✗        │ ✗       │
│ Action Executor     │ ✗       │ ✓ Uses  │ ✗        │ ✗        │ ✗       │
│ Page Analyzer       │ ✗       │ ✓ Uses  │ ✗        │ ✗        │ ✗       │
│ Browser Controller  │ ✗       │ ✗       │ ✗        │ ✗        │ ✗       │
│ LLM Client          │ ✗       │ ✗       │ ✗        │ ✗        │ ✗       │
└─────────────────────┴─────────┴─────────┴──────────┴──────────┴─────────┘

Legend:
  ✓ Uses  = Component uses/calls this service
  ✗       = No direct interaction
```

---

## 🔁 STATE TRANSITIONS

### Orchestrator Mode State Machine

```
                    ┌──────────────┐
                    │   INITIAL    │
                    │   (No Mode)  │
                    └──────┬───────┘
                           │
                           │ User sends message
                           │
                           ▼
                    ┌──────────────┐
                    │ DETECTING    │
                    │   INTENT     │
                    └──────┬───────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
┌──────────────┐  ┌────────────────┐  ┌─────────────────┐
│ CHAT MODE    │  │ CONTROLLED     │  │ AUTONOMOUS      │
│              │  │ AUTOMATION     │  │ GOAL MODE       │
└──────┬───────┘  └────────┬───────┘  └────────┬────────┘
       │                   │                    │
       │ Generate          │ Generate           │ Start
       │ response          │ plan               │ goal loop
       │                   │                    │
       ▼                   ▼                    ▼
┌──────────────┐  ┌────────────────┐  ┌─────────────────┐
│ RESPONDING   │  │ AWAITING       │  │ EXECUTING       │
│              │  │ APPROVAL       │  │ AUTONOMOUS      │
└──────┬───────┘  └────────┬───────┘  └────────┬────────┘
       │                   │                    │
       │ LLM call          │ User replies       │ Loop runs
       │                   │                    │
       ▼                   ▼                    ▼
┌──────────────┐  ┌────────────────┐  ┌─────────────────┐
│ COMPLETE     │  │ EXECUTING      │  │ COMPLETE        │
│              │  │ PLAN           │  │                 │
└──────────────┘  └────────┬───────┘  └─────────────────┘
                           │
                           │ Steps run
                           │
                           ▼
                  ┌────────────────┐
                  │ COMPLETE       │
                  │                │
                  └────────────────┘

All modes return to INITIAL when new message arrives
```

---

## 🔀 DECISION TREE: Intent Detection

```
User Message
      │
      ▼
┌─────────────────────────────────────────┐
│ Contains autonomous keywords?           │
│ ("find best", "compare", "research")    │
└────┬────────────────────────────────┬───┘
     │ YES                            │ NO
     ▼                                ▼
AUTONOMOUS_GOAL              ┌──────────────────────────┐
                             │ Contains automation      │
                             │ keywords?                │
                             │ ("open", "search",       │
                             │  "click", "navigate")    │
                             └────┬──────────────────┬──┘
                                  │ YES              │ NO
                                  ▼                  ▼
                          CONTROLLED_AUTOMATION   ┌────────────────┐
                                                  │ Contains URL?  │
                                                  │ (http://, .com)│
                                                  └────┬────────┬──┘
                                                       │ YES    │ NO
                                                       ▼        ▼
                                               CONTROLLED    CHAT
                                               AUTOMATION    MODE
```

---

## 🎭 SEQUENCE DIAGRAM: Autonomous Goal Execution

```
User    Frontend    API     Orchestrator    AutonomousCtrl    Planner    Executor    Browser    LLM
 │          │        │            │                 │            │          │          │         │
 │─Message──▶        │            │                 │            │          │          │         │
 │          │─POST───▶            │                 │            │          │          │         │
 │          │        │─handle_msg─▶                 │            │          │          │         │
 │          │        │            │─detect_intent───│            │          │          │         │
 │          │        │            │◀─AUTONOMOUS_GOAL│            │          │          │         │
 │          │        │            │─run_goal────────▶            │          │          │         │
 │          │        │            │                 │            │          │          │         │
 │          │        │            │                 │─analyze────▶          │          │         │
 │          │        │            │                 │◀─PageState─│          │          │         │
 │          │        │            │                 │            │          │          │         │
 │          │        │            │                 │─replan─────▶          │          │         │
 │          │        │            │                 │            │─decide───▶          │         │
 │          │        │            │                 │            │          │         │         │
 │          │        │            │                 │            │◀─ActionDecision───  │         │
 │          │        │            │                 │◀─ActionDecision───    │          │         │
 │          │        │            │                 │            │          │          │         │
 │          │        │            │                 │─execute────▶          │          │         │
 │          │        │            │                 │            │─click────▶          │         │
 │          │        │            │                 │            │          │─goto()───▶         │
 │          │        │            │                 │            │          │◀─loaded──│         │
 │          │        │            │                 │            │◀─success─│          │         │
 │          │        │            │                 │◀─result────│          │          │         │
 │          │        │            │                 │            │          │          │         │
 │          │        │            │                 │─[LOOP continues...]   │          │         │
 │          │        │            │                 │            │          │          │         │
 │          │        │            │                 │─is_complete─▶         │          │         │
 │          │        │            │                 │            │──────────▶          │         │
 │          │        │            │                 │            │          │          │─check───▶
 │          │        │            │                 │            │          │          │◀─YES────│
 │          │        │            │                 │◀─COMPLETE──│          │          │         │
 │          │        │            │◀─final_report───│            │          │          │         │
 │          │        │◀─response──│                 │            │          │          │         │
 │          │◀─JSON──│            │                 │            │          │          │         │
 │◀─Display─│        │            │                 │            │          │          │         │
 │          │        │            │                 │            │          │          │         │
```

---

## 📊 DEPENDENCY GRAPH

```
Frontend Dependencies:
  React ──┬──▶ react-dom
          ├──▶ react-router-dom
          └──▶ @tanstack/react-query

  UI ─────┬──▶ @radix-ui/* (25 packages)
          ├──▶ lucide-react (icons)
          ├──▶ tailwindcss
          └──▶ shadcn/ui components

  Build ──┬──▶ vite
          ├──▶ typescript
          └──▶ @vitejs/plugin-react-swc

Backend Dependencies:
  FastAPI ─┬──▶ uvicorn (ASGI server)
           ├──▶ pydantic (validation)
           └──▶ python-multipart

  Browser ─▶ playwright

  HTTP ────▶ requests (LLM client)

  Config ──▶ pydantic-settings
```

---

## 🗂️ FILE DEPENDENCY MAP

```
api_server.py
  ├── llm_client.py
  ├── planner.py
  │   └── llm_client.py
  ├── browser_controller.py
  ├── executor.py
  │   └── browser_controller.py
  ├── agent_controller.py (LEGACY)
  ├── orchestrator.py
  │   ├── llm_client.py
  │   ├── planner.py
  │   ├── executor.py
  │   └── autonomous_controller.py
  │       ├── page_analyzer.py
  │       ├── planner.py (HybridPlanner)
  │       ├── action_executor.py
  │       └── llm_client.py
  └── models/schemas.py

Frontend (simplified):
App.tsx
  └── pages/Index.tsx
      ├── components/AppHeader.tsx
      ├── components/AppSidebar.tsx
      │   └── components/NavLink.tsx
      ├── components/ChatMessage.tsx
      ├── components/ChatComposer.tsx
      │   ├── components/ui/textarea.tsx
      │   └── components/ui/button.tsx
      ├── components/ModeSwitcher.tsx
      ├── components/TelemetryPanel.tsx
      └── components/SettingsModal.tsx
          ├── components/ui/dialog.tsx
          └── components/ui/tabs.tsx
```

---

**Last Updated:** February 26, 2026  
**Architecture Version:** 2.0.0
