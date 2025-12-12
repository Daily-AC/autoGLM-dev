"""
Unit tests for ActionHandler and AsyncActionHandler.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


class TestActionHandler:
    """Tests for sync ActionHandler."""
    
    def test_init(self):
        """Test handler initialization."""
        from phone_agent.actions import ActionHandler
        
        handler = ActionHandler(device_id="test-device")
        assert handler.device_id == "test-device"
    
    def test_execute_finish(self, sample_finish_action):
        """Test finish action execution."""
        from phone_agent.actions import ActionHandler
        
        handler = ActionHandler()
        result = handler.execute(sample_finish_action, 1080, 2400)
        
        assert result.success == True
        assert result.should_finish == True
        assert result.message == "Task completed successfully"
    
    def test_execute_unknown_type(self):
        """Test unknown action type."""
        from phone_agent.actions import ActionHandler
        
        handler = ActionHandler()
        result = handler.execute({"_metadata": "unknown"}, 1080, 2400)
        
        assert result.success == False
        assert result.should_finish == True
        assert "Unknown action type" in result.message
    
    def test_coordinate_conversion(self):
        """Test relative to absolute coordinate conversion."""
        from phone_agent.actions import ActionHandler
        
        handler = ActionHandler()
        
        # 500/1000 = 0.5, 0.5 * 1080 = 540
        x, y = handler._convert_relative_to_absolute([500, 500], 1080, 2400)
        assert x == 540
        assert y == 1200
        
        # Edge cases
        x, y = handler._convert_relative_to_absolute([0, 0], 1080, 2400)
        assert x == 0
        assert y == 0
        
        x, y = handler._convert_relative_to_absolute([1000, 1000], 1080, 2400)
        assert x == 1080
        assert y == 2400


class TestAsyncActionHandler:
    """Tests for AsyncActionHandler."""
    
    def test_init(self):
        """Test async handler initialization."""
        from phone_agent.actions import AsyncActionHandler
        
        handler = AsyncActionHandler(device_id="test-device")
        assert handler.device_id == "test-device"
    
    def test_execute_is_async(self):
        """Test that execute is async."""
        from phone_agent.actions import AsyncActionHandler
        
        handler = AsyncActionHandler()
        assert asyncio.iscoroutinefunction(handler.execute)
    
    @pytest.mark.asyncio
    async def test_execute_finish(self, sample_finish_action):
        """Test async finish action execution."""
        from phone_agent.actions import AsyncActionHandler
        
        handler = AsyncActionHandler()
        result = await handler.execute(sample_finish_action, 1080, 2400)
        
        assert result.success == True
        assert result.should_finish == True
    
    @pytest.mark.asyncio
    async def test_execute_tap(self, sample_tap_action):
        """Test async tap action with mocked ADB."""
        from phone_agent.actions import AsyncActionHandler
        
        handler = AsyncActionHandler(device_id="test-device")
        
        with patch('phone_agent.adb.async_tap', new_callable=AsyncMock) as mock_tap:
            result = await handler.execute(sample_tap_action, 1080, 2400)
            
            assert result.success == True
            assert result.should_finish == False
            mock_tap.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_swipe(self, sample_swipe_action):
        """Test async swipe action with mocked ADB."""
        from phone_agent.actions import AsyncActionHandler
        
        handler = AsyncActionHandler(device_id="test-device")
        
        with patch('phone_agent.adb.async_swipe', new_callable=AsyncMock) as mock_swipe:
            result = await handler.execute(sample_swipe_action, 1080, 2400)
            
            assert result.success == True
            mock_swipe.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_wait(self):
        """Test async wait action."""
        from phone_agent.actions import AsyncActionHandler
        
        handler = AsyncActionHandler()
        action = {"_metadata": "do", "action": "Wait", "duration": "0.1 seconds"}
        
        start = asyncio.get_event_loop().time()
        result = await handler.execute(action, 1080, 2400)
        elapsed = asyncio.get_event_loop().time() - start
        
        assert result.success == True
        assert elapsed >= 0.1
