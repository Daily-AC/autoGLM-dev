"""Test async phone agent."""
import asyncio
import sys
sys.path.insert(0, '.')

from phone_agent import AsyncPhoneAgent
from phone_agent.model import ModelConfig

async def test_async_agent():
    """Test AsyncPhoneAgent initialization and basic structure."""
    print("Testing AsyncPhoneAgent...")
    
    # Test initialization
    config = ModelConfig(
        base_url="http://localhost:8000/v1",
        api_key="test-key",
        model_name="test-model"
    )
    
    agent = AsyncPhoneAgent(config)
    print(f"✓ AsyncPhoneAgent initialized")
    
    # Test that step is async
    assert asyncio.iscoroutinefunction(agent.step), "step() should be async"
    print("✓ step() is an async function")
    
    # Test that run is async
    assert asyncio.iscoroutinefunction(agent.run), "run() should be async"
    print("✓ run() is an async function")
    
    # Test cancel
    agent.cancel()
    assert agent.is_cancelled, "is_cancelled should be True after cancel()"
    print("✓ cancel() works")
    
    # Test reset
    agent.reset()
    assert not agent.is_cancelled, "is_cancelled should be False after reset()"
    print("✓ reset() works")
    
    print("\n✅ All AsyncPhoneAgent tests passed!")

if __name__ == "__main__":
    asyncio.run(test_async_agent())
