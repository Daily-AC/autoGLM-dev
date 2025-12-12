"""
Unit tests for async ADB functions.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch


class TestAsyncADBFunctions:
    """Tests for async ADB functions."""
    
    def test_async_tap_is_coroutine(self):
        """Test async_tap is a coroutine function."""
        from phone_agent.adb import async_tap
        assert asyncio.iscoroutinefunction(async_tap)
    
    def test_async_swipe_is_coroutine(self):
        """Test async_swipe is a coroutine function."""
        from phone_agent.adb import async_swipe
        assert asyncio.iscoroutinefunction(async_swipe)
    
    def test_async_back_is_coroutine(self):
        """Test async_back is a coroutine function."""
        from phone_agent.adb import async_back
        assert asyncio.iscoroutinefunction(async_back)
    
    def test_async_home_is_coroutine(self):
        """Test async_home is a coroutine function."""
        from phone_agent.adb import async_home
        assert asyncio.iscoroutinefunction(async_home)
    
    def test_async_type_text_is_coroutine(self):
        """Test async_type_text is a coroutine function."""
        from phone_agent.adb import async_type_text
        assert asyncio.iscoroutinefunction(async_type_text)
    
    def test_async_get_screenshot_is_coroutine(self):
        """Test async_get_screenshot is a coroutine function."""
        from phone_agent.adb import async_get_screenshot
        assert asyncio.iscoroutinefunction(async_get_screenshot)
    
    @pytest.mark.asyncio
    async def test_async_tap_calls_subprocess(self):
        """Test async_tap calls subprocess correctly."""
        from phone_agent.adb import async_tap
        
        with patch('asyncio.create_subprocess_exec', new_callable=AsyncMock) as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.wait = AsyncMock(return_value=0)
            mock_exec.return_value = mock_proc
            
            await async_tap(100, 200, device_id="test-device")
            
            mock_exec.assert_called_once()
            args = mock_exec.call_args[0]
            assert "adb" in args
            assert "-s" in args
            assert "test-device" in args
            assert "tap" in args
    
    @pytest.mark.asyncio
    async def test_async_swipe_calls_subprocess(self):
        """Test async_swipe calls subprocess correctly."""
        from phone_agent.adb import async_swipe
        
        with patch('asyncio.create_subprocess_exec', new_callable=AsyncMock) as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.wait = AsyncMock(return_value=0)
            mock_exec.return_value = mock_proc
            
            await async_swipe(100, 200, 300, 400, device_id="test-device")
            
            mock_exec.assert_called_once()
            args = mock_exec.call_args[0]
            assert "swipe" in args


class TestAsyncInputFunctions:
    """Tests for async input functions."""
    
    def test_async_clear_text_is_coroutine(self):
        """Test async_clear_text is a coroutine function."""
        from phone_agent.adb import async_clear_text
        assert asyncio.iscoroutinefunction(async_clear_text)
    
    def test_async_detect_and_set_adb_keyboard_is_coroutine(self):
        """Test async_detect_and_set_adb_keyboard is a coroutine function."""
        from phone_agent.adb import async_detect_and_set_adb_keyboard
        assert asyncio.iscoroutinefunction(async_detect_and_set_adb_keyboard)


class TestScreenshot:
    """Tests for screenshot functions."""
    
    def test_screenshot_dataclass(self):
        """Test Screenshot dataclass."""
        from phone_agent.adb.screenshot import Screenshot
        
        ss = Screenshot(
            base64_data="test_data",
            width=1080,
            height=2400,
            is_sensitive=False
        )
        
        assert ss.base64_data == "test_data"
        assert ss.width == 1080
        assert ss.height == 2400
        assert ss.is_sensitive == False
