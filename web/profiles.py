"""Profile management for model configurations."""

import os
import json
from typing import List, Dict, Optional

from dotenv import load_dotenv


PROFILES_FILE = "profiles.json"


def load_profiles() -> List[Dict]:
    """
    Load profiles from JSON file, or create defaults from .env.
    
    Returns:
        List of profile dictionaries.
    """
    if not os.path.exists(PROFILES_FILE):
        load_dotenv()
        defaults = [{
            "name": "Default (.env)",
            "provider": "Anthropic" if "claude" in os.getenv("PHONE_AGENT_MODEL", "").lower() else "OpenAI",
            "base_url": os.getenv("PHONE_AGENT_BASE_URL", "https://api.openai.com/v1"),
            "api_key": os.getenv("PHONE_AGENT_API_KEY", ""),
            "model": os.getenv("PHONE_AGENT_MODEL", "gpt-4o"),
            "is_active": True
        }]
        save_profiles(defaults)
        return defaults
    
    try:
        with open(PROFILES_FILE, "r") as f:
            data = json.load(f)
            # Migration: Ensure provider exists
            for p in data:
                if "provider" not in p:
                    p["provider"] = "Anthropic" if "claude" in p.get("model", "").lower() else "OpenAI"
            return data
    except Exception:
        return []


def save_profiles(profiles: List[Dict]) -> None:
    """
    Save profiles to JSON file.
    
    Args:
        profiles: List of profile dictionaries to save.
    """
    with open(PROFILES_FILE, "w") as f:
        json.dump(profiles, f, indent=2)


def get_active_profile() -> Optional[Dict]:
    """
    Get the currently active profile.
    
    Returns:
        Active profile dict, or first profile if none active, or None if empty.
    """
    profiles = load_profiles()
    for p in profiles:
        if p.get("is_active"):
            return p
    return profiles[0] if profiles else None
