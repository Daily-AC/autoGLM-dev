"""
Unified configuration management for Phone Agent.

Supports loading from:
- Environment variables (.env)
- YAML config files (config.yaml)
- Programmatic overrides

Priority (highest to lowest):
1. Programmatic overrides
2. Environment variables
3. YAML config files
4. Default values

Usage:
    from phone_agent.config import settings
    
    # Access settings
    settings.model.api_key
    settings.device.id
    
    # Override at runtime
    settings.model.api_key = "new-key"
    
    # Reload from files
    settings.reload()
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
import json


# =============================================================================
# Configuration Dataclasses
# =============================================================================

@dataclass
class ModelSettings:
    """AI Model configuration."""
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model_name: str = "gpt-4o"
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 60
    max_retries: int = 3


@dataclass
class DeviceSettings:
    """Android device configuration."""
    id: Optional[str] = None
    adb_path: str = "adb"
    scrcpy_path: str = "scrcpy"
    screenshot_timeout: int = 10
    action_delay: float = 1.0


@dataclass
class AgentSettings:
    """Agent behavior configuration."""
    max_steps: int = 100
    verbose: bool = False
    language: str = "zh"
    confirm_sensitive: bool = True
    auto_screenshot: bool = True


@dataclass
class WebSettings:
    """Web console configuration."""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    auto_open_browser: bool = True
    stream_fps: int = 10


@dataclass  
class LogSettings:
    """Logging configuration."""
    level: str = "INFO"
    file_path: Optional[str] = None
    json_format: bool = False


@dataclass
class Settings:
    """
    Main settings container.
    
    Provides unified access to all configuration.
    """
    model: ModelSettings = field(default_factory=ModelSettings)
    device: DeviceSettings = field(default_factory=DeviceSettings)
    agent: AgentSettings = field(default_factory=AgentSettings)
    web: WebSettings = field(default_factory=WebSettings)
    log: LogSettings = field(default_factory=LogSettings)
    
    # Internal state
    _config_file: Optional[Path] = None
    _env_prefix: str = "AUTOGLM_"
    
    def __post_init__(self):
        """Load configuration after initialization."""
        self._load_from_env()
        self._load_from_yaml()
    
    def _load_from_env(self):
        """Load settings from environment variables."""
        prefix = self._env_prefix
        
        # Model settings
        if val := os.getenv(f"{prefix}API_KEY"):
            self.model.api_key = val
        if val := os.getenv(f"{prefix}BASE_URL"):
            self.model.base_url = val
        if val := os.getenv(f"{prefix}MODEL"):
            self.model.model_name = val
        if val := os.getenv(f"{prefix}MAX_TOKENS"):
            self.model.max_tokens = int(val)
        if val := os.getenv(f"{prefix}TEMPERATURE"):
            self.model.temperature = float(val)
        if val := os.getenv(f"{prefix}TIMEOUT"):
            self.model.timeout = int(val)
            
        # Device settings
        if val := os.getenv(f"{prefix}DEVICE_ID"):
            self.device.id = val
        if val := os.getenv(f"{prefix}ADB_PATH"):
            self.device.adb_path = val
            
        # Agent settings
        if val := os.getenv(f"{prefix}MAX_STEPS"):
            self.agent.max_steps = int(val)
        if val := os.getenv(f"{prefix}VERBOSE"):
            self.agent.verbose = val.lower() in ("true", "1", "yes")
        if val := os.getenv(f"{prefix}LANGUAGE"):
            self.agent.language = val
            
        # Web settings
        if val := os.getenv(f"{prefix}HOST"):
            self.web.host = val
        if val := os.getenv(f"{prefix}PORT"):
            self.web.port = int(val)
        if val := os.getenv(f"{prefix}DEBUG"):
            self.web.debug = val.lower() in ("true", "1", "yes")
            
        # Log settings
        if val := os.getenv(f"{prefix}LOG_LEVEL"):
            self.log.level = val.upper()
        if val := os.getenv(f"{prefix}LOG_FILE"):
            self.log.file_path = val
    
    def _load_from_yaml(self):
        """Load settings from YAML config file."""
        try:
            import yaml
        except ImportError:
            return  # PyYAML not installed, skip
        
        # Look for config files in order
        search_paths = [
            Path.cwd() / "config.yaml",
            Path.cwd() / "config.yml",
            Path.home() / ".autoglm" / "config.yaml",
        ]
        
        for config_path in search_paths:
            if config_path.exists():
                self._config_file = config_path
                self._apply_yaml_config(config_path)
                break
    
    def _apply_yaml_config(self, path: Path):
        """Apply config from YAML file."""
        try:
            import yaml
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            
            # Model settings
            if model := data.get("model"):
                for key, val in model.items():
                    if hasattr(self.model, key):
                        setattr(self.model, key, val)
            
            # Device settings
            if device := data.get("device"):
                for key, val in device.items():
                    if hasattr(self.device, key):
                        setattr(self.device, key, val)
            
            # Agent settings
            if agent := data.get("agent"):
                for key, val in agent.items():
                    if hasattr(self.agent, key):
                        setattr(self.agent, key, val)
            
            # Web settings
            if web := data.get("web"):
                for key, val in web.items():
                    if hasattr(self.web, key):
                        setattr(self.web, key, val)
                        
            # Log settings
            if log := data.get("log"):
                for key, val in log.items():
                    if hasattr(self.log, key):
                        setattr(self.log, key, val)
                        
        except Exception as e:
            print(f"Warning: Failed to load config from {path}: {e}")
    
    def reload(self):
        """Reload configuration from all sources."""
        # Reset to defaults
        self.model = ModelSettings()
        self.device = DeviceSettings()
        self.agent = AgentSettings()
        self.web = WebSettings()
        self.log = LogSettings()
        
        # Reload
        self._load_from_env()
        self._load_from_yaml()
    
    def to_dict(self) -> dict:
        """Convert settings to dictionary."""
        return {
            "model": {
                "base_url": self.model.base_url,
                "model_name": self.model.model_name,
                "max_tokens": self.model.max_tokens,
                "temperature": self.model.temperature,
                "timeout": self.model.timeout,
                "max_retries": self.model.max_retries,
                # Exclude api_key for security
            },
            "device": {
                "id": self.device.id,
                "adb_path": self.device.adb_path,
                "screenshot_timeout": self.device.screenshot_timeout,
                "action_delay": self.device.action_delay,
            },
            "agent": {
                "max_steps": self.agent.max_steps,
                "verbose": self.agent.verbose,
                "language": self.agent.language,
                "confirm_sensitive": self.agent.confirm_sensitive,
            },
            "web": {
                "host": self.web.host,
                "port": self.web.port,
                "debug": self.web.debug,
                "auto_open_browser": self.web.auto_open_browser,
                "stream_fps": self.web.stream_fps,
            },
            "log": {
                "level": self.log.level,
                "file_path": self.log.file_path,
                "json_format": self.log.json_format,
            }
        }
    
    def __repr__(self) -> str:
        return f"Settings(config_file={self._config_file})"


# =============================================================================
# Global Settings Instance
# =============================================================================

# Create singleton settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings


def configure(**kwargs):
    """
    Configure settings programmatically.
    
    Args:
        **kwargs: Settings to override in format "section_key=value"
        
    Example:
        configure(model_api_key="xxx", web_port=9000)
    """
    for key, value in kwargs.items():
        parts = key.split("_", 1)
        if len(parts) == 2:
            section, attr = parts
            if hasattr(settings, section):
                section_obj = getattr(settings, section)
                if hasattr(section_obj, attr):
                    setattr(section_obj, attr, value)
