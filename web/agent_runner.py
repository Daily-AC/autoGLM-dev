"""Agent task execution and lifecycle management (Async version)."""

import asyncio
import sys
import uuid
from typing import Optional

from web.state import app_state
from web.profiles import get_active_profile
from phone_agent import AsyncPhoneAgent, PhoneAgent, TaskCancelledException, get_logger
from phone_agent.model import ModelConfig
from phone_agent.agent import AgentConfig

# Module logger
logger = get_logger("runner")


async def web_takeover_callback(message: str) -> None:
    """
    Handle takeover request from agent by waiting for user confirmation via Web UI.
    """
    from phone_agent.logging import LogLevel
    
    logger.warn("Takeover requested", message=message)
    # Log a specific event for frontend to show a modal/button
    logger.log(LogLevel.AGENT, f"Manual Intervention Required: {message}", tag="TAKEOVER")
    
    app_state.takeover_confirmed = False
    
    # Wait for confirmation
    while not app_state.takeover_confirmed:
        # Check if task is cancelled/stopped
        if app_state.status_agent != "busy":
            logger.warn("Takeover cancelled because task stopped")
            break
        await asyncio.sleep(0.5)
    
    if app_state.takeover_confirmed:
        logger.info("Takeover confirmed by user")


def init_agent(use_async: bool = True) -> Optional[str]:
    """
    Initialize or reinitialize the PhoneAgent with active profile.
    
    Args:
        use_async: If True, use AsyncPhoneAgent. If False, use sync PhoneAgent.
    
    Returns:
        None on success, error message on failure.
    """
    profile = get_active_profile()
    if not profile:
        return "No active profile"
    
    try:
        logger.info("Initializing Agent", profile=profile['name'], async_mode=use_async)
        model_config = ModelConfig(
            base_url=profile["base_url"],
            api_key=profile["api_key"],
            model_name=profile["model"]
        )
        agent_config = AgentConfig()
        
        if use_async:
            app_state.agent = AsyncPhoneAgent(
                model_config, 
                agent_config,
                takeover_callback=web_takeover_callback
            )
        else:
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
    # Initialize agent if needed (use async by default)
    if not app_state.agent:
        error = init_agent(use_async=True)
        if error:
            return "", error
    
    # Clear old logs for new task
    app_state.json_logs.clear()
    
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
        app_state.status_agent = "ready"
        print(f"\n!!! USER STOPPED TASK - Cancellation requested !!!")
        return True
    return False


def reset_agent() -> None:
    """Reset the agent completely."""
    if app_state.agent:
        app_state.agent = None
    app_state.status_agent = "idle"
    print("!!! AGENT RESET !!!")


async def run_agent_task(task: str, task_id: str) -> None:
    """
    Execute an agent task asynchronously.
    
    This function uses AsyncPhoneAgent for non-blocking execution.
    
    Args:
        task: The task description.
        task_id: Unique identifier for this task.
    """
    logger.info("Task started (async)", task_id=task_id[:8], task=task)
    app_state.status_agent = "busy"
    
    def stream_screenshot_provider(device_id):
        """Callback to get screenshot from stream cache."""
        if app_state.latest_frame and app_state.original_screen_size:
            orig_w, orig_h = app_state.original_screen_size
            return (app_state.latest_frame, orig_w, orig_h)
        elif app_state.latest_frame:
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
            
            # First step (async!)
            res = await app_state.agent.step(task)
            
            # Main execution loop
            while not res.finished and app_state.status_agent == "busy":
                # Check for preemption
                if app_state.current_task_id != task_id:
                    logger.warn("Task preempted by new task", task_id=task_id[:8])
                    break

                # Check cancellation
                if app_state.status_agent != "busy":
                    logger.cancelled("Task interrupted by user")
                    break
                
                # Yield to event loop (allow other tasks to run)
                await asyncio.sleep(0)
                    
                # Next step (async!)
                res = await app_state.agent.step()
                
                # Safety limit
                if app_state.agent.step_count > 100: 
                    logger.warn("Auto-stop: Too many steps")
                    break
            
            # Log final result
            if res.finished and app_state.current_task_id == task_id:
                # Check if it's a failure (action with _metadata="error")
                is_error = res.action and res.action.get("_metadata") == "error"
                
                if is_error:
                    logger.failed(res.message or "任务执行失败")
                    # Don't reset agent on failure - allow continue
                else:
                    logger.result(res.message or "任务完成")
                    app_state.agent.reset()
                
    except asyncio.CancelledError:
        logger.cancelled("Task cancelled")
    except TaskCancelledException as e:
        logger.cancelled(str(e))
    except Exception as e:
        logger.error("Task error", error=str(e))
        import traceback
        traceback.print_exc(file=sys.stdout)
    finally:
        # Always reset status when task ends
        app_state.status_agent = "ready"
        if app_state.current_task_id == task_id:
            app_state.current_task_id = None


# Legacy sync version for CLI compatibility
def run_agent_task_sync(task: str, task_id: str) -> None:
    """
    Execute an agent task synchronously (for CLI use).
    
    Uses the sync PhoneAgent.
    """
    # Re-init with sync agent if needed
    if app_state.agent is None or isinstance(app_state.agent, AsyncPhoneAgent):
        init_agent(use_async=False)
    
    logger.info("Task started (sync)", task_id=task_id[:8], task=task)
    app_state.status_agent = "busy"
    
    try:
        if app_state.agent:
            app_state.agent.reset()
            res = app_state.agent.step(task)
            
            while not res.finished and app_state.status_agent == "busy":
                if app_state.current_task_id != task_id:
                    break
                res = app_state.agent.step()
                if app_state.agent.step_count > 100: 
                    break
            
            if res.finished:
                logger.result(res.message or "Task Completed")
                app_state.agent.reset()
                
    except TaskCancelledException as e:
        logger.cancelled(str(e))
    except Exception as e:
        logger.error("Task error", error=str(e))
    finally:
        app_state.status_agent = "ready"
        if app_state.current_task_id == task_id:
            app_state.current_task_id = None

