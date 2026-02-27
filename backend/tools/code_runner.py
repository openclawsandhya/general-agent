"""
Code execution tools for SANDHYA.AI.

Provides sandboxed code execution:
  run_python(code)  — run a Python snippet, capture stdout/stderr
  run_shell(command) — run a shell command, capture output

Security: Both functions run in a subprocess with a timeout.
Shell commands are executed directly; use with trusted agent-generated code only.
"""

import asyncio
import subprocess
import sys
import io
import contextlib
import textwrap
from typing import Optional

from ..utils.logger import get_logger

logger = get_logger(__name__)

# Hard limits
_PYTHON_TIMEOUT = 15    # seconds
_SHELL_TIMEOUT = 30     # seconds
_MAX_OUTPUT = 4000      # chars to return to memory


# ============================================================================
# Python execution
# ============================================================================

async def run_python(code: str, timeout: int = _PYTHON_TIMEOUT) -> str:
    """
    Execute a Python code snippet in a subprocess.
    Returns combined stdout+stderr, capped at _MAX_OUTPUT chars.
    """
    logger.info(f"[Tool:run_python] len={len(code)} timeout={timeout}s")
    logger.debug(f"[Tool:run_python] code=\n{code[:500]}")

    # Wrap code to redirect output
    wrapper = textwrap.dedent(f"""
import sys, traceback
_code = {repr(code)}
try:
    exec(compile(_code, '<agent>', 'exec'), {{}})
except Exception as _e:
    print("ERROR:", traceback.format_exc(), file=sys.stderr)
""").strip()

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-c", wrapper,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
        out = stdout.decode("utf-8", errors="replace")
        err = stderr.decode("utf-8", errors="replace")

        result_parts = []
        if out.strip():
            result_parts.append(f"STDOUT:\n{out.strip()}")
        if err.strip():
            result_parts.append(f"STDERR:\n{err.strip()}")

        combined = "\n".join(result_parts) if result_parts else "(no output)"
        combined = combined[:_MAX_OUTPUT]

        if proc.returncode == 0 and not err.strip():
            logger.info(f"[Tool:run_python] OK | return_code={proc.returncode}")
        else:
            logger.warning(
                f"[Tool:run_python] return_code={proc.returncode} | stderr={err[:200]}"
            )

        return combined

    except asyncio.TimeoutError:
        logger.error(f"[Tool:run_python] Timed out after {timeout}s")
        return f"Python execution timed out after {timeout} seconds."
    except Exception as e:
        logger.error(f"[Tool:run_python] Error: {e}")
        return f"Python execution error: {e}"


# ============================================================================
# Shell execution
# ============================================================================

async def run_shell(command: str, timeout: int = _SHELL_TIMEOUT) -> str:
    """
    Execute a shell command and return combined stdout+stderr.
    Uses PowerShell on Windows, /bin/sh on Unix.
    """
    logger.info(f"[Tool:run_shell] command={command[:120]!r} timeout={timeout}s")

    if sys.platform == "win32":
        args = ["powershell", "-NoProfile", "-NonInteractive", "-Command", command]
    else:
        args = ["/bin/sh", "-c", command]

    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
        out = stdout.decode("utf-8", errors="replace").strip()
        err = stderr.decode("utf-8", errors="replace").strip()

        result_parts = []
        if out:
            result_parts.append(out)
        if err:
            result_parts.append(f"STDERR: {err}")

        combined = "\n".join(result_parts) if result_parts else "(no output)"
        combined = combined[:_MAX_OUTPUT]

        logger.info(
            f"[Tool:run_shell] return_code={proc.returncode} "
            f"| out_chars={len(out)}"
        )
        return combined

    except asyncio.TimeoutError:
        logger.error(f"[Tool:run_shell] Timed out after {timeout}s")
        return f"Shell command timed out after {timeout} seconds."
    except Exception as e:
        logger.error(f"[Tool:run_shell] Error: {e}")
        return f"Shell execution error: {e}"


# ============================================================================
# Registry helper
# ============================================================================

def make_code_tools() -> dict:
    """Return dict of code execution tool async functions for ToolRegistry."""
    return {
        "run_python": run_python,
        "run_shell": run_shell,
    }
