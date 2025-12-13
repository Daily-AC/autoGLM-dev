"""
Remote control logic for Web UI.
Handles coordinate scaling and device interaction.
"""

from typing import Tuple
from pydantic import BaseModel

from phone_agent.adb import async_tap, async_swipe
from phone_agent.adb.input import async_type_text, async_input_keyevent
from web.state import app_state


# =============================================================================
# Request Models
# =============================================================================

class TapRequest(BaseModel):
    x: float  # Normalized 0.0 - 1.0
    y: float  # Normalized 0.0 - 1.0


class SwipeRequest(BaseModel):
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    duration: int = 500  # ms


class InputRequest(BaseModel):
    text: str


class KeyRequest(BaseModel):
    keycode: int | str


# =============================================================================
# Logic
# =============================================================================

def _scale_coordinates(x: float, y: float) -> Tuple[int, int]:
    """
    Convert normalized coordinates (0.0-1.0) to device coordinates.
    Uses app_state.original_screen_size for the real device resolution.
    """
    if not app_state.original_screen_size:
        # Fallback if unknown (should not happen if stream is running)
        width, height = 1080, 2400
    else:
        width, height = app_state.original_screen_size
        
    device_x = int(x * width)
    device_y = int(y * height)
    
    # Clamp to screen bounds
    device_x = max(0, min(device_x, width))
    device_y = max(0, min(device_y, height))
    
    return device_x, device_y


async def handle_tap(req: TapRequest) -> dict:
    """Handle tap request from web UI."""
    # Ensure there is an active device from profile or auto-detect
    # For now, async commands usually auto-detect if no device_id passed
    
    x, y = _scale_coordinates(req.x, req.y)
    print(f"Control: Tap at ({x}, {y})")
    
    await async_tap(x, y)
    return {"status": "ok", "x": x, "y": y}


async def handle_swipe(req: SwipeRequest) -> dict:
    """Handle swipe request."""
    x1, y1 = _scale_coordinates(req.start_x, req.start_y)
    x2, y2 = _scale_coordinates(req.end_x, req.end_y)
    
    print(f"Control: Swipe ({x1}, {y1}) -> ({x2}, {y2})")
    
    await async_swipe(x1, y1, x2, y2, req.duration)
    return {"status": "ok"}


async def handle_input(req: InputRequest) -> dict:
    """Handle text input."""
    print(f"Control: Type text '{req.text}'")
    
    # 1. Ensure ADB Keyboard is active (async check/set)
    from phone_agent.adb.input import async_detect_and_set_adb_keyboard, async_input_keyevent
    await async_detect_and_set_adb_keyboard()
    
    # 2. Send text
    await async_type_text(req.text)
    
    # 3. Optional: Send ENTER to submit (simulates clicking 'Send')
    # This is often expected behavior in chat apps
    await async_input_keyevent(66) # KEYCODE_ENTER
    
    return {"status": "ok"}


async def handle_key(req: KeyRequest) -> dict:
    """Handle key event."""
    print(f"Control: Key event {req.keycode}")
    await async_input_keyevent(req.keycode)
    return {"status": "ok"}
