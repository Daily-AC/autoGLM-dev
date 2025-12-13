"""
AutoGLM Web Console - Main FastAPI Application

This is the main entry point for the web console.
All business logic has been refactored into the web/ package.
"""

import os
import sys
import threading
import webbrowser
from typing import List
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

# Ensure modules are accessible
sys.path.append(os.getcwd())

# Import refactored modules
from web.state import app_state, QueueLogger
from web.models import Profile, ChatRequest
from web.profiles import load_profiles, save_profiles, get_active_profile
from web.screen import video_stream_generator
from web.agent_runner import start_task, stop_task, reset_agent, run_agent_task
from web.services import status_monitor_loop
from web.control import (
    TapRequest, SwipeRequest, InputRequest, KeyRequest,
    handle_tap, handle_swipe, handle_input, handle_key
)

# Import check functions from main
from main import check_system_requirements, check_model_api


# ============================================================================
# Application Lifecycle
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    print("--- AutoGLM Web Console Starting ---")
    
    # Redirect stdout to capture logs
    sys.stdout = QueueLogger(app_state)
    
    # Start background status monitor
    monitor_thread = threading.Thread(
        target=status_monitor_loop,
        args=(check_system_requirements, check_model_api),
        daemon=True
    )
    monitor_thread.start()
    
    yield
    
    # Cleanup
    sys.stdout = sys.__stdout__
    print("--- AutoGLM Web Console Stopped ---")


app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="web/templates")


# ============================================================================
# Page Routes
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the main console page."""
    return templates.TemplateResponse("index.html", {"request": request})


# ============================================================================
# Screen Streaming
# ============================================================================

@app.get("/api/screen/stream")
async def screen_stream():
    """Stream device screen as MJPEG."""
    return StreamingResponse(
        video_stream_generator(), 
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


# ============================================================================
# Profile Management
# ============================================================================

@app.get("/api/profiles")
async def get_profiles():
    """Get all saved profiles."""
    return load_profiles()


@app.post("/api/profiles")
async def update_profiles(profiles: List[Profile]):
    """Update and save profiles."""
    data = [p.dict() for p in profiles]
    save_profiles(data)
    
    # Force API status reset and agent re-init on next request
    app_state.status_api = None
    app_state.agent = None
    
    return {"status": "ok"}


# ============================================================================
# Status API
# ============================================================================

@app.get("/api/status")
async def check_status():
    """Get current system status (cached)."""
    active = get_active_profile()
    return {
        "adb": app_state.status_adb,
        "api": app_state.status_api,
        "agent": app_state.status_agent,
        "active_profile": active["name"] if active else "None"
    }


# ============================================================================
# Chat / Task API
# ============================================================================

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Start a new agent task (async version)."""
    import asyncio
    
    task_id, error = start_task(request.task)
    
    if error:
        return {"status": "error", "message": error}
    
    # Run task as async background task (non-blocking)
    asyncio.create_task(run_agent_task(request.task, task_id))
    return {"status": "accepted", "task_id": task_id}


@app.delete("/api/chat/stop")
async def api_stop_chat():
    """Stop the current running task."""
    if stop_task():
        return {"status": "stopped"}
    return {"status": "ignored"}


@app.post("/api/chat/continue")
async def api_continue_chat():
    """Continue a failed task from where it left off."""
    import asyncio
    
    if not app_state.agent:
        return {"status": "error", "message": "No agent to continue"}
    
    # Agent wasn't reset on failure, so context is preserved
    task_id = str(__import__('uuid').uuid4())
    app_state.current_task_id = task_id
    
    # Continue task (step without new prompt uses existing context)
    asyncio.create_task(run_agent_task("继续", task_id))
    return {"status": "continuing", "task_id": task_id}


@app.post("/api/chat/reset")
async def api_reset_chat():
    """Reset the agent completely."""
    try:
        reset_agent()
        return {"status": "reset"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/takeover_confirm")
async def api_takeover_confirm():
    """User confirms they have completed takeover operation."""
    app_state.takeover_confirmed = True
    return {"status": "confirmed"}


# ============================================================================
# Logs API
# ============================================================================

@app.get("/api/logs")
async def get_logs(since: int = 0):
    """Get logs since the specified cursor position."""
    current_len = len(app_state.logs)
    if since >= current_len:
        return {"logs": [], "next_cursor": current_len}
    return {
        "logs": app_state.logs[since:],
        "next_cursor": current_len
    }


# ============================================================================
# Remote Control API
# ============================================================================

@app.post("/api/control/tap")
async def api_control_tap(req: TapRequest):
    """Handle tap control request."""
    return await handle_tap(req)


@app.post("/api/control/swipe")
async def api_control_swipe(req: SwipeRequest):
    """Handle swipe control request."""
    return await handle_swipe(req)


@app.post("/api/control/input")
async def api_control_input(req: InputRequest):
    """Handle input control request."""
    return await handle_input(req)


@app.post("/api/control/key")
async def api_control_key(req: KeyRequest):
    """Handle key event control request."""
    return await handle_key(req)


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Open browser after server starts
    threading.Timer(1.5, lambda: webbrowser.open("http://localhost:8000")).start()
    
    # Start server
    uvicorn.run(app, host="0.0.0.0", port=8000)
