# Autonomous Agent Controller Documentation

## Overview

`agent_controller.py` contains the `AutonomousAgentController` class, which implements a **fully autonomous goal-driven agent** that runs a continuous feedback loop:

```
OBSERVE STATE → CHECK IF GOAL COMPLETE → REASON (LLM) → EXECUTE → REPEAT
```

Unlike the single-plan approach in `AutomationAgent`, this controller:
- Continuously observes the browser state
- Dynamically reasons about next steps via LLM
- Adapts actions based on real-time feedback
- Detects stuck loops and exits gracefully
- Runs until goal is achieved or max iterations reached

## Architecture

```
┌─────────────────────────────────────────────┐
│   AutonomousAgentController                 │
│  (runs goal-driven feedback loop)           │
└────────────────┬────────────────────────────┘
                 │
     ┌───────────┼───────────┐
     │           │           │
     ▼           ▼           ▼
   Browser    Executor     LLM
  Controller (executes)  (reasons)
     │           │           │
     └───────────┼───────────┘
                 │
         Playwright   Plan    LM Studio
         Automation   Exec    (OpenAI
                             compatible)
```

## Key Features

✅ **Autonomous Reasoning**: LLM decides next steps dynamically  
✅ **Continuous Loop**: Observes → Decides → Executes → Repeats  
✅ **Safety Limits**: Max iterations + loop detection  
✅ **Real-time Feedback**: Streaming status updates  
✅ **Flexible Goals**: Any natural language goal  
✅ **Error Recovery**: Graceful degradation on failures  

## Class: AutonomousAgentController

### Constructor

```python
agent = AutonomousAgentController(
    browser_controller=browser,      # BrowserController instance
    executor=executor,               # Executor instance
    llm_client=llm,                  # LLMClient instance
    max_iterations=10                # Max loop iterations
)
```

### Main Methods

#### `run_goal(goal: str) -> str`

Runs the autonomous goal loop until completion.

```python
goal = "Find the cheapest Python course on Udemy"
result = await agent.run_goal(goal)
```

**Returns**: Completion report with status and final state

**Loop Details**:
```
for iteration in range(max_iterations):
    1. OBSERVE: Get current URL, title, visible text
    2. CHECK: Ask LLM if goal is complete
       → If YES: Return success
    3. DETECT: Check for repetitive loops
       → If LOOP: Return failure
    4. REASON: Ask LLM what to do next
    5. EXECUTE: Run the planned actions
```

#### `set_status_callback(callback: Callable[[str], None])`

Set function to receive status updates.

```python
def on_status(msg: str):
    print(f"[Status] {msg}")

agent.set_status_callback(on_status)
```

**Status Messages Include**:
- `🚀 Starting browser...`
- `📍 Step N/M: Analyzing current state...`
- `🤔 Reasoning about next steps...`
- `⚡ Executing: [action descriptions]`
- `✅ Goal achieved!`
- `🔄 Detected repetitive loop, stopping...`

#### `reset()`

Reset controller state for a new goal.

```python
agent.reset()
result = await agent.run_goal("Different goal")
```

#### `get_iteration_count() -> int`

Get current iteration count.

```python
iterations = agent.get_iteration_count()
print(f"Completed {iterations} iterations")
```

### Private Methods

#### `_observe_state() -> dict`

Collects current browser state.

**Returns**:
```python
{
    "url": "https://example.com",
    "title": "Example Page Title",
    "text": "Visible text content..."  # Summarized to 1500 chars
}
```

#### `_decide_next_actions(goal, observation) -> ActionPlan`

Uses LLM to generate next action plan.

**Prompt Template**:
```
GOAL: {goal}

CURRENT BROWSER STATE:
- URL: {url}
- Page Title: {title}
- Visible Text: {text}

What are the NEXT STEPS to take toward the goal?
```

**LLM Response** (JSON):
```json
{
  "steps": [
    {"action": "click", "selector": ".course-link", "description": "Click course"},
    {"action": "extract_text", "selector": ".price", "description": "Get price"}
  ],
  "reasoning": "Need to open course and check price..."
}
```

#### `_is_goal_complete(goal, observation) -> bool`

LLM evaluates if goal is achieved.

**Returns**: True if goal complete, False otherwise

#### `_is_repetitive_loop(observation) -> bool`

Detects if agent is stuck in repetitive loop.

**Heuristic**: If last 3 observations have same URL, returns True

## Workflow Example

### Scenario: "Find best free Python course"

