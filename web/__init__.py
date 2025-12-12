"""Web package for AutoGLM Console."""

from web.state import app_state, AppState
from web.models import Profile, ChatRequest
from web.profiles import load_profiles, save_profiles, get_active_profile

__all__ = [
    "app_state",
    "AppState", 
    "Profile",
    "ChatRequest",
    "load_profiles",
    "save_profiles",
    "get_active_profile",
]
