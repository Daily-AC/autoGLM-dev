"""Main PhoneAgent class for orchestrating phone automation."""

import json
import threading
import traceback
from dataclasses import dataclass
from typing import Any, Callable

from phone_agent.actions import ActionHandler
from phone_agent.actions.handler import do, finish, parse_action
from phone_agent.adb import get_current_app, get_screenshot
from phone_agent.config import get_messages, get_system_prompt
from phone_agent.model import ModelClient, ModelConfig
from phone_agent.model.client import MessageBuilder
from phone_agent.logging import get_logger

# Module logger
logger = get_logger("agent")


class CancellationToken:
    """
    Thread-safe cancellation token for stopping agent tasks.
    
    Usage:
        token = CancellationToken()
        
        # In worker thread:
        if token.is_cancelled:
            raise TaskCancelledException()
        
        # In main thread:
        token.cancel()
    """
    
    def __init__(self):
        self._cancelled = threading.Event()
    
    def cancel(self):
        """Request cancellation."""
        self._cancelled.set()
    
    @property
    def is_cancelled(self) -> bool:
        """Check if cancellation was requested."""
        return self._cancelled.is_set()
    
    def reset(self):
        """Reset the token for reuse."""
        self._cancelled.clear()
    
    def raise_if_cancelled(self, message: str = "Task cancelled by user"):
        """Raise TaskCancelledException if cancelled."""
        if self.is_cancelled:
            raise TaskCancelledException(message)


class TaskCancelledException(Exception):
    """Exception raised when a task is cancelled."""
    pass


@dataclass
class AgentConfig:
    """Configuration for the PhoneAgent."""

    max_steps: int = 100
    device_id: str | None = None
    lang: str = "cn"
    system_prompt: str | None = None
    verbose: bool = True
    # Context trimming settings
    max_context_messages: int = 10  # Maximum number of messages to keep (excluding system)
    remove_old_images: bool = True  # Remove images from old messages to save tokens

    def __post_init__(self):
        if self.system_prompt is None:
            self.system_prompt = get_system_prompt(self.lang)


@dataclass
class StepResult:
    """Result of a single agent step."""

    success: bool
    finished: bool
    action: dict[str, Any] | None
    thinking: str
    message: str | None = None


