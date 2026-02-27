"""
Memory system for SANDHYA.AI autonomous agent.

Maintains:
  - short_term_memory: current task context (steps, results, errors)
  - long_term_memory:  persisted task history across sessions

Both stores are keyed by session_id.
Long-term memory is optionally persisted to a JSON file.
"""

import json
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from .utils.logger import get_logger

logger = get_logger(__name__)

# Where long-term memory is persisted (relative to cwd when server runs)
_MEMORY_DIR = os.path.join(os.path.dirname(__file__), "..", "logs", "memory")


# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class StepRecord:
    """Record of a single executed step."""
    step_number: int
    action: str
    parameters: Dict[str, Any]
    result: str
    success: bool
    duration_ms: int
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TaskRecord:
    """Full record of a task execution attempt."""
    task_id: str
    session_id: str
    goal: str
    mode: str
    started_at: str
    completed: bool = False
    completed_at: Optional[str] = None
    steps: List[StepRecord] = field(default_factory=list)
    final_result: Optional[str] = None
    iterations: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "session_id": self.session_id,
            "goal": self.goal,
            "mode": self.mode,
            "started_at": self.started_at,
            "completed": self.completed,
            "completed_at": self.completed_at,
            "steps": [s.to_dict() for s in self.steps],
            "final_result": self.final_result,
            "iterations": self.iterations,
        }


# ============================================================================
# Short-term memory (per-session, in-memory)
# ============================================================================

