"""Background services for the web console."""

import io
import contextlib
import time

from web.state import app_state
from web.profiles import get_active_profile


def status_monitor_loop(check_system_requirements, check_model_api) -> None:
    """
    Background service that periodically checks system status.
    
    Updates app_state with:
    - ADB connection status
    - Model API availability
    - Agent status
    
    Args:
        check_system_requirements: Function to check ADB/system status.
        check_model_api: Function to check model API connectivity.
    """
    while True:
        try:
            # Capture output to avoid spamming the main log
            f = io.StringIO()
            with contextlib.redirect_stdout(f):
                adb_ok = check_system_requirements()
            
            profile = get_active_profile()
            
            # Check API only if status is unknown (None)
            # This prevents rate limiting by avoiding repeated checks
            if app_state.status_api is None and profile:
                with contextlib.redirect_stdout(f):
                    try:
                        api_ok = check_model_api(
                            profile["base_url"], 
                            profile["model"], 
                            profile["api_key"]
                        )
                        app_state.status_api = api_ok
                    except Exception:
                        app_state.status_api = False
            
            # Update State
            app_state.status_adb = adb_ok
            # app_state.status_api is updated conditionally above
            
            # Determine Agent Status
            if app_state.agent:
                if app_state.status_agent != "busy":
                    app_state.status_agent = "ready"
            else:
                app_state.status_agent = "idle"
                
        except Exception as e:
            print(f"Monitor Error: {e}")
            
        time.sleep(10)  # Check every 10s
