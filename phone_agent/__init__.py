"""
Phone Agent - An AI-powered phone automation framework.

This package provides tools for automating Android phone interactions
using AI models for visual understanding and decision making.
"""

from phone_agent.agent import PhoneAgent, AsyncPhoneAgent, CancellationToken, AsyncCancellationToken, TaskCancelledException
from phone_agent.logging import get_logger, set_global_queue, StructuredLogger, LogLevel
from phone_agent.exceptions import (
    AutoGLMError,
    DeviceError,
    DeviceNotFoundError,
    DeviceDisconnectedError,
    ModelError,
    ModelRateLimitError,
    ModelInvalidResponseError,
    ActionError,
    ActionParseError,
    TaskCancelledError,
    is_retryable,
)
from phone_agent.retry import (
    retry_sync,
    retry_async,
    with_retry,
    ADBConnectionManager,
    CircuitBreaker,
    RetryConfig,
)

__version__ = "0.1.0"
__all__ = [
    # Core
    "PhoneAgent",
    "AsyncPhoneAgent",
    "CancellationToken",
    "AsyncCancellationToken",
    "TaskCancelledException",
    # Retry & Recovery
    "retry_sync",
    "retry_async",
    "with_retry",
    "ADBConnectionManager",
    "CircuitBreaker",
    "RetryConfig",
    "is_retryable",
    # Logging
    "get_logger",
    "set_global_queue",
    "StructuredLogger",
    "LogLevel",
    # Exceptions
    "AutoGLMError",
    "DeviceError",
    "DeviceNotFoundError",
    "DeviceDisconnectedError",
    "ModelError",
    "ModelRateLimitError",
    "ModelInvalidResponseError",
    "ActionError",
    "ActionParseError",
    "TaskCancelledError",
]

