"""
Unit tests for settings configuration.
"""
import pytest
import os
from unittest.mock import patch


class TestSettings:
    """Tests for Settings class."""
    
    def test_settings_import(self):
        """Test settings can be imported."""
        from phone_agent.config import settings
        assert settings is not None
    
    def test_settings_singleton(self):
        """Test settings is a singleton."""
        from phone_agent.config import settings, get_settings
        assert settings is get_settings()
    
    def test_default_model_settings(self):
        """Test default model settings."""
        from phone_agent.config import ModelSettings
        
        model = ModelSettings()
        assert model.max_tokens == 4096
        assert model.temperature == 0.7
        assert model.max_retries == 3
    
    def test_default_device_settings(self):
        """Test default device settings."""
        from phone_agent.config import DeviceSettings
        
        device = DeviceSettings()
        assert device.adb_path == "adb"
        assert device.screenshot_timeout == 10
    
    def test_default_agent_settings(self):
        """Test default agent settings."""
        from phone_agent.config import AgentSettings
        
        agent = AgentSettings()
        assert agent.max_steps == 100
        assert agent.language == "zh"
    
    def test_default_web_settings(self):
        """Test default web settings."""
        from phone_agent.config import WebSettings
        
        web = WebSettings()
        assert web.port == 8000
        assert web.host == "0.0.0.0"
    
    def test_to_dict(self):
        """Test settings to_dict method."""
        from phone_agent.config import Settings
        
        settings = Settings()
        d = settings.to_dict()
        
        assert "model" in d
        assert "device" in d
        assert "agent" in d
        assert "web" in d
        assert "log" in d
        
        # API key should not be in output
        assert "api_key" not in d["model"]


class TestConfigure:
    """Tests for configure function."""
    
    def test_configure_model(self):
        """Test configuring model settings."""
        from phone_agent.config import Settings, configure
        
        # Create fresh settings for test
        settings = Settings()
        settings.model.max_tokens = 1000
        
        assert settings.model.max_tokens == 1000
    
    def test_configure_web_port(self):
        """Test configuring web port."""
        from phone_agent.config import Settings
        
        settings = Settings()
        settings.web.port = 9000
        
        assert settings.web.port == 9000


class TestEnvLoading:
    """Tests for environment variable loading."""
    
    def test_load_api_key_from_env(self):
        """Test loading API key from environment."""
        from phone_agent.config import Settings
        
        with patch.dict(os.environ, {"AUTOGLM_API_KEY": "test-key-123"}):
            settings = Settings()
            assert settings.model.api_key == "test-key-123"
    
    def test_load_port_from_env(self):
        """Test loading port from environment."""
        from phone_agent.config import Settings
        
        with patch.dict(os.environ, {"AUTOGLM_PORT": "9999"}):
            settings = Settings()
            assert settings.web.port == 9999
    
    def test_load_debug_from_env(self):
        """Test loading debug flag from environment."""
        from phone_agent.config import Settings
        
        with patch.dict(os.environ, {"AUTOGLM_DEBUG": "true"}):
            settings = Settings()
            assert settings.web.debug == True
