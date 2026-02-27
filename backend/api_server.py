"""
Production FastAPI server for Trial Generalized Automation Agent.

Unified API layer that routes all user interactions through AgentOrchestrator,
the central control engine supporting:
  - Conversational chat mode
  - Controlled automation with approval flow
  - Autonomous goal-driven execution

The orchestrator internally decides routing based on intent detection.

Author: Agent System
Date: 2026-02-25
Version: 2.0.0
"""

import os
import asyncio
import uuid
import json
import time
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from .config import settings
from .llm_client import LLMClient
from .planner import Planner
from .browser_controller import BrowserController
from .executor import Executor
from .agent_controller import AutonomousAgentController
from .orchestrator import AgentOrchestrator
from .tools import registry as tool_registry
from .tools.browser import make_browser_tools
from .session_manager import BrowserSessionManager, get_session
from .tools.filesystem import make_filesystem_tools
from .tools.code_runner import make_code_tools
from .tools.web_research import make_web_tools
from .utils.logger import get_logger

# Backward-compat alias used in health endpoint / shutdown
BrowserSingleton = BrowserSessionManager


logger = get_logger(__name__)


# ============================================================================
# Pydantic Request/Response Models
# ============================================================================

class AgentMessageRequest(BaseModel):
    """User message request to agent."""
    message: str = Field(..., min_length=1, description="User message")
    session_id: Optional[str] = Field(None, description="Optional session ID")


class AgentMessageResponse(BaseModel):
    """Agent response message."""
    reply: str = Field(..., description="Agent response (always conversational)")
    session_id: str = Field(..., description="Session ID for tracking")
    mode: Optional[str] = Field(None, description="Execution mode used")


class SessionInfoResponse(BaseModel):
    """Session information."""
    session_id: str
    current_mode: str
    conversation_turns: int
    pending_approval: bool
    timestamp: str


class ConversationHistoryResponse(BaseModel):
    """Conversation history."""
    session_id: str
    history: list = Field(..., description="List of conversation turns")
    count: int


class ResetResponse(BaseModel):
    """Reset session response."""
    status: str
    session_id: str
    message: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    llm_available: bool
    model: str           # backward compat alias for llm_model
    llm_model: str
    llm_base_url: str
    model_loaded: bool
    orchestrator_ready: bool
    browser_ready: bool
    timestamp: str


# ============================================================================
# Global State
# ============================================================================

# Per-session orchestrators
orchestrators: dict = {}


# ============================================================================
# FastAPI Application Setup
# ============================================================================

app = FastAPI(
    title="SANDHYA.AI - Autonomous Agent API",
    description="Fully autonomous general-purpose execution agent — browser, filesystem, code, and web research tools",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Global Exception Handler
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled errors.
    
    Returns structured JSON error response.
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "path": str(request.url),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    )


# ============================================================================
# Initialization
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize all components on server startup."""
    logger.info("=" * 70)
    logger.info("SANDHYA.AI AGENT SERVER STARTUP")
    logger.info("=" * 70)

    try:
        # Initialize LLM client with settings from .env
        logger.info("[1/5] Initializing LLM client...")
        logger.info(f"  Base URL: {settings.LLM_BASE_URL}")
        logger.info(f"  Model: {settings.LLM_MODEL}")
        
        llm_client = LLMClient(
            base_url=settings.LLM_BASE_URL,
            model=settings.LLM_MODEL,
            timeout=settings.LLM_TIMEOUT
        )

        # Check LLM health
        health = llm_client.health_check()
        if not health["available"]:
            logger.warning(
                f"⚠️  LM Studio not detected at {settings.LLM_BASE_URL}. "
                f"Error: {health.get('error', 'Unknown')}. "
                "Chat and planning will not work. Ensure LM Studio is running."
            )
        elif not health["model_loaded"]:
            logger.warning(
                f"⚠️  Model '{settings.LLM_MODEL}' not loaded in LM Studio. "
                "Please load the model in LM Studio."
            )
        else:
            logger.info(f"[OK] LLM client ready - Model '{settings.LLM_MODEL}' loaded")

        # Initialize browser controller
        logger.info("[2/5] Initializing browser controller...")
        browser_controller = BrowserController(
            headless=settings.BROWSER_HEADLESS,
            timeout_ms=settings.BROWSER_TIMEOUT_MS
        )
        logger.info("[OK] Browser controller initialized")

        # Initialize planner
        logger.info("[3/5] Initializing planner...")
        planner = Planner(llm_client)
        logger.info("[OK] Planner initialized")

        # Initialize executor
        logger.info("[4/5] Initializing executor...")
        executor = Executor(browser_controller)
        logger.info("[OK] Executor initialized")

        # Initialize autonomous agent controller
        logger.info("[5/5] Initializing autonomous agent controller...")
        autonomous_controller = AutonomousAgentController(
            browser_controller=browser_controller,
            executor=executor,
            llm_client=llm_client,
            max_iterations=10
        )
        logger.info("[OK] Autonomous controller initialized")

        # Store in app state for later access
        app.state.llm_client = llm_client
        app.state.browser_controller = browser_controller
        app.state.planner = planner
        app.state.executor = executor
        app.state.autonomous_controller = autonomous_controller

        # Register tools into the global ToolRegistry
        logger.info("[+] Registering tools into ToolRegistry...")
        for name, fn in make_browser_tools(browser_controller).items():
            tool_registry.register(name, fn)
        for name, fn in make_filesystem_tools().items():
            tool_registry.register(name, fn)
        for name, fn in make_code_tools().items():
            tool_registry.register(name, fn)
        for name, fn in make_web_tools().items():
            tool_registry.register(name, fn)
        logger.info(f"[OK] Tools registered: {tool_registry.available()}")

        logger.info("=" * 70)
        logger.info("[OK] SERVER STARTUP COMPLETE - ALL SYSTEMS READY")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"❌ STARTUP FAILED: {str(e)}", exc_info=True)
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on server shutdown."""
    logger.info("Server shutting down...")

    try:
        # Stop the persistent browser session (via BrowserSessionManager)
        await get_session().stop()
        logger.info("BrowserSessionManager stopped")
    except Exception as e:
        logger.error(f"Shutdown error (BrowserSessionManager): {e}")

    try:
        if hasattr(app.state, 'browser_controller'):
            await app.state.browser_controller.stop()
    except Exception as e:
        logger.error(f"Shutdown error (legacy browser_controller): {e}")

    logger.info("Server shutdown complete")


