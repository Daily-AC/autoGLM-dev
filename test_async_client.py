"""Test async model client."""
import asyncio
import sys
sys.path.insert(0, '.')

from phone_agent.model import AsyncModelClient, ModelConfig

async def test_async_client():
    """Test AsyncModelClient initialization and basic structure."""
    print("Testing AsyncModelClient...")
    
    # Test initialization
    config = ModelConfig(
        base_url="http://localhost:8000/v1",
        api_key="test-key",
        model_name="test-model"
    )
    
    client = AsyncModelClient(config)
    print(f"✓ AsyncModelClient initialized with config: {config.model_name}")
    
    # Test that request is async
    assert asyncio.iscoroutinefunction(client.request), "request() should be async"
    print("✓ request() is an async function")
    
    print("\n✅ All AsyncModelClient tests passed!")

if __name__ == "__main__":
    asyncio.run(test_async_client())
