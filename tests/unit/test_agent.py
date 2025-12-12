"""
Unit tests for AsyncPhoneAgent.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


class TestAsyncPhoneAgent:
    """Tests for AsyncPhoneAgent."""
    
    def test_init(self, model_config, agent_config):
        """Test agent initialization."""
        from phone_agent import AsyncPhoneAgent
        
        agent = AsyncPhoneAgent(model_config, agent_config)
        assert agent.model_config == model_config
        assert agent.agent_config == agent_config
        assert agent.step_count == 0
    
    def test_init_default_config(self):
        """Test agent with default config."""
        from phone_agent import AsyncPhoneAgent
        
        agent = AsyncPhoneAgent()
        assert agent.model_config is not None
        assert agent.agent_config is not None
    
    def test_step_is_async(self, model_config, agent_config):
        """Test that step is an async function."""
        from phone_agent import AsyncPhoneAgent
        
        agent = AsyncPhoneAgent(model_config, agent_config)
        assert asyncio.iscoroutinefunction(agent.step)
    
    def test_run_is_async(self, model_config, agent_config):
        """Test that run is an async function."""
        from phone_agent import AsyncPhoneAgent
        
        agent = AsyncPhoneAgent(model_config, agent_config)
        assert asyncio.iscoroutinefunction(agent.run)
    
    def test_reset(self, model_config, agent_config):
        """Test agent reset."""
        from phone_agent import AsyncPhoneAgent
        
        agent = AsyncPhoneAgent(model_config, agent_config)
        agent._step_count = 5
        agent._cancelled = True
        
        agent.reset()
        
        assert agent.step_count == 0
        assert agent._cancelled == False
        assert agent.context == []
    
    def test_cancel(self, model_config, agent_config):
        """Test agent cancel."""
        from phone_agent import AsyncPhoneAgent
        
        agent = AsyncPhoneAgent(model_config, agent_config)
        assert agent._cancelled == False
        
        agent.cancel()
        
        assert agent._cancelled == True


class TestPhoneAgent:
    """Tests for sync PhoneAgent."""
    
    def test_init(self, model_config, agent_config):
        """Test agent initialization."""
        from phone_agent import PhoneAgent
        
        agent = PhoneAgent(model_config, agent_config)
        assert agent.model_config == model_config
        assert agent.step_count == 0
    
    def test_step_is_sync(self, model_config, agent_config):
        """Test that step is NOT an async function."""
        from phone_agent import PhoneAgent
        
        agent = PhoneAgent(model_config, agent_config)
        assert not asyncio.iscoroutinefunction(agent.step)


class TestCancellationToken:
    """Tests for cancellation tokens."""
    
    def test_sync_token(self):
        """Test synchronous CancellationToken."""
        from phone_agent import CancellationToken
        
        token = CancellationToken()
        assert token.is_cancelled == False
        
        token.cancel()
        assert token.is_cancelled == True
        
        token.reset()
        assert token.is_cancelled == False
    
    def test_async_token(self):
        """Test AsyncCancellationToken."""
        from phone_agent import AsyncCancellationToken
        
        token = AsyncCancellationToken()
        assert token.is_cancelled == False
        
        token.cancel()
        assert token.is_cancelled == True
        
        token.reset()
        assert token.is_cancelled == False
    
    @pytest.mark.asyncio
    async def test_async_token_check(self):
        """Test AsyncCancellationToken.check()."""
        from phone_agent import AsyncCancellationToken
        
        token = AsyncCancellationToken()
        
        # Should not raise when not cancelled
        await token.check()
        
        # Should raise when cancelled
        token.cancel()
        with pytest.raises(asyncio.CancelledError):
            await token.check()
