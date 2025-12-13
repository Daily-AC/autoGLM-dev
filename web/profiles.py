"""Profile management for model configurations."""

import os
import json
from typing import List, Dict, Optional

# Remove load_dotenv, use settings instead
from phone_agent.config import settings


PROFILES_FILE = "profiles.json"


def load_profiles() -> List[Dict]:
    """
    Load profiles from JSON file, or create defaults from unified settings.
    
    Returns:
        List of profile dictionaries.
    """
    if not os.path.exists(PROFILES_FILE):
        # Create default profile from unified settings (config.yaml / env)
        defaults = [{
            "name": "Default (Config)",
            "provider": "Anthropic" if "claude" in settings.model.model_name.lower() else "OpenAI",
            "base_url": settings.model.base_url,
            "api_key": settings.model.api_key,
            "model": settings.model.model_name,
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