# ============================================================================
# Helper Functions
# ============================================================================

def _get_or_create_orchestrator(session_id: str) -> AgentOrchestrator:
    """
    Get existing orchestrator or create new one for session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        AgentOrchestrator instance
    """
    if session_id not in orchestrators:
        logger.info(f"Creating new orchestrator for session: {session_id}")
        orchestrators[session_id] = AgentOrchestrator(
            planner=app.state.planner,
            executor=app.state.executor,
            llm_client=app.state.llm_client,
            autonomous_controller=app.state.autonomous_controller,
            session_id=session_id
        )
    return orchestrators[session_id]


def _format_sse(event_type: str, content: str, is_final: bool = False) -> str:
    """
    Format message as Server-Sent Event (SSE).
    
    Args:
        event_type: Event type (status, response, error, complete)
        content: Event content
        is_final: Whether this is the final message
        
    Returns:
        Formatted SSE string
    """
    data = {
        "type": event_type,
        "content": content,
        "is_final": is_final
    }
    return f"data: {json.dumps(data)}\n\n"


# ============================================================================
# Health & Status Endpoints
# ============================================================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint with comprehensive status.
    
    Verifies:
    - LLM server reachability
    - Configured model availability
    - Orchestrator initialization
    
    Returns:
        Detailed health status
    """
    health_data = app.state.llm_client.health_check()

    status = "healthy" if health_data["available"] and health_data["model_loaded"] else "degraded"

    bc = getattr(app.state, "browser_controller", None)
    browser_ready = get_session().is_ready

    return HealthResponse(
        status=status,
        llm_available=health_data["available"],
        model=health_data["model_name"],
        llm_model=health_data["model_name"],
        llm_base_url=app.state.llm_client.base_url,
        model_loaded=health_data.get("model_loaded", False),
        orchestrator_ready=True,
        browser_ready=browser_ready,
        timestamp=datetime.utcnow().isoformat() + "Z"
    )


# ============================================================================
# Main Agent Endpoints
# ============================================================================

@app.post("/agent/message", response_model=AgentMessageResponse)
async def message_endpoint(request: AgentMessageRequest) -> AgentMessageResponse:
    """
    Main unified agent message endpoint.
    
    Routes request through AgentOrchestrator which internally decides:
      - Chat: Conversational LLM response
      - Controlled Automation: Plan generation + approval request
      - Autonomous Goal: Goal-driven reasoning loop
    
    The routing is automatic based on message intent.
    
    Args:
        request: User message request
        
    Returns:
        Conversational agent response
        
    Raises:
        HTTPException: On processing errors
    """
    start_time = time.time()
    message = request.message.strip()
    session_id = request.session_id or str(uuid.uuid4())

    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    logger.info(f"[{session_id}] Message: {message[:80]}...")

    try:
        # Get or create orchestrator for session
        orchestrator = _get_or_create_orchestrator(session_id)

        # Process message through orchestrator
        reply = await orchestrator.handle_message(message)

        # Determine mode used
        mode = orchestrator.current_mode.value
        
        execution_time = time.time() - start_time

        logger.info(f"[{session_id}] \u2713 Mode: {mode}, Reply: {len(reply)} chars, Time: {execution_time:.2f}s")

        return AgentMessageResponse(
            reply=reply,
            session_id=session_id,
            mode=mode
        )

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"[{session_id}] \u2717 Error after {execution_time:.2f}s: {str(e)}", exc_info=True)
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "message": str(e),
                "session_id": session_id
            }
        )


@app.get("/agent/history", response_model=ConversationHistoryResponse)
async def get_history(session_id: str) -> ConversationHistoryResponse:
    """
    Retrieve conversation history for a session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Conversation history with metadata
        
    Raises:
        HTTPException: If session not found
    """
    if session_id not in orchestrators:
        raise HTTPException(status_code=404, detail="Session not found")

    orchestrator = orchestrators[session_id]
    history = orchestrator.get_conversation_history()

    logger.info(f"[{session_id}] History retrieved: {len(history)} turns")

    return ConversationHistoryResponse(
        session_id=session_id,
        history=history,
        count=len(history)
    )


@app.get("/agent/session", response_model=SessionInfoResponse)
async def session_info(session_id: str) -> SessionInfoResponse:
    """
    Get session information and state.
    
    Useful for debugging and frontend state management.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Current session state information
        
    Raises:
        HTTPException: If session not found
    """
    if session_id not in orchestrators:
        raise HTTPException(status_code=404, detail="Session not found")

    orchestrator = orchestrators[session_id]
    info = orchestrator.get_session_info()

    logger.info(f"[{session_id}] Session info retrieved")

    return SessionInfoResponse(**info)


@app.post("/agent/reset", response_model=ResetResponse)
async def reset_session(session_id: str) -> ResetResponse:
    """
    Reset session state (clear history, pending plans, memory).
    
    Args:
        session_id: Session identifier
        
    Returns:
        Confirmation of reset
        
    Raises:
        HTTPException: If session not found
    """
    if session_id not in orchestrators:
        raise HTTPException(status_code=404, detail="Session not found")

    orchestrator = orchestrators[session_id]
    orchestrator.clear_state()

    logger.info(f"[{session_id}] Session reset")

    return ResetResponse(
        status="success",
        session_id=session_id,
        message="Session state cleared. Ready for new conversation."
    )


# ============================================================================
# Streaming Endpoints (for real-time frontend updates)
# ============================================================================

@app.post("/agent/message/stream")
async def message_stream_endpoint(request: AgentMessageRequest):
    """
    Streaming variant of message endpoint using Server-Sent Events (SSE).
    
    Sends real-time status updates during execution.
    
    Useful for:
      - Long-running autonomous goals
      - User experience during automation
      - Frontend progress indication
    
    Args:
        request: User message request
        
    Returns:
        StreamingResponse with SSE updates
    """
    message = request.message.strip()
    session_id = request.session_id or str(uuid.uuid4())

    logger.info(f"[{session_id}] Stream started: {message[:80]}...")

    async def generate():
        try:
            orchestrator = _get_or_create_orchestrator(session_id)

            yield _format_sse("status", "Processing your request...")

            # Process through orchestrator
            reply = await orchestrator.handle_message(message)

            # Send response
            yield _format_sse("response", reply, is_final=True)

        except Exception as e:
            logger.error(f"[{session_id}] Streaming error: {str(e)}")
            yield _format_sse(
                "error",
                f"Error: {str(e)}",
                is_final=True
            )

    return StreamingResponse(generate(), media_type="text/event-stream")


# ============================================================================
# Browser Control Endpoints (optional manual control)
# ============================================================================

@app.post("/browser/start")
async def start_browser():
    """Manually start browser (optional)."""
    try:
        if not app.state.browser_controller.page:
            await app.state.browser_controller.start()
        logger.info("Browser started")
        return {"status": "Browser started"}
    except Exception as e:
        logger.error(f"Failed to start browser: {e}")
        return {"status": "error", "detail": str(e)}


@app.post("/browser/stop")
async def stop_browser():
    """Manually stop browser (optional)."""
    try:
        await app.state.browser_controller.stop()
        logger.info("Browser stopped")
        return {"status": "Browser stopped"}
    except Exception as e:
        logger.error(f"Failed to stop browser: {e}")
        return {"status": "error", "detail": str(e)}


# ============================================================================
# Cleanup Endpoints
# ============================================================================

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """
    Delete session and free resources.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Confirmation of deletion
    """
    if session_id not in orchestrators:
        raise HTTPException(status_code=404, detail="Session not found")

    del orchestrators[session_id]
    logger.info(f"Session deleted: {session_id}")

    return {"status": "Session deleted"}


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    logger.info("Starting Trial Automation Agent API server...")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_config=None  # Use logger configuration from utils.logger
    )
