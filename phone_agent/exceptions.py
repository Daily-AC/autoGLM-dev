"""
Exception hierarchy for Open-AutoGLM.

This module defines a structured exception hierarchy that enables:
- Clear categorization of error types
- Retry/recovery decision support
- Rich error context for debugging
- User-friendly error messages

Usage:
    from phone_agent.exceptions import ModelRateLimitError
    
    raise ModelRateLimitError(
        "API rate limit exceeded",
        retry_after=30,
        model="gpt-4o"
    )
"""

from typing import Any, Optional


class AutoGLMError(Exception):
    """
    Base exception for all Open-AutoGLM errors.
    
    All custom exceptions inherit from this class, enabling
    catch-all handling when needed.
    
    Attributes:
        retryable: Whether this error can be retried
        user_message: User-friendly error description
        context: Additional context for debugging
    """
    
    retryable: bool = False
    user_message: str = "An error occurred"
    
    def __init__(self, message: str, **context: Any):
        super().__init__(message)
        self.context = context
    
    def __str__(self) -> str:
        base = super().__str__()
        if self.context:
            ctx_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{base} ({ctx_str})"
        return base


# ============================================================================
# Device Errors
# ============================================================================

class DeviceError(AutoGLMError):
    """Base class for device-related errors."""
    user_message = "Device connection error"


class DeviceNotFoundError(DeviceError):
    """
    No device found via ADB.
    
    This is typically not retryable - user needs to connect a device.
    """
    retryable = False
    user_message = "No Android device found. Please connect a device via USB or WiFi."


class DeviceDisconnectedError(DeviceError):
    """
    Device was connected but lost connection.
    
    This is retryable - the device might reconnect.
    """
    retryable = True
    user_message = "Device disconnected. Attempting to reconnect..."


class DeviceCommandError(DeviceError):
    """
    ADB command execution failed.
    
    This might be retryable depending on the command.
    """
    retryable = True
    user_message = "Device command failed"


# ============================================================================
# Model Errors
# ============================================================================

class ModelError(AutoGLMError):
    """Base class for AI model-related errors."""
    user_message = "AI model error"


class ModelConnectionError(ModelError):
    """
    Cannot connect to model API.
    
    Retryable with exponential backoff.
    """
    retryable = True
    user_message = "Cannot connect to AI service. Please check your network."


class ModelAuthenticationError(ModelError):
    """
    API key invalid or expired.
    
    Not retryable - user needs to fix credentials.
    """
    retryable = False
    user_message = "API authentication failed. Please check your API key."


class ModelRateLimitError(ModelError):
    """
    API rate limit exceeded.
    
    Retryable with exponential backoff.
    Use the retry_after context value if available.
    """
    retryable = True
    user_message = "API rate limit exceeded. Please wait and try again."
    
    @property
    def retry_after(self) -> float:
        """Suggested wait time in seconds."""
        return self.context.get("retry_after", 1.0)


class ModelInvalidResponseError(ModelError):
    """
    Model returned an unparseable response.
    
    Retryable - the model might return a valid response on retry.
    """
    retryable = True
    user_message = "AI returned an invalid response. Retrying..."


class ModelTimeoutError(ModelError):
    """
    Model request timed out.
    
    Retryable with exponential backoff.
    """
    retryable = True
    user_message = "AI request timed out. Please try again."


# ============================================================================
# Action Errors
# ============================================================================

class ActionError(AutoGLMError):
    """Base class for action-related errors."""
    user_message = "Action execution error"


class ActionParseError(ActionError):
    """
    Failed to parse action from model response.
    
    Not directly retryable - the model needs to generate a new response.
    """
    retryable = False
    user_message = "Failed to understand AI's action"


class ActionExecutionError(ActionError):
    """
    Action execution failed on device.
    
    Might be retryable depending on the action.
    """
    retryable = True
    user_message = "Failed to execute action on device"


class ActionSecurityError(ActionError):
    """
    Action was blocked for security reasons.
    
    Not retryable - requires user approval.
    """
    retryable = False
    user_message = "Action blocked for security. User approval required."


# ============================================================================
# Task Errors
# ============================================================================

class TaskCancelledError(AutoGLMError):
    """
    Task was cancelled by user.
    
    This is a clean cancellation, not an error condition.
    """
    retryable = False
    user_message = "Task cancelled by user"


class TaskTimeoutError(AutoGLMError):
    """
    Task exceeded maximum steps or time limit.
    
    Not retryable in current form - might need task redesign.
    """
    retryable = False
    user_message = "Task took too long and was stopped"


# ============================================================================
# Screenshot Errors
# ============================================================================

class ScreenshotError(DeviceError):
    """
    Failed to capture screenshot.
    
    Retryable - device might recover.
    """
    retryable = True
    user_message = "Failed to capture screen"


# ============================================================================
# Utility Functions
# ============================================================================

def is_retryable(error: Exception) -> bool:
    """
    Check if an exception is retryable.
    
    Args:
        error: The exception to check
        
    Returns:
        True if the error is an AutoGLMError with retryable=True
    """
    if isinstance(error, AutoGLMError):
        return error.retryable
    return False


def get_user_message(error: Exception) -> str:
    """
    Get a user-friendly error message.
    
    Args:
        error: The exception
        
    Returns:
        User-friendly message string
    """
    if isinstance(error, AutoGLMError):
        return error.user_message
    return str(error)
