"""
Unit tests for retry and recovery utilities.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock


class TestRetryDecorators:
    """Tests for retry decorators."""
    
    def test_retry_sync_success(self):
        """Test sync retry with immediate success."""
        from phone_agent import retry_sync
        
        call_count = 0
        
        @retry_sync(max_attempts=3)
        def func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = func()
        assert result == "success"
        assert call_count == 1
    
    def test_retry_sync_eventual_success(self):
        """Test sync retry with eventual success."""
        from phone_agent import retry_sync
        
        call_count = 0
        
        @retry_sync(max_attempts=3, base_delay=0.01)
        def func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Temporary error")
            return "success"
        
        result = func()
        assert result == "success"
        assert call_count == 2
    
    def test_retry_sync_max_attempts(self):
        """Test sync retry exhausts all attempts."""
        from phone_agent import retry_sync
        
        call_count = 0
        
        @retry_sync(max_attempts=3, base_delay=0.01)
        def func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")
        
        with pytest.raises(ValueError):
            func()
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_async_success(self):
        """Test async retry with immediate success."""
        from phone_agent import retry_async
        
        call_count = 0
        
        @retry_async(max_attempts=3)
        async def func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await func()
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_async_eventual_success(self):
        """Test async retry with eventual success."""
        from phone_agent import retry_async
        
        call_count = 0
        
        @retry_async(max_attempts=3, base_delay=0.01)
        async def func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Temporary error")
            return "success"
        
        result = await func()
        assert result == "success"
        assert call_count == 2


class TestWithRetry:
    """Tests for with_retry helper."""
    
    @pytest.mark.asyncio
    async def test_with_retry_success(self):
        """Test with_retry on success."""
        from phone_agent import with_retry
        
        async def success_func():
            return "done"
        
        result = await with_retry(success_func, max_attempts=3)
        assert result == "done"
    
    @pytest.mark.asyncio
    async def test_with_retry_failure(self):
        """Test with_retry on failure."""
        from phone_agent import with_retry
        
        call_count = 0
        
        async def always_fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("fail")
        
        with pytest.raises(ValueError):
            await with_retry(always_fail, max_attempts=2)
        
        assert call_count == 2


class TestCircuitBreaker:
    """Tests for CircuitBreaker."""
    
    def test_initial_state_closed(self):
        """Test circuit breaker starts closed."""
        from phone_agent import CircuitBreaker
        
        cb = CircuitBreaker()
        assert cb.state == CircuitBreaker.CLOSED
        assert cb.can_execute() == True
    
    def test_opens_after_failures(self):
        """Test circuit opens after threshold failures."""
        from phone_agent import CircuitBreaker
        
        cb = CircuitBreaker(failure_threshold=3)
        
        cb.record_failure()
        assert cb.state == CircuitBreaker.CLOSED
        
        cb.record_failure()
        assert cb.state == CircuitBreaker.CLOSED
        
        cb.record_failure()
        assert cb.state == CircuitBreaker.OPEN
        assert cb.can_execute() == False
    
    def test_success_resets_failures(self):
        """Test success resets failure count."""
        from phone_agent import CircuitBreaker
        
        cb = CircuitBreaker(failure_threshold=3)
        
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        
        # Should be reset, need 3 more failures
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreaker.CLOSED


class TestADBConnectionManager:
    """Tests for ADBConnectionManager."""
    
    def test_init(self):
        """Test manager initialization."""
        from phone_agent import ADBConnectionManager
        
        manager = ADBConnectionManager(device_id="test-device")
        assert manager.device_id == "test-device"
        assert manager.max_reconnect_attempts == 3


class TestRetryConfig:
    """Tests for RetryConfig."""
    
    def test_default_values(self):
        """Test default config values."""
        from phone_agent import RetryConfig
        
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.exponential_base == 2.0
    
    def test_custom_values(self):
        """Test custom config values."""
        from phone_agent import RetryConfig
        
        config = RetryConfig(
            max_attempts=5,
            base_delay=0.5,
            max_delay=60.0
        )
        assert config.max_attempts == 5
        assert config.base_delay == 0.5
        assert config.max_delay == 60.0