class ShortTermMemory:
    """
    In-memory store for a single task's context.

    Cleared at the start of each new task; retained across
    autonomous planning iterations for the same goal.
    """

    def __init__(self):
        self.task_id: Optional[str] = None
        self.goal: str = ""
        self.mode: str = "chat"
        self.steps: List[StepRecord] = []
        self.errors: List[str] = []
        self.variables: Dict[str, Any] = {}   # arbitrary key-value context
        self.started_at: Optional[str] = None

    def start_task(self, task_id: str, goal: str, mode: str) -> None:
        """Reset and start tracking a new task."""
        self.task_id = task_id
        self.goal = goal
        self.mode = mode
        self.steps = []
        self.errors = []
        self.variables = {}
        self.started_at = datetime.utcnow().isoformat() + "Z"
        logger.debug(f"[Memory] New task started | id={task_id} | goal={goal[:60]!r}")

    def add_step(
        self,
        step_number: int,
        action: str,
        parameters: Dict[str, Any],
        result: str,
        success: bool,
        duration_ms: int,
        error: Optional[str] = None,
    ) -> None:
        """Record a completed step."""
        record = StepRecord(
            step_number=step_number,
            action=action,
            parameters=parameters,
            result=result,
            success=success,
            duration_ms=duration_ms,
            error=error,
        )
        self.steps.append(record)
        if not success:
            self.errors.append(f"Step {step_number} ({action}): {error or result}")

    def set(self, key: str, value: Any) -> None:
        """Store an arbitrary value in context."""
        self.variables[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from context."""
        return self.variables.get(key, default)

    def get_steps_summary(self) -> str:
        """Human-readable summary of all steps."""
        if not self.steps:
            return "No steps executed yet."
        lines = []
        for s in self.steps:
            status = "✓" if s.success else "✗"
            lines.append(f"  {status} Step {s.step_number}: {s.action}({json.dumps(s.parameters)[:80]}) → {s.result[:100]}")
        return "\n".join(lines)

    def get_results_summary(self) -> str:
        """Summary of results collected so far."""
        results = [s.result for s in self.steps if s.success and s.result]
        if not results:
            return "No results collected."
        return "\n".join(f"  - {r[:200]}" for r in results[-10:])  # last 10

    def has_errors(self) -> bool:
        return bool(self.errors)

    def to_task_record(self, session_id: str) -> TaskRecord:
        """Convert current state to a TaskRecord for long-term storage."""
        return TaskRecord(
            task_id=self.task_id or "unknown",
            session_id=session_id,
            goal=self.goal,
            mode=self.mode,
            started_at=self.started_at or datetime.utcnow().isoformat() + "Z",
            steps=list(self.steps),
        )


# ============================================================================
# Long-term memory (persisted task history)
# ============================================================================

class LongTermMemory:
    """
    Persisted task history.

    On startup, loads existing records from disk.
    After each task, appends the completed record.
    """

    def __init__(self, persist_path: Optional[str] = None):
        self.persist_path = persist_path or os.path.join(_MEMORY_DIR, "long_term.json")
        self.records: List[TaskRecord] = []
        self._load()

    def _load(self) -> None:
        """Load persisted records from disk."""
        try:
            if os.path.exists(self.persist_path):
                with open(self.persist_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                    for item in raw:
                        steps = [StepRecord(**s) for s in item.get("steps", [])]
                        item["steps"] = steps
                        self.records.append(TaskRecord(**item))
                logger.info(f"[Memory] Loaded {len(self.records)} long-term records")
        except Exception as e:
            logger.warning(f"[Memory] Could not load long-term memory: {e}")
            self.records = []

    def _save(self) -> None:
        """Persist all records to disk."""
        try:
            os.makedirs(os.path.dirname(self.persist_path), exist_ok=True)
            data = [r.to_dict() for r in self.records]
            with open(self.persist_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"[Memory] Could not save long-term memory: {e}")

    def store_task(self, record: TaskRecord) -> None:
        """Append a completed task record and persist."""
        record.completed_at = datetime.utcnow().isoformat() + "Z"
        record.completed = True
        # Avoid duplicates
        self.records = [r for r in self.records if r.task_id != record.task_id]
        self.records.append(record)
        # Keep last 500 records
        if len(self.records) > 500:
            self.records = self.records[-500:]
        self._save()
        logger.debug(f"[Memory] Stored task {record.task_id!r} to long-term memory")

    def get_recent(self, n: int = 5) -> List[TaskRecord]:
        """Return the n most recent task records."""
        return self.records[-n:]

    def search_by_goal(self, keyword: str) -> List[TaskRecord]:
        """Find tasks whose goal contains the keyword (case-insensitive)."""
        kw = keyword.lower()
        return [r for r in self.records if kw in r.goal.lower()]

    def summary(self) -> str:
        """Human-readable summary of task history."""
        if not self.records:
            return "No task history."
        recent = self.records[-5:]
        lines = [f"Last {len(recent)} tasks:"]
        for r in recent:
            status = "✓" if r.completed else "…"
            lines.append(
                f"  {status} [{r.started_at[:10]}] {r.goal[:60]} "
                f"({len(r.steps)} steps, mode={r.mode})"
            )
        return "\n".join(lines)


# ============================================================================
# Unified MemoryManager
# ============================================================================

class MemoryManager:
    """
    Facade over ShortTermMemory + LongTermMemory.

    One MemoryManager is created per session.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory()
        logger.info(f"[Memory] MemoryManager created for session {session_id}")

    # ---- Delegate short-term helpers ----

    def start_task(self, task_id: str, goal: str, mode: str) -> None:
        self.short_term.start_task(task_id, goal, mode)

    def add_step(self, **kwargs) -> None:
        self.short_term.add_step(**kwargs)

    def set(self, key: str, value: Any) -> None:
        self.short_term.set(key, value)

    def get(self, key: str, default: Any = None) -> Any:
        return self.short_term.get(key, default)

    def steps_summary(self) -> str:
        return self.short_term.get_steps_summary()

    def results_summary(self) -> str:
        return self.short_term.get_results_summary()

    # ---- Complete and archive current task ----

    def complete_task(self, final_result: str, iterations: int = 1) -> None:
        """Mark current task as done, move to long-term memory."""
        record = self.short_term.to_task_record(self.session_id)
        record.final_result = final_result
        record.iterations = iterations
        self.long_term.store_task(record)
        logger.info(
            f"[Memory] Task complete | id={record.task_id} | "
            f"steps={len(record.steps)} | iterations={iterations}"
        )

    # ---- Context for LLM re-planning ----

    @property
    def goal(self) -> str:
        return self.short_term.goal

    @property
    def steps(self):
        return self.short_term.steps