```
Iteration 1:
  📍 Step 1/10: Analyzing current state...
  [Observes] URL=https://google.com, Title=Google
  🤔 Reasoning about next steps...
  ⚡ Executing: Search for 'best free Python course'

Iteration 2:
  📍 Step 2/10: Analyzing current state...
  [Observes] URL=https://google.com/search?q=best+free+python, Title=Search Results
  🤔 Reasoning about next steps...
  ⚡ Executing: Click first result

Iteration 3:
  📍 Step 3/10: Analyzing current state...
  [Observes] URL=https://article.example.com, Title=10 Best Free Python Courses
  🤔 Reasoning about next steps...
  ⚡ Executing: Extract visible text (find course names)

Iteration 4:
  📍 Step 4/10: Analyzing current state...
  [Observes] Text includes courses like "Codecademy Python", "freeCodeCamp Python"...
  ✅ Goal achieved!
  
Result: Successfully found best free Python courses
```

## Safety Features

### 1. Max Iterations Limit
```python
agent = AutonomousAgentController(..., max_iterations=10)
# Will stop after 10 iterations even if goal not complete
```

### 2. Loop Detection
```python
# Automatically detects repetitive patterns
if self._is_repetitive_loop(observation):
    return "Failed due to repetitive loop"
```

### 3. LLM-Controlled Only
- LLM only outputs **structured action plans**
- No direct code execution
- Actions are whitelisted (open_url, click, scroll, etc.)

### 4. Timeout Handling
- Each operation has timeout
- Graceful failure on timeout
- Detailed error messages

## Integration with Existing Modules

### Uses Existing Classes

| Module | Usage |
|--------|-------|
| BrowserController | Observes state (`get_current_url()`, `get_title()`, `extract_text()`) |
| Executor | Executes action plans (same as other agents) |
| LLMClient | Gets reasoning about next steps and goal completion |
| ActionPlan, ActionStep | Same structured action format |

### Compatibility Notes

```python
# ✓ Works with existing executor
plan = await agent._decide_next_actions(goal, observation)
await executor.execute(plan)

# ✓ Works with existing browser controller
observation = await agent._observe_state()
# Uses browser_controller.get_current_url(), etc.

# ✓ Works with existing LLM client
response = llm_client.generate_response(prompt, system_prompt)
```

## API Endpoints

### POST /agent/autonomous/goal

Run autonomous goal loop.

**Request**:
```json
{
  "message": "Find the best online machine learning course",
  "session_id": "optional-session-id"
}
```

**Response**:
```json
{
  "response": "✅ GOAL ACHIEVED!\nGoal: Find the best online machine learning course...",
  "intent": "automation",
  "session_id": "..."
}
```

### POST /agent/autonomous/goal/stream

Streaming autonomous goal execution.

**Server-Sent Events**:
```
data: {"type": "status", "content": "🚀 Initializing..."}
data: {"type": "progress", "content": "📍 Step 1: Analyzing..."}
data: {"type": "progress", "content": "⚡ Executing: Search for..."}
data: {"type": "response", "content": "✅ Goal achieved!", "is_final": true}
```

## Usage Examples

### Example 1: Basic Usage

```python
from agent_controller import AutonomousAgentController

agent = AutonomousAgentController(
    browser_controller=browser,
    executor=executor,
    llm_client=llm
)

goal = "Search for machine learning tutorials and get the top 3"
result = await agent.run_goal(goal)
print(result)
```

### Example 2: With Status Feedback

```python
def print_status(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

agent.set_status_callback(print_status)
result = await agent.run_goal("Find best online Python course")
```

Output:
```
[10:30:45] 🚀 Starting browser...
[10:30:46] 📍 Step 1/10: Analyzing current state...
[10:30:47] 🤔 Reasoning about next steps...
[10:30:48] ⚡ Executing: Open Google → Search for 'best online Python course'
[10:30:52] 📍 Step 2/10: Analyzing current state...
[10:30:53] ⚡ Executing: Click first result
[10:30:57] 📍 Step 3/10: Analyzing current state...
[10:30:58] ✅ Goal achieved!
```

### Example 3: Using with REST API

```bash
# Start goal loop
curl -X POST http://localhost:8000/agent/autonomous/goal \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Find best free Python course on Udemy"
  }'
```

### Example 4: Streaming with Real-Time Updates

```bash
# Stream goal execution
curl -X POST http://localhost:8000/agent/autonomous/goal/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Find cheapest Python course"
  }' \
  -N  # Disable buffering
```

## LLM Prompts

