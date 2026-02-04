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
from fastapi.staticfiles import StaticFiles

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

from phone_agent.adb import ADBConnection
from pydantic import BaseModel




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
    
    # Inject queue into structured logger
    from phone_agent.logging import set_global_queue
    set_global_queue(app_state.log_queue)
    
    yield
    
    # Cleanup
    sys.stdout = sys.__stdout__
    print("--- AutoGLM Web Console Stopped ---")


app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="web/templates")

# Mount static files (CSS, JS)
app.mount("/static", StaticFiles(directory="web/static"), name="static")


# ============================================================================
# Device Management API
# ============================================================================

class ConnectRequest(BaseModel):
    address: str

class SelectDeviceRequest(BaseModel):
    device_id: str

@app.get("/api/devices")
async def api_list_devices():
    """List all connected devices."""
    conn = ADBConnection()
    devices = conn.list_devices()
    
    # Convert to dict list
    device_list = []
    for d in devices:
        item = {
            "id": d.device_id,
            "status": d.status,
            "type": d.connection_type.value,
            "model": d.model,
            "selected": d.device_id == app_state.current_device_id
        }
        device_list.append(item)
        
    # Auto-select first device if none selected and devices exist
    if not app_state.current_device_id and device_list:
        # Prefer "device" status
        ready_devices = [d for d in device_list if d['status'] == 'device']
        if ready_devices:
            app_state.current_device_id = ready_devices[0]['id']
            ready_devices[0]['selected'] = True
    
    return device_list


@app.post("/api/device/connect")
async def api_connect_device(req: ConnectRequest):
    """Connect to a remote device."""
    conn = ADBConnection()
    success, msg = conn.connect(req.address)
    if success:
        return {"status": "ok", "message": msg}
    return {"status": "error", "message": msg}


@app.post("/api/device/disconnect")
async def api_disconnect_device(req: ConnectRequest):
    """Disconnect a remote device."""
    conn = ADBConnection()
    success, msg = conn.disconnect(req.address)
    if success:
        if app_state.current_device_id == req.address or app_state.current_device_id == f"{req.address}:5555":
            app_state.current_device_id = None
        return {"status": "ok", "message": msg}
    return {"status": "error", "message": msg}


@app.post("/api/device/select")
async def api_select_device(req: SelectDeviceRequest):
    """Set the active device for the agent."""
    app_state.current_device_id = req.device_id
    
    # If agent is initialized, we might need to re-init or update it
    # For now, just setting state is enough, it will be used on next task start
    # But if an agent is IDLE, we can force re-init now to be safe
    if app_state.status_agent == "idle" or app_state.status_agent == "ready":
         # Force re-init on next task
         app_state.agent = None
         
    return {"status": "ok", "selected": req.device_id}


# ============================================================================
# Page Routes
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, legacy: bool = False):
    """Serve the main console page.
    
    By default, serves the new refactored UI.
    Add ?legacy=true to use the old UI.
    """
    template_name = "index.html" if legacy else "index_new.html"
    return templates.TemplateResponse(template_name, {"request": request})


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
    """Get logs since the specified cursor position.
    
    This endpoint drains the log_queue (which contains JSON-formatted logs)
    and stores them in json_logs list for frontend consumption.
    """
    # Drain log_queue and append to json_logs
    while not app_state.log_queue.empty():
        try:
            json_log = app_state.log_queue.get_nowait()
            app_state.json_logs.append(json_log)
            # Keep list size manageable
            if len(app_state.json_logs) > 1000:
                app_state.json_logs.pop(0)
                app_state.removed_log_count += 1
        except:
            break
    
    current_total = app_state.removed_log_count + len(app_state.json_logs)
    
    # Calculate relative index in the sliding window
    relative_since = max(0, since - app_state.removed_log_count)
    
    return {
        "logs": app_state.json_logs[relative_since:],
        "next_cursor": current_total
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
