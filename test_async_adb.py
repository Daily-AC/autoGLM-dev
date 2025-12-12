"""Test async ADB functions."""
import asyncio
import sys
sys.path.insert(0, '.')

from phone_agent.adb import (
    async_tap, async_swipe, async_back, async_home,
    async_launch_app, async_get_current_app
)

async def test_async_adb():
    """Test async ADB function structure."""
    print("Testing Async ADB Functions...")
    
    # Verify all functions are async
    assert asyncio.iscoroutinefunction(async_tap), "async_tap should be async"
    print("✓ async_tap is async")
    
    assert asyncio.iscoroutinefunction(async_swipe), "async_swipe should be async"
    print("✓ async_swipe is async")
    
    assert asyncio.iscoroutinefunction(async_back), "async_back should be async"
    print("✓ async_back is async")
    
    assert asyncio.iscoroutinefunction(async_home), "async_home should be async"
    print("✓ async_home is async")
    
    assert asyncio.iscoroutinefunction(async_launch_app), "async_launch_app should be async"
    print("✓ async_launch_app is async")
    
    assert asyncio.iscoroutinefunction(async_get_current_app), "async_get_current_app should be async"
    print("✓ async_get_current_app is async")
    
    print("\n✅ All Async ADB tests passed!")

if __name__ == "__main__":
    asyncio.run(test_async_adb())
