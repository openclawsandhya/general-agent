# Agent Core Documentation

## Overview

`agent_core.py` contains the `AutomationAgent` class, which is the central orchestration layer for the Trial Automation Agent. It provides:

- **Intent Detection**: Automatically determines if a message is conversational or automation-related
- **Conversation Management**: Maintains message history for context
- **Human-in-the-Loop Approval**: Requires user approval before executing automation
- **Multi-turn Interaction**: Handles approval/rejection responses in follow-up messages

## Architecture

```
User Message
    ↓
AutomationAgent.handle_message()
    ├─ Check if pending approval is needed
    │  └─ Yes → _handle_approval_response()
    └─ No → Detect intent
       ├─ Chat → _handle_chat_request()
       └─ Automation → _handle_automation_request()
```

## Key Classes

### AutomationAgent

Main orchestration class.

#### Constructor

```python
agent = AutomationAgent(
    planner=planner,           # Planner instance
    executor=executor,         # Executor instance  
    llm_client=llm_client      # LLMClient instance
)
```

#### Core Methods

**`handle_message(message: str) -> str`**
- Main entry point for processing user messages
- Returns conversational response
- Example usage:
  ```python
  response = await agent.handle_message("Search for Python courses")
  print(response)  # Plan explanation + approval request
  ```

**`has_pending_approval() -> bool`**
- Check if awaiting user approval for automation

**`get_pending_plan_summary() -> Optional[str]`**
- Get human-readable summary of pending plan

**`get_history() -> List[dict]`**
- Get full conversation history

**`clear_history() -> None`**
- Clear conversation history and pending state

## Workflow Examples

### Example 1: Chat-Only Interaction

```python
agent = AutomationAgent(planner, executor, llm_client)

# User asks a question
response = await agent.handle_message("What is machine learning?")
print(response)
# Output: "Machine learning is a field of AI that..."

# Chat history is maintained
history = agent.get_history()
print(len(history))  # 2 messages
```

### Example 2: Automation with Approval

```python
agent = AutomationAgent(planner, executor, llm_client)

# Step 1: Request automation
response = await agent.handle_message("Search for Python courses")
print(response)
# Output:
# "I will perform the following steps:
# 1. Open Google
# 2. Search for 'Python courses'
# 3. Click first result
# 🔔 Shall I proceed? (yes/no)"

print(agent.has_pending_approval())  # True

# Step 2: User approves
response = await agent.handle_message("yes")
print(response)
# Output:
# "✅ Automation completed successfully!
# ✓ All 3 steps completed successfully!..."

print(agent.has_pending_approval())  # False
```

### Example 3: Automation with Rejection

```python
agent = AutomationAgent(planner, executor, llm_client)

# Step 1: Request automation
response = await agent.handle_message("Find best React tutorial")
print(response)
# Output: [Plan explanation + approval request]

# Step 2: User rejects
response = await agent.handle_message("no")
print(response)
# Output: "Automation cancelled. How can I help you with something else?"

print(agent.has_pending_approval())  # False
```

### Example 4: Multi-turn Conversation

```python
agent = AutomationAgent(planner, executor, llm_client)

# Message 1: Chat
r1 = await agent.handle_message("What is AWS?")
# Agent responds with chat reply

# Message 2: Chat
r2 = await agent.handle_message("Tell me more about EC2")
# Agent responds, uses history for context

# Message 3: Automation
r3 = await agent.handle_message("Search for AWS tutorials")
# Agent generates plan, waits for approval

# Message 4: Approval
r4 = await agent.handle_message("yes")
# Agent executes and reports

history = agent.get_history()
# 8 messages total (4 user, 4 assistant)
```

## Intent Detection

The `_is_automation_request()` method uses rule-based heuristics (no LLM call):

**Classified as Automation if:**
- Contains action verbs: open, search, click, scroll, extract, etc.
- Contains URL patterns: http://, www., .com domains
- Uses command-like phrasing: "Can you search...", "Please find..."

**Otherwise:** Classified as Chat

### Automation Keywords

```python
{
    "open", "visit", "go to", "navigate", "search", "find", "look for",
    "click", "press", "scroll", "extract", "read", "get", "fetch",
    "type", "enter", "fill", "submit", "screenshot", "capture",
    "download", "upload", "buy", "purchase", "follow", "check"
}
```

## Approval Flow

### User Approval Recognition

Accepts various affirmative responses:
- "yes", "yeah", "yep", "ok", "okay", "proceed", "go", "sure", "alright"

Accepts various negative responses:
- "no", "nope", "cancel", "stop", "don't", "skip"

Responses are case-insensitive and stripped.

### Ambiguous Responses

If user response is ambiguous, agent asks for clarification:
```
"I'm not sure if you want to proceed. Please respond with 'yes' to proceed or 'no' to cancel."
```

## Response Formatting

### Plan Explanation

When generating plan, agent formats it readably:

```
I will perform the following steps:

1. Open Google
2. Search for 'Python tutorials'
3. Click first result

Reasoning: Opening Google and searching for tutorial videos.

🔔 Shall I proceed? (yes/no)
```

### Execution Report

After completion:

```
✅ Automation completed successfully!

✓ All 3 steps completed successfully!

📋 Plan reasoning: Opening Google and searching for tutorial videos.

📊 Execution: 3/3 steps completed
```

## Error Handling

The agent gracefully handles:

- Invalid or empty plans → Returns error message, doesn't set pending state
- LLM connection failures → Descriptive error message
- Execution failures → Reports error, clears pending state
- Timeout errors → Retries, then reports failure

All errors maintain conversation flow - user can continue interacting.

## Integration with API Server

The REST API (`api_server.py`) uses `AutomationAgent` like this:

```python
# Per-session agent
active_agents: dict = {}

def _get_or_create_agent(session_id: str) -> AutomationAgent:
    if session_id not in active_agents:
        active_agents[session_id] = AutomationAgent(
            planner=planner,
            executor=executor,
            llm_client=llm_client
        )
    return active_agents[session_id]

@app.post("/agent/message")
async def message_endpoint(request: MessageRequest):
    agent = _get_or_create_agent(session_id)
    response = await agent.handle_message(user_message)
    return MessageResponse(
        response=response,
        intent=IntentType.AUTOMATION if agent.pending_plan else IntentType.CHAT,
        plan=agent.pending_plan,
        session_id=session_id
    )
```

## Session Management

Each session maintains its own:
- Conversation history
- Pending plan (if any)
- Auto-cleared after deletion

### Session API Endpoints

```
POST /agent/message              # Send message, get response
GET  /sessions/{session_id}      # Get session metadata
GET  /sessions/{session_id}/history  # Get conversation history
DELETE /sessions/{session_id}    # Delete session + clear history
```

## Best Practices

### 1. Always Use Async

```python
# ✓ Correct
response = await agent.handle_message(message)

# ✗ Wrong - will block
response = agent.handle_message(message)  # No await!
```

### 2. Check Pending State

```python
if agent.has_pending_approval():
    print("Awaiting user approval...")
    summary = agent.get_pending_plan_summary()
    print(summary)
```

### 3. Handle Large Histories

```python
# Get history only when needed
history = agent.get_history()
if len(history) > 100:
    agent.clear_history()
    # Start fresh
```

### 4. One Agent Per Session

```python
# ✓ Correct - separate agents for each user session
agents = {}
agents['user_1'] = AutomationAgent(...)
agents['user_2'] = AutomationAgent(...)

# ✗ Wrong - shared agent loses context
global_agent = AutomationAgent(...)
```

## Advanced: Custom Intent Detection

To customize intent detection, override the method:

```python
class CustomAgent(AutomationAgent):
    def _is_automation_request(self, message: str) -> bool:
        # Custom logic here
        if "buy" in message.lower():
            return True
        return super()._is_automation_request(message)
```

## Troubleshooting

### Agent keeps asking for approval on same plan

**Issue:** User said "yes" but plan wasn't executed

**Solution:** Check browser is running and execute succeeded

```python
if agent.pending_plan:
    print("Plan still pending!")
    print(agent.get_pending_plan_summary())
```

### Conversation history not persisting

**Issue:** History clears unexpectedly

**Possible causes:**
- `clear_history()` was called
- Session was deleted
- Different agent instance

**Solution:** Use persistent async sessions

### Wrong intent classification

**Issue:** Chat marked as automation or vice versa

**Solution:** Check automation keywords match your use case

```python
# Add custom keywords in agent initialization
class MyAgent(AutomationAgent):
    AUTOMATION_KEYWORDS = AutomationAgent.AUTOMATION_KEYWORDS | {
        "customize", "extract", "analyze"
    }
```

## Testing

### Unit Test Example

```python
@pytest.mark.asyncio
async def test_chat_request():
    agent = AutomationAgent(mock_planner, mock_executor, mock_llm)
    response = await agent.handle_message("What is Python?")
    assert "Python" in response or "programming" in response
    assert not agent.has_pending_approval()

@pytest.mark.asyncio
async def test_automation_approval_flow():
    agent = AutomationAgent(mock_planner, mock_executor, mock_llm)
    
    # Request automation
    r1 = await agent.handle_message("Search for tutorials")
    assert agent.has_pending_approval()
    
    # Approve
    r2 = await agent.handle_message("yes")
    assert not agent.has_pending_approval()
    assert "completed" in r2.lower() or "executed" in r2.lower()
```

## Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| Chat response | 1-3s | LLM inference + history processing |
| Plan generation | 3-5s | LLM creates structured plan |
| Plan execution | 10-60s | Depends on browser operations + network |
| Intent detection | <100ms | Rule-based, no LLM |
| History lookup | <1ms | In-memory |

## Security Considerations

⚠️ **Important Notes:**

1. **No code execution:** Plans contain only predefined actions
2. **No arbitrary browser commands:** Only whitelisted Playwright methods
3. **Approval required:** No automation without user confirmation
4. **Session isolation:** Each session is independent
5. **Input validation:** All inputs sanitized before use

## Future Enhancements

- [ ] Conversation context summarization (for very long histories)
- [ ] Multi-step approval workflows
- [ ] Automation templates/saved workflows
- [ ] Predictive approval (learn user patterns)
- [ ] Plan refinement (user can edit plan before approval)
