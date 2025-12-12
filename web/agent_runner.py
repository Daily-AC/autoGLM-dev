"""Agent task execution and lifecycle management."""

import json
import sys
import uuid
from typing import Optional

from web.state import app_state
from web.profiles import get_active_profile
from phone_agent import PhoneAgent, TaskCancelledException, get_logger
from phone_agent.model import ModelConfig
from phone_agent.agent import AgentConfig

# Module logger
logger = get_logger("runner")


def init_agent() -> Optional[str]:
    """
    Initialize or reinitialize the PhoneAgent with active profile.
    
    Returns:
        None on success, error message on failure.
    """
    profile = get_active_profile()
    if not profile:
        return "No active profile"
    
    try:
        logger.info("Initializing Agent", profile=profile['name'])
        model_config = ModelConfig(
            base_url=profile["base_url"],
            api_key=profile["api_key"],
            model_name=profile["model"]
        )
        agent_config = AgentConfig()
        app_state.agent = PhoneAgent(model_config, agent_config)
        logger.info("Agent initialized successfully")
        return None
    except Exception as e:
        logger.error("Failed to init agent", error=str(e))
        return str(e)


def start_task(task: str) -> tuple[str, Optional[str]]:
    """
    Start a new agent task.
    
    Args:
        task: The task description.
        
    Returns:
        Tuple of (task_id, error_message). Error is None on success.
    """
    # Initialize agent if needed
    if not app_state.agent:
        error = init_agent()
        if error:
            return "", error
    
    task_id = str(uuid.uuid4())
    app_state.current_task_id = task_id
    return task_id, None


def stop_task() -> bool:
    """
    Stop the currently running task.
    
    Returns:
        True if a task was stopped, False otherwise.
    """
    if app_state.status_agent == "busy" and app_state.agent:
        app_state.agent.cancel()
        app_state.current_task_id = None
        app_state.status_agent = "ready"  # Reset to ready so new tasks can be sent
        print(f"\n!!! USER STOPPED TASK - Cancellation requested !!!")
        return True
    return False


def reset_agent() -> None:
    """Reset the agent completely."""
    if app_state.agent:
        app_state.agent = None
    app_state.status_agent = "idle"
    print("!!! AGENT RESET !!!")


def run_agent_task(task: str, task_id: str) -> None:
    """
    Execute an agent task in a background thread.
    
    This function is designed to be called from BackgroundTasks.
    It handles the full task lifecycle including cancellation.
    
    Args:
        task: The task description.
        task_id: Unique identifier for this task.
    """
    logger.info("Task started", task_id=task_id[:8], task=task)
    app_state.status_agent = "busy"
    
    def stream_screenshot_provider(device_id):
        """
        Callback to get screenshot from stream cache.
        
        Returns:
            Tuple of (PIL.Image, original_width, original_height) or None.
            The image may be resized for display, but original dimensions are
            provided for accurate coordinate mapping.
        """
        if app_state.latest_frame and app_state.original_screen_size:
            orig_w, orig_h = app_state.original_screen_size
            return (app_state.latest_frame, orig_w, orig_h)
        elif app_state.latest_frame:
            # Fallback: use frame size if original not available
            img = app_state.latest_frame
            return (img, img.width, img.height)
        return None

    try:
        if app_state.agent:
            # Inject screenshot provider
            if hasattr(app_state.agent, 'set_screenshot_provider'):
                app_state.agent.set_screenshot_provider(stream_screenshot_provider)
            
            logger.thought("Initializing task...")
            
            # Check if preempted before start
            if app_state.current_task_id != task_id:
                logger.warn("Task preempted before start", task_id=task_id[:8])
                return

            # Start with fresh state
            app_state.agent.reset()
            res = app_state.agent.step(task)
            
            # Main execution loop
            while not res.finished and app_state.status_agent == "busy":
                # Check for preemption
                if app_state.current_task_id != task_id:
                    logger.warn("Task preempted by new task", task_id=task_id[:8])
                    break

                # Note: Logging is already done inside agent.step() via logger.thought/action
                # Don't log here to avoid duplicates
                
                # Check cancellation
                if app_state.status_agent != "busy":
                    logger.cancelled("Task interrupted by user")
                    break
                    
                # Next step
                res = app_state.agent.step()
                
                # Safety limit
                if app_state.agent.step_count > 100: 
                    logger.warn("Auto-stop: Too many steps")
                    break
            
            # Log final result
            if res.finished and app_state.current_task_id == task_id:
                logger.result(res.message or "Task Completed")
                app_state.agent.reset()
                
    except TaskCancelledException as e:
        logger.cancelled(str(e))
    except Exception as e:
        logger.error("Task error", error=str(e))
        import traceback
        traceback.print_exc(file=sys.stdout)
    finally:
        # Always reset status when task ends (regardless of how it ended)
        # This ensures new tasks can always be sent
        app_state.status_agent = "ready"
        if app_state.current_task_id == task_id:
            app_state.current_task_id = None
