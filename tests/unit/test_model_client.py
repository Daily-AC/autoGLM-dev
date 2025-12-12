"""
Unit tests for AsyncModelClient.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


class TestAsyncModelClient:
    """Tests for AsyncModelClient."""
    
    def test_init(self, model_config):
        """Test client initialization."""
        from phone_agent.model import AsyncModelClient
        
        client = AsyncModelClient(model_config)
        assert client.config == model_config
        assert client.config.model_name == "test-model"
    
    def test_init_default_config(self):
        """Test client with default config."""
        from phone_agent.model import AsyncModelClient
        
        client = AsyncModelClient()
        assert client.config is not None
    
    def test_request_is_async(self, model_config):
        """Test that request is an async function."""
        from phone_agent.model import AsyncModelClient
        
        client = AsyncModelClient(model_config)
        assert asyncio.iscoroutinefunction(client.request)
    
    @pytest.mark.asyncio
    async def test_request_success(self, model_config, mock_model_response):
        """Test successful API request."""
        from phone_agent.model import AsyncModelClient
        
        client = AsyncModelClient(model_config)
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = mock_model_response
            mock_response.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client
            
            response = await client.request([{"role": "user", "content": "test"}])
            
            assert response is not None
            assert response.thinking is not None or response.action is not None
    
    @pytest.mark.asyncio
    async def test_request_empty_response(self, model_config):
        """Test handling of empty response."""
        from phone_agent.model import AsyncModelClient
        
        client = AsyncModelClient(model_config)
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "choices": [{"message": {"content": ""}}]
            }
            mock_response.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client
            
            response = await client.request([{"role": "user", "content": "test"}])
            
            # Should return empty but not crash
            assert response is not None


class TestModelConfig:
    """Tests for ModelConfig."""
    
    def test_default_values(self):
        """Test default config values."""
        from phone_agent.model import ModelConfig
        
        config = ModelConfig()
        assert config.max_tokens > 0
        assert config.temperature >= 0
    
    def test_custom_values(self):
        """Test custom config values."""
        from phone_agent.model import ModelConfig
        
        config = ModelConfig(
            base_url="http://custom:8080",
            api_key="custom-key",
            model_name="custom-model",
            max_tokens=1000
        )
        assert config.base_url == "http://custom:8080"
        assert config.api_key == "custom-key"
        assert config.max_tokens == 1000