class PhoneAgent:
    """
    AI-powered agent for automating Android phone interactions.

    The agent uses a vision-language model to understand screen content
    and decide on actions to complete user tasks.

    Args:
        model_config: Configuration for the AI model.
        agent_config: Configuration for the agent behavior.
        confirmation_callback: Optional callback for sensitive action confirmation.
        takeover_callback: Optional callback for takeover requests.

    Example:
        >>> from phone_agent import PhoneAgent
        >>> from phone_agent.model import ModelConfig
        >>>
        >>> model_config = ModelConfig(base_url="http://localhost:8000/v1")
        >>> agent = PhoneAgent(model_config)
        >>> agent.run("Open WeChat and send a message to John")
    """

    def __init__(
        self,
        model_config: ModelConfig | None = None,
        agent_config: AgentConfig | None = None,
        confirmation_callback: Callable[[str], bool] | None = None,
        takeover_callback: Callable[[str], None] | None = None,
    ):
        self.model_config = model_config or ModelConfig()
        self.agent_config = agent_config or AgentConfig()

        self.model_client = ModelClient(self.model_config)
        self.action_handler = ActionHandler(
            device_id=self.agent_config.device_id,
            confirmation_callback=confirmation_callback,
            takeover_callback=takeover_callback,
        )

        self._context: list[dict[str, Any]] = []
        self._step_count = 0
        self._screenshot_provider: Callable[[str], Any] | None = None
        self._cancellation_token = CancellationToken()

    def set_screenshot_provider(self, provider: Callable[[str], Any]):
        """Set a provider to get screenshots potentially from a video stream."""
        self._screenshot_provider = provider

    def run(self, task: str) -> str:
        """
        Run the agent to complete a task.

        Args:
            task: Natural language description of the task.

        Returns:
            Final message from the agent.
        """
        self._context = []
        self._step_count = 0

        # First step with user prompt
        result = self._execute_step(task, is_first=True)

        if result.finished:
            return result.message or "Task completed"

        # Continue until finished or max steps reached
        while self._step_count < self.agent_config.max_steps:
            result = self._execute_step(is_first=False)

            if result.finished:
                return result.message or "Task completed"

        return "Max steps reached"

    def step(self, task: str | None = None) -> StepResult:
        """
        Execute a single step of the agent.

        Useful for manual control or debugging.

        Args:
            task: Task description (only needed for first step).

        Returns:
            StepResult with step details.
        """
        is_first = len(self._context) == 0

        if is_first and not task:
            raise ValueError("Task is required for the first step")

        return self._execute_step(task, is_first)

    def reset(self) -> None:
        """Reset the agent state for a new task."""
        self._context = []
        self._step_count = 0
        self._cancellation_token.reset()
    
    def _trim_context(self) -> None:
        """
        Trim the context to save tokens and prevent unbounded growth.
        
        Applies two strategies:
        1. Remove images from old messages (keep only latest)
        2. Limit total message count
        """
        if len(self._context) <= 1:
            return
        
        # Strategy 1: Remove images from old messages (keep system + latest user msg)
        if self.agent_config.remove_old_images:
            for i, msg in enumerate(self._context):
                # Skip system message (index 0) and the last user message
                if i == 0 or i >= len(self._context) - 2:
                    continue
                MessageBuilder.remove_images_from_message(msg)
        
        # Strategy 2: Limit message count (keep system + last N)
        max_msgs = self.agent_config.max_context_messages
        if len(self._context) > max_msgs + 1:  # +1 for system message
            # Keep: system message + last max_msgs messages
            self._context = [self._context[0]] + self._context[-(max_msgs):]
            logger.debug("Context trimmed", kept_messages=len(self._context))
    
    def cancel(self) -> None:
        """Cancel the current running task."""
        self._cancellation_token.cancel()
    
    @property
    def is_cancelled(self) -> bool:
        """Check if current task is cancelled."""
        return self._cancellation_token.is_cancelled

    def _execute_step(
        self, user_prompt: str | None = None, is_first: bool = False
    ) -> StepResult:
        """Execute a single step of the agent loop."""
        # Check for cancellation before starting
        self._cancellation_token.raise_if_cancelled()
        
        self._step_count += 1

        # Capture current screen state
        logger.debug("Getting screenshot", step=self._step_count)
        screenshot = None
        if self._screenshot_provider:
            result = self._screenshot_provider(self.agent_config.device_id)
            if result:
                # Provider returns (img, original_width, original_height)
                if isinstance(result, tuple) and len(result) == 3:
                    img, orig_width, orig_height = result
                    logger.debug("Screenshot from provider", display=str(img.size), original=f"{orig_width}x{orig_height}")
                else:
                    # Fallback for old-style provider returning just image
                    img = result
                    orig_width, orig_height = img.width, img.height
                    logger.debug("Screenshot from provider (legacy)", size=str(img.size))
                
                # Convert PIL to Screenshot object
                from phone_agent.adb.screenshot import Screenshot
                import io, base64
                buf = io.BytesIO()
                img.save(buf, format='PNG')
                b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
                # ⚠️ Use ORIGINAL screen size for coordinate mapping, not resized image size
                screenshot = Screenshot(base64_data=b64, width=orig_width, height=orig_height, is_sensitive=False)
        
        if not screenshot:
             logger.debug("Screenshot from ADB (fallback)")
             screenshot = get_screenshot(self.agent_config.device_id)
        
        logger.debug("Screenshot ready", width=screenshot.width, height=screenshot.height)
        current_app = get_current_app(self.agent_config.device_id)

        # Build messages
        if is_first:
            self._context.append(
                MessageBuilder.create_system_message(self.agent_config.system_prompt)
            )

            screen_info = MessageBuilder.build_screen_info(current_app)
            text_content = f"{user_prompt}\n\n{screen_info}"

            self._context.append(
                MessageBuilder.create_user_message(
                    text=text_content, image_base64=screenshot.base64_data
                )
            )
        else:
            screen_info = MessageBuilder.build_screen_info(current_app)
            text_content = f"** Screen Info **\n\n{screen_info}"

            self._context.append(
                MessageBuilder.create_user_message(
                    text=text_content, image_base64=screenshot.base64_data
                )
            )

        # Check for cancellation before model call (expensive operation)
        self._cancellation_token.raise_if_cancelled()
        
        # Get model response
        try:
            logger.debug("Calling model client")
            response = self.model_client.request(self._context)
            logger.debug("Model responded")
        except Exception as e:
            if self.agent_config.verbose:
                traceback.print_exc()
            return StepResult(
                success=False,
                finished=True,
                action=None,
                thinking="",
                message=f"Model error: {e}",
            )

        # Parse action from response
        try:
            if not response.action: 
                raise ValueError("Empty action from model")
            action = parse_action(response.action)
        except ValueError:
            if self.agent_config.verbose:
                logger.warn("Parsing failed or empty action", raw=response.raw_content[:200] if response.raw_content else "")
            # Don't finish immediately - let agent_runner decide whether to retry
            # Track consecutive failures to prevent infinite loop
            self._consecutive_failures = getattr(self, '_consecutive_failures', 0) + 1
            if self._consecutive_failures >= 3:
                # Too many consecutive failures, stop
                return StepResult(
                    success=False,
                    finished=True,
                    action=None,
                    thinking=response.thinking,
                    message=f"Model failed to generate valid actions after {self._consecutive_failures} attempts.",
                )
            else:
                # Return failure but allow retry
                return StepResult(
                    success=False,
                    finished=False,  # Don't finish, let loop retry
                    action=None,
                    thinking=response.thinking,
                    message="Model returned empty response, will retry...",
                )

        if self.agent_config.verbose:
            # Log thinking process and action using structured logging
            logger.thought(response.thinking)
            logger.action(action.get("action", "unknown"), action)
        
        # Reset failure counter on success
        self._consecutive_failures = 0

        # Remove image from context to save space
        # self._context[-1] = MessageBuilder.remove_images_from_message(self._context[-1])

        # Check for cancellation before action execution
        self._cancellation_token.raise_if_cancelled()
        
        # Execute action
        try:
            logger.debug("Executing action handler")
            result = self.action_handler.execute(
                action, screenshot.width, screenshot.height
            )
            logger.debug("Action handler completed")
        except Exception as e:
            logger.error("Action handler exception", error=str(e))
            if self.agent_config.verbose:
                traceback.print_exc()
            result = self.action_handler.execute(
                finish(message=str(e)), screenshot.width, screenshot.height
            )

        # Add assistant response to context
        self._context.append(
            MessageBuilder.create_assistant_message(
                f"<think>{response.thinking}</think><answer>{response.action}</answer>"
            )
        )
        
        # Trim context to save tokens
        self._trim_context()

        # Check if finished
        finished = action.get("_metadata") == "finish" or result.should_finish

        if finished and self.agent_config.verbose:
            msgs = get_messages(self.agent_config.lang)
            logger.result(result.message or action.get('message', msgs['done']))

        return StepResult(
            success=result.success,
            finished=finished,
            action=action,
            thinking=response.thinking,
            message=result.message or action.get("message"),
        )

    @property
    def context(self) -> list[dict[str, Any]]:
        """Get the current conversation context."""
        return self._context.copy()

    @property
    def step_count(self) -> int:
        """Get the current step count."""
        return self._step_count


