"""
Tools package for SANDHYA.AI.

Exposes a unified ToolRegistry that maps tool names to async callables.
The AutonomousGoalExecutor (executor.py) dispatches through this registry.

Execution contract:
  Every tool function MUST return a dict with at minimum:
    {"status": "success"|"error", "data": <any>, "error": <str|None>}

  If a tool returns something other than this format, ToolRegistry wraps it
  automatically so callers always get a consistent structure.
"""

from typing import Any, Callable, Dict, Optional

from ..utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# Shared result helpers (importable from any tool module)
# ============================================================================

def success(data: Any = None) -> Dict[str, Any]:
    """Return a standardised success payload."""
    return {"status": "success", "data": data, "error": None}


def failure(msg: str) -> Dict[str, Any]:
    """Return a standardised error payload."""
    return {"status": "error", "data": None, "error": str(msg)}


def _normalise(raw: Any) -> Dict[str, Any]:
    """
    Ensure raw tool output conforms to {status, data, error}.

    Handles:
      - Already-compliant dicts → returned as-is
      - Plain strings          → wrapped as success(data=string)
      - None                   → success(data=None)
      - Anything else          → success(data=str(raw))
    """
    if isinstance(raw, dict) and "status" in raw:
        # Ensure required keys exist
        raw.setdefault("data", None)
        raw.setdefault("error", None)
        return raw
    if raw is None:
        return success(None)
    if isinstance(raw, str):
        return success(raw)
    return success(str(raw))


# ============================================================================
# Tool Registry
# ============================================================================

class ToolRegistry:
    """
    Central registry mapping tool names → async callables.

    Contract guarantees:
      - execute() NEVER raises; always returns {status, data, error}
      - Unknown tool → failure("Tool '...' not registered")
      - Exception in tool → failure("<ExceptionType>: <message>")
      - Non-compliant return → auto-normalised to success format
    """

    def __init__(self):
        self._tools: Dict[str, Callable] = {}

    def register(self, name: str, fn: Callable) -> None:
        """Register a tool function under a given name."""
        self._tools[name] = fn
        logger.debug(f"[ToolRegistry] Registered tool: {name!r}")

    def get(self, name: str) -> Optional[Callable]:
        """Look up a tool by name, returning None if not found."""
        return self._tools.get(name)

    def available(self) -> list:
        """List all registered tool names."""
        return sorted(self._tools.keys())

    async def execute(self, name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dispatch a tool call by name with keyword parameters.

        Args:
            name:       Registered tool name (e.g. "open_url")
            parameters: Dict of keyword arguments passed to the tool

        Returns:
            Always a dict: {"status": "success"|"error", "data": ..., "error": ...}
            Never raises.
        """
        logger.info(f"[TOOL] Executing: {name} | params={parameters}")

        fn = self._tools.get(name)
        if fn is None:
            available = ", ".join(self.available()) or "(none registered)"
            result = failure(f"Tool '{name}' not registered. Available: {available}")
            logger.error(f"[TOOL RESULT] {result}")
            return result

        try:
            raw = await fn(**parameters)
            result = _normalise(raw)
        except Exception as e:
            result = failure(f"{type(e).__name__}: {e}")
            logger.error(
                f"[TOOL RESULT] {name} raised {type(e).__name__}: {e}",
                exc_info=True,
            )
            return result

        # Log result at appropriate level
        if result["status"] == "success":
            data_preview = str(result.get("data", ""))[:120]
            logger.info(f"[TOOL RESULT] {name} → success | data={data_preview!r}")
        else:
            logger.warning(f"[TOOL RESULT] {name} → error | {result['error']}")

        return result


# ============================================================================
# Module-level singleton (populated by api_server.py at startup)
# ============================================================================

registry = ToolRegistry()