### Prompt 1: Decide Next Actions

```
You are an autonomous browser automation agent.
Your task is to decide the NEXT STEPS to take to achieve the given goal.

Available actions:
- open_url: Open a URL
- search: Search a query
- click: Click an element
- scroll: Scroll page
- extract_text: Extract page text
- fill_input: Fill input field
- wait: Wait duration
- navigate_back: Go back

GOAL: {goal}
CURRENT STATE: URL, Title, Visible Text

What are the NEXT STEPS?
```

**LLM Output**:
```json
{
  "steps": [...],
  "reasoning": "Why these steps will help..."
}
```

### Prompt 2: Is Goal Complete?

```
GOAL: {goal}
CURRENT STATE: URL, Title, Text

Has the goal been achieved?
Answer only with 'yes' or 'no'.
```

## Troubleshooting

### Agent keeps looping on same page

**Cause**: Poor LLM reasoning or circular actions

**Solution**:
```python
# Lower temperature for more consistent reasoning
# (Already set to 0.4 for planning, 0.1 for completion check)

# Or check browser conditions
observation = await agent._observe_state()
print(f"Current URL: {observation['url']}")
```

### Goal never completes after max iterations

**Possible Causes**:
1. Goal is too complex (needs more iterations)
2. Goal is ambiguous
3. Website structure doesn't match expectations

**Solutions**:
```python
# Increase max iterations
agent = AutonomousAgentController(..., max_iterations=20)

# Make goal more specific
# Instead of: "Find information about Docker"
# Use: "Go to official Docker website and find pricing page"
```

### LLM sending invalid action plans

**Cause**: LLM response not valid JSON

**Solution**: Agent has fallback to empty plan

```python
# The agent continues if LLM fails:
plan = await agent._decide_next_actions(goal, observation)
if not plan:
    # Gracefully stops
    return "No valid actions suggested"
```

## Performance Characteristics

| Operation | Time |
|-----------|------|
| Observe state | 0.5-1s |
| LLM decision | 2-4s |
| LLM completion check | 1-2s |
| Action execution | 3-10s |
| Full iteration | 7-17s |
| Full goal (5 iterations avg) | 35-85s |

## Advanced Configuration

### Custom Loop Detection

```python
class CustomAutonomousAgent(AutonomousAgentController):
    def _is_repetitive_loop(self, observation):
        # Custom logic
        # Examples: check for error messages, specific URLs, etc.
        return super()._is_repetitive_loop(observation)
```

### Custom Status Formatting

```python
class CustomAgent(AutonomousAgentController):
    async def _send_status(self, message: str):
        # Send to webhook, database, etc.
        await send_to_webhook(message)
```

### Custom Goal Evaluation

```python
class CustomAgent(AutonomousAgentController):
    async def _is_goal_complete(self, goal, observation):
        # Use custom heuristics alongside LLM
        if "error" in observation.get("text", "").lower():
            return False
        return await super()._is_goal_complete(goal, observation)
```

## Differences from AutomationAgent

| Feature | AutomationAgent | AutonomousAgentController |
|---------|-----------------|--------------------------|
| Planning | Single plan created upfront | Dynamic planning each iteration |
| Adaptation | No; executes fixed plan | Yes; adapts based on state |
| Loop | No | Yes; repeats until goal complete |
| LLM Calls | 1-2 for planning | Many (per iteration + goal check) |
| User Input | Requires approval | Autonomous (no approval needed) |
| Best For | Single tasks | Complex multi-step goals |

## Future Enhancements

- [ ] Memory: Remember websites visited (reduce re-exploration)
- [ ] Learning: Improve action selection over time
- [ ] Parallelization: Run multiple autonomous agents
- [ ] Web Scraping: Extract structured data
- [ ] Form Filling: Intelligently handle web forms
- [ ] Error Recovery: Re-attempt failed actions automatically
- [ ] Multi-Modal: Process images/screenshots for better state understanding

## Production Considerations

### Cost
- Each iteration calls LLM 2-3 times
- With 5-10 iterations, expect 10-30 LLM calls per goal
- Monitor token usage with local LM Studio

### Reliability
- Test with variety of websites
- Set appropriate `max_iterations` based on goal complexity
- Monitor logs for repetitive loops

### Monitoring
```python
agent.set_status_callback(lambda msg: log_to_system(msg))
iterations = agent.get_iteration_count()
logger.info(f"Goal completed in {iterations} iterations")
```

---

**Version**: 1.0.0  
**Status**: Production Ready ✨
