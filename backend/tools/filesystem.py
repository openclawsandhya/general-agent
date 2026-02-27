"""
File system tools for SANDHYA.AI.

Provides safe file operations scoped to the workspace output directory:
  create_file(path, content)
  read_file(path)
  list_files(directory)
  delete_file(path)

All paths are resolved relative to the agent's output base directory
(project root/output/) to prevent directory traversal.
"""

import asyncio
import os
import shutil
from pathlib import Path
from typing import Optional

from ..utils.logger import get_logger

logger = get_logger(__name__)

# Base output directory — agent files are written here
_BASE_DIR = Path(__file__).resolve().parent.parent.parent / "output"


def _safe_path(user_path: str) -> Path:
    """
    Resolve user-supplied path safely inside _BASE_DIR.
    Raises ValueError on path traversal attempts.
    """
    _BASE_DIR.mkdir(parents=True, exist_ok=True)
    resolved = (_BASE_DIR / user_path).resolve()
    try:
        resolved.relative_to(_BASE_DIR.resolve())
    except ValueError:
        raise ValueError(
            f"Path traversal detected: {user_path!r} escapes the output directory."
        )
    return resolved


# ============================================================================
# Tool functions (async wrappers for sync IO)
# ============================================================================

async def create_file(path: str, content: str = "") -> str:
    """Create or overwrite a file with given content."""
    logger.info(f"[Tool:create_file] path={path!r} len={len(content)}")
    try:
        safe = _safe_path(path)
        safe.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(_write_file, safe, content)
        return f"Created file: output/{path} ({len(content)} chars)"
    except Exception as e:
        logger.error(f"[Tool:create_file] Error: {e}")
        return f"Error creating file {path!r}: {e}"


def _write_file(path: Path, content: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


async def read_file(path: str) -> str:
    """Read and return the content of a file."""
    logger.info(f"[Tool:read_file] path={path!r}")
    try:
        safe = _safe_path(path)
        if not safe.exists():
            return f"File not found: {path!r}"
        content = await asyncio.to_thread(_read_file, safe)
        trimmed = content[:5000]  # cap to avoid huge memory entries
        suffix = f"\n[...truncated, total {len(content)} chars]" if len(content) > 5000 else ""
        return trimmed + suffix
    except Exception as e:
        logger.error(f"[Tool:read_file] Error: {e}")
        return f"Error reading file {path!r}: {e}"


def _read_file(path: Path) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


async def list_files(directory: str = "./") -> str:
    """List files in a directory."""
    logger.info(f"[Tool:list_files] directory={directory!r}")
    try:
        safe = _safe_path(directory)
        if not safe.exists():
            return f"Directory not found: {directory!r}"
        entries = await asyncio.to_thread(_list_dir, safe)
        if not entries:
            return f"Directory is empty: {directory!r}"
        return "Files:\n" + "\n".join(f"  {e}" for e in entries[:100])
    except Exception as e:
        logger.error(f"[Tool:list_files] Error: {e}")
        return f"Error listing directory {directory!r}: {e}"


def _list_dir(path: Path) -> list:
    result = []
    for item in sorted(path.iterdir()):
        rel = item.relative_to(_BASE_DIR)
        marker = "/" if item.is_dir() else ""
        size = f" ({item.stat().st_size} bytes)" if item.is_file() else ""
        result.append(f"{rel}{marker}{size}")
    return result


async def delete_file(path: str) -> str:
    """Delete a file or empty directory."""
    logger.info(f"[Tool:delete_file] path={path!r}")
    try:
        safe = _safe_path(path)
        if not safe.exists():
            return f"Path not found: {path!r}"
        await asyncio.to_thread(_delete, safe)
        return f"Deleted: {path!r}"
    except Exception as e:
        logger.error(f"[Tool:delete_file] Error: {e}")
        return f"Error deleting {path!r}: {e}"


def _delete(path: Path) -> None:
    if path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


# ============================================================================
# Registry helper
# ============================================================================

def make_filesystem_tools() -> dict:
    """Return dict of filesystem tool async functions for ToolRegistry."""
    return {
        "create_file": create_file,
        "read_file": read_file,
        "list_files": list_files,
        "delete_file": delete_file,
    }
