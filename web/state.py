"""Global application state management."""

import queue
import sys
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

from PIL import Image


# Constants
MAX_LOGS = 1000


@dataclass
class AppState:
    """
    Global application state container.
    
    Holds references to the agent, logs, and current status.
    Note: This is a singleton pattern - only one instance should exist.
    """
    agent: Any = None  # PhoneAgent instance
    log_queue: queue.Queue = field(default_factory=queue.Queue)
    logs: List[str] = field(default_factory=list)  # Console formatted logs
    json_logs: List[str] = field(default_factory=list)  # JSON formatted logs for frontend
    removed_log_count: int = 0  # Track how many logs were popped from the front
    current_profile: Optional[Dict] = None
    
    # Status State
    status_adb: bool = False
    status_api: Optional[bool] = None  # None means checking/unknown
    status_agent: str = "idle"  # idle | ready | busy
    current_task_id: Optional[str] = None  # Unique ID for the running task thread
    
    # Shared Frame Cache for Agent
    latest_frame: Optional[Image.Image] = None
    # Original screen size (width, height) before resize - needed for accurate coordinate mapping
    original_screen_size: Optional[tuple[int, int]] = None
    
    # Takeover confirmation flag - set to True when user clicks "继续执行" button
    takeover_confirmed: bool = False


class QueueLogger:
    """
    Log interceptor that captures stdout and stores in a queue.
    
    This allows the web console to display logs in real-time.
    """
    
    def __init__(self, state: AppState):
        self.state = state
    
    def write(self, text: str) -> None:
        if text.strip():
            # Filter out high-frequency polling noise from UI and Console
            noise_patterns = [
                "GET /api/logs",
                "GET /api/status", 
                "GET /api/screen/stream",
                "Gen: Yielded"
            ]
            if any(pattern in text for pattern in noise_patterns):
                return

            self.state.log_queue.put(text)
            self.state.logs.append(text)
            if len(self.state.logs) > MAX_LOGS:
                self.state.logs.pop(0)
            sys.__stdout__.write(text)
            sys.__stdout__.flush()

    def flush(self) -> None:
        sys.__stdout__.flush()


# Global singleton instance
app_state = AppState()
