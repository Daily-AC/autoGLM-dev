"""
Retry and recovery utilities for error handling.

This module provides decorators and utilities for:
- Exponential backoff retry for API calls
- Automatic ADB reconnection
- Error recovery with fallback strategies
"""

import asyncio
import functools
import time
from typing import Any, Callable, TypeVar, Optional
from dataclasses import dataclass

from phone_agent.exceptions import (
    AutoGLMError,
    DeviceDisconnectedError,
    ModelRateLimitError,
    ModelTimeoutError,
    ModelConnectionError,
    is_retryable,
)
from phone_agent.logging import get_logger

logger = get_logger("retry")

T = TypeVar("T")


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """
    Calculate delay with exponential backoff.
    
    Args:
        attempt: Current attempt number (0-indexed)
        config: Retry configuration
        
    Returns:
        Delay in seconds
    """
    import random
    
    delay = config.base_delay * (config.exponential_base ** attempt)
    delay = min(delay, config.max_delay)
    
    if config.jitter:
        # Add ±25% jitter to prevent thundering herd
        jitter_factor = 0.75 + random.random() * 0.5
        delay *= jitter_factor
    
    return delay


def retry_sync(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    retryable_exceptions: tuple = (Exception,),
):
    """
    Decorator for synchronous retry with exponential backoff.
    
    Args:
        max_attempts: Maximum number of attempts
        base_delay: Initial delay between retries
        retryable_exceptions: Tuple of exception types to retry
    """
    config = RetryConfig(max_attempts=max_attempts, base_delay=base_delay)
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    
                    # Check if error is marked as non-retryable
                    if isinstance(e, AutoGLMError) and not e.retryable:
                        raise
                    
                    if attempt < config.max_attempts - 1:
                        delay = calculate_delay(attempt, config)
                        logger.warn(
                            f"Retry attempt {attempt + 1}/{config.max_attempts}",
                            error=str(e),
                            delay=f"{delay:.1f}s"
                        )
                        time.sleep(delay)
            
            raise last_exception
        return wrapper
    return decorator


def retry_async(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    retryable_exceptions: tuple = (Exception,),
):
    """
    Decorator for async retry with exponential backoff.
    
    Args:
        max_attempts: Maximum number of attempts
        base_delay: Initial delay between retries
        retryable_exceptions: Tuple of exception types to retry
    """
    config = RetryConfig(max_attempts=max_attempts, base_delay=base_delay)
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    
                    # Check if error is marked as non-retryable
                    if isinstance(e, AutoGLMError) and not e.retryable:
                        raise
                    
                    # Special handling for rate limit
                    if isinstance(e, ModelRateLimitError):
                        delay = e.retry_after
                    else:
                        delay = calculate_delay(attempt, config)
                    
                    if attempt < config.max_attempts - 1:
                        logger.warn(
                            f"Retry attempt {attempt + 1}/{config.max_attempts}",
                            error=str(e),
                            delay=f"{delay:.1f}s"
                        )
                        await asyncio.sleep(delay)
            
            raise last_exception
        return wrapper
    return decorator


# =============================================================================
# ADB Reconnection
# =============================================================================