# =============================================================================
# Async Phone Agent
# =============================================================================

class AsyncPhoneAgent:
    """
    Async version of PhoneAgent for web applications.
    
    Uses AsyncModelClient for non-blocking API calls.
    All methods that involve I/O are async.
    
    Args:
        model_config: Configuration for the AI model.
        agent_config: Configuration for the agent behavior.
        confirmation_callback: Optional async callback for sensitive action confirmation.
        takeover_callback: Optional async callback for takeover requests.
    """
    
    def __init__(
        self,
        model_config: ModelConfig | None = None,
        agent_config: AgentConfig | None = None,
        confirmation_callback: Callable[[str], bool] | None = None,
        takeover_callback: Callable[[str], None] | None = None,
    ):
        from phone_agent.model import AsyncModelClient
        
        self.model_config = model_config or ModelConfig()
        self.agent_config = agent_config or AgentConfig()

        self.model_client = AsyncModelClient(self.model_config)
        self.action_handler = ActionHandler(
            device_id=self.agent_config.device_id,
            confirmation_callback=confirmation_callback,
            takeover_callback=takeover_callback,
        )

        self._context: list[dict[str, Any]] = []
        self._step_count = 0
        self._consecutive_failures = 0
        self._screenshot_provider: Callable[[str], Any] | None = None
        self._cancelled = False

    def set_screenshot_provider(self, provider: Callable[[str], Any]):
        """Set a provider to get screenshots potentially from a video stream."""
        self._screenshot_provider = provider

    async def run(self, task: str) -> str:
        """
        Run the agent to complete a task asynchronously.

        Args:
            task: Natural language description of the task.

        Returns:
            Final message from the agent.
        """
        self._context = []
        self._step_count = 0
        self._cancelled = False

        # First step with user prompt
        result = await self._execute_step(task, is_first=True)

        if result.finished:
            return result.message or "Task completed"

        # Continue until finished or max steps reached
        while self._step_count < self.agent_config.max_steps:
            if self._cancelled:
                return "Task cancelled"
                
            result = await self._execute_step(is_first=False)

            if result.finished:
                return result.message or "Task completed"

        return "Max steps reached"

    async def step(self, task: str | None = None) -> StepResult:
        """
        Execute a single step of the agent asynchronously.

        Args:
            task: Task description (only needed for first step).

        Returns:
            StepResult with step details.
        """
        is_first = len(self._context) == 0

        if is_first and not task:
            raise ValueError("Task is required for the first step")

        return await self._execute_step(task, is_first)

    def reset(self) -> None:
        """Reset the agent state for a new task."""
        self._context = []
        self._step_count = 0
        self._consecutive_failures = 0
        self._cancelled = False
    
    def cancel(self) -> None:
        """Cancel the current running task."""
        self._cancelled = True
    
    @property
    def is_cancelled(self) -> bool:
        """Check if current task is cancelled."""
        return self._cancelled

    async def _execute_step(
        self, user_prompt: str | None = None, is_first: bool = False
    ) -> StepResult:
        """Execute a single step of the agent loop asynchronously."""
        import asyncio
        
        # Check for cancellation
        if self._cancelled:
            raise asyncio.CancelledError("Task cancelled by user")
        
        self._step_count += 1

        # Capture current screen state
        logger.debug("Getting screenshot", step=self._step_count)
        screenshot = None
        if self._screenshot_provider:
            result = self._screenshot_provider(self.agent_config.device_id)
            if result:
                if isinstance(result, tuple) and len(result) == 3:
                    img, orig_width, orig_height = result
                else:
                    img = result
                    orig_width, orig_height = img.width, img.height
                
                from phone_agent.adb.screenshot import Screenshot
                import io, base64
                buf = io.BytesIO()
                img.save(buf, format='PNG')
                b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
                screenshot = Screenshot(base64_data=b64, width=orig_width, height=orig_height, is_sensitive=False)
        
        if not screenshot:
            screenshot = get_screenshot(self.agent_config.device_id)
        
        current_app = get_current_app(self.agent_config.device_id)

        # Build messages
        if is_first:
            self._context.append(
                MessageBuilder.create_system_message(self.agent_config.system_prompt)
            )
            screen_info = MessageBuilder.build_screen_info(current_app)
            text_content = f"{user_prompt}\n\n{screen_info}"
            self._context.append(
                MessageBuilder.create_user_message(
                    text=text_content, image_base64=screenshot.base64_data
                )
            )
        else:
            screen_info = MessageBuilder.build_screen_info(current_app)
            text_content = f"** Screen Info **\n\n{screen_info}"
            self._context.append(
                MessageBuilder.create_user_message(
                    text=text_content, image_base64=screenshot.base64_data
                )
            )

        # Check for cancellation before model call
        if self._cancelled:
            raise asyncio.CancelledError("Task cancelled by user")
        
        # Get model response (async!)
        try:
            logger.debug("Calling async model client")
            response = await self.model_client.request(self._context)
            logger.debug("Model responded")
        except Exception as e:
            if self.agent_config.verbose:
                traceback.print_exc()
            return StepResult(
                success=False,
                finished=True,
                action=None,
                thinking="",
                message=f"Model error: {e}",
            )

        # Parse action from response
        try:
            if not response.action: 
                raise ValueError("Empty action from model")
            action = parse_action(response.action)
        except ValueError:
            if self.agent_config.verbose:
                logger.warn("Parsing failed or empty action", raw=response.raw_content[:200] if response.raw_content else "")
            self._consecutive_failures += 1
            if self._consecutive_failures >= 3:
                return StepResult(
                    success=False,
                    finished=True,
                    action=None,
                    thinking=response.thinking,
                    message=f"Model failed to generate valid actions after {self._consecutive_failures} attempts.",
                )
            else:
                return StepResult(
                    success=False,
                    finished=False,
                    action=None,
                    thinking=response.thinking,
                    message="Model returned empty response, will retry...",
                )

        if self.agent_config.verbose:
            logger.thought(response.thinking)
            logger.action(action.get("action", "unknown"), action)
        
        self._consecutive_failures = 0

        # Check for cancellation before action execution
        if self._cancelled:
            raise asyncio.CancelledError("Task cancelled by user")
        
        # Execute action (sync for now, can be made async later)
        try:
            logger.debug("Executing action handler")
            result = self.action_handler.execute(
                action, screenshot.width, screenshot.height
            )
            logger.debug("Action handler completed")
        except Exception as e:
            logger.error("Action handler exception", error=str(e))
            if self.agent_config.verbose:
                traceback.print_exc()
            result = self.action_handler.execute(
                finish(message=str(e)), screenshot.width, screenshot.height
            )

        # Add assistant response to context
        self._context.append(
            MessageBuilder.create_assistant_message(
                f"<think>{response.thinking}</think><answer>{response.action}</answer>"
            )
        )
        
        # Trim context
        self._trim_context()

        # Check if finished
        finished = action.get("_metadata") == "finish" or result.should_finish

        if finished and self.agent_config.verbose:
            msgs = get_messages(self.agent_config.lang)
            logger.result(result.message or action.get('message', msgs['done']))

        return StepResult(
            success=result.success,
            finished=finished,
            action=action,
            thinking=response.thinking,
            message=result.message or action.get("message"),
        )

    def _trim_context(self) -> None:
        """Trim the context to save tokens."""
        if len(self._context) <= 1:
            return
        
        if self.agent_config.remove_old_images:
            for i, msg in enumerate(self._context):
                if i == 0 or i >= len(self._context) - 2:
                    continue
                MessageBuilder.remove_images_from_message(msg)
        
        max_msgs = self.agent_config.max_context_messages
        if len(self._context) > max_msgs + 1:
            self._context = [self._context[0]] + self._context[-(max_msgs):]

    @property
    def context(self) -> list[dict[str, Any]]:
        """Get the current conversation context."""
        return self._context.copy()

    @property
    def step_count(self) -> int:
        """Get the current step count."""
        return self._step_count