class ADBConnectionManager:
    """
    Manages ADB connection with automatic reconnection.
    
    Usage:
        manager = ADBConnectionManager(device_id="xxx")
        
        async with manager.ensure_connected():
            await async_tap(100, 200)
    """
    
    def __init__(
        self,
        device_id: str | None = None,
        max_reconnect_attempts: int = 3,
        reconnect_delay: float = 2.0,
    ):
        self.device_id = device_id
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_delay = reconnect_delay
        self._connected = False
    
    async def check_connection(self) -> bool:
        """Check if ADB connection is alive."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "adb", *([] if not self.device_id else ["-s", self.device_id]),
                "get-state",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)
            state = stdout.decode().strip()
            self._connected = state == "device"
            return self._connected
        except Exception:
            self._connected = False
            return False
    
    async def reconnect(self) -> bool:
        """
        Attempt to reconnect to the device.
        
        Returns:
            True if reconnection successful
        """
        logger.info("Attempting to reconnect to device", device_id=self.device_id)
        
        for attempt in range(self.max_reconnect_attempts):
            try:
                # First try adb reconnect
                proc = await asyncio.create_subprocess_exec(
                    "adb", *([] if not self.device_id else ["-s", self.device_id]),
                    "reconnect",
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await proc.wait()
                
                # Wait for device to come back
                await asyncio.sleep(self.reconnect_delay)
                
                # Check if reconnected
                if await self.check_connection():
                    logger.info("Device reconnected successfully")
                    return True
                
                # Exponential backoff
                delay = self.reconnect_delay * (2 ** attempt)
                logger.warn(
                    f"Reconnect attempt {attempt + 1}/{self.max_reconnect_attempts} failed",
                    delay=f"{delay:.1f}s"
                )
                await asyncio.sleep(delay)
                
            except Exception as e:
                logger.error("Reconnect error", error=str(e))
        
        logger.error("Failed to reconnect after all attempts")
        return False
    
    async def ensure_connected(self):
        """Context manager to ensure connection before operations."""
        return _ConnectionContext(self)


class _ConnectionContext:
    """Context manager for ADB connection."""
    
    def __init__(self, manager: ADBConnectionManager):
        self.manager = manager
    
    async def __aenter__(self):
        if not await self.manager.check_connection():
            if not await self.manager.reconnect():
                raise DeviceDisconnectedError(
                    "Failed to connect to device",
                    device_id=self.manager.device_id
                )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # If we got a device error, try to reconnect for next operation
        if exc_type and issubclass(exc_type, DeviceDisconnectedError):
            await self.manager.reconnect()
        return False  # Don't suppress the exception


# =============================================================================
# Retry wrapper for API calls
# =============================================================================

async def with_retry(
    coro_func: Callable[..., T],
    *args: Any,
    max_attempts: int = 3,
    **kwargs: Any
) -> T:
    """
    Execute coroutine with retry.
    
    Args:
        coro_func: Async function to call
        *args: Arguments to pass
        max_attempts: Maximum attempts
        **kwargs: Keyword arguments to pass
        
    Returns:
        Result of the coroutine
        
    Example:
        result = await with_retry(async_tap, 100, 200, max_attempts=3)
    """
    config = RetryConfig(max_attempts=max_attempts)
    last_exception = None
    
    for attempt in range(max_attempts):
        try:
            return await coro_func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            
            if not is_retryable(e) and isinstance(e, AutoGLMError):
                raise
            
            if attempt < max_attempts - 1:
                delay = calculate_delay(attempt, config)
                logger.warn(
                    f"Retry {attempt + 1}/{max_attempts}",
                    error=str(e),
                    delay=f"{delay:.1f}s"
                )
                await asyncio.sleep(delay)
    
    raise last_exception


# =============================================================================
# Circuit Breaker (for API protection)
# =============================================================================

class CircuitBreaker:
    """
    Circuit breaker pattern for API protection.
    
    Prevents repeated calls to a failing service.
    
    States:
        CLOSED: Normal operation
        OPEN: Failing, reject all calls
        HALF_OPEN: Testing if service recovered
    """
    
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        name: str = "default"
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        
        self._state = self.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
    
    @property
    def state(self) -> str:
        """Get current state, transitioning if needed."""
        if self._state == self.OPEN:
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = self.HALF_OPEN
                logger.info(f"Circuit breaker [{self.name}] half-open")
        return self._state
    
    def record_success(self):
        """Record a successful call."""
        self._failure_count = 0
        if self._state == self.HALF_OPEN:
            self._state = self.CLOSED
            logger.info(f"Circuit breaker [{self.name}] closed")
    
    def record_failure(self):
        """Record a failed call."""
        self._failure_count += 1
        self._last_failure_time = time.time()
        
        if self._failure_count >= self.failure_threshold:
            self._state = self.OPEN
            logger.warn(f"Circuit breaker [{self.name}] opened")
    
    def can_execute(self) -> bool:
        """Check if calls are allowed."""
        state = self.state
        if state == self.CLOSED:
            return True
        if state == self.HALF_OPEN:
            return True  # Allow test call
        return False
    
    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorator for protecting functions."""
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            if not self.can_execute():
                raise ModelConnectionError(
                    f"Circuit breaker [{self.name}] is open",
                    state=self._state
                )
            
            try:
                result = await func(*args, **kwargs)
                self.record_success()
                return result
            except Exception as e:
                self.record_failure()
                raise
        
        return wrapper
