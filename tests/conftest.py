"""
Pytest configuration and shared fixtures.
"""
import pytest
import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# Async fixtures
# =============================================================================

@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Model fixtures
# =============================================================================

@pytest.fixture
def model_config():
    """Provide a test model config."""
    from phone_agent.model import ModelConfig
    return ModelConfig(
        base_url="http://localhost:8000/v1",
        api_key="test-key-12345",
        model_name="test-model"
    )


@pytest.fixture
def agent_config():
    """Provide a test agent config."""
    from phone_agent.agent import AgentConfig
    return AgentConfig(
        device_id="test-device",
        max_steps=10,
        verbose=False
    )


@pytest.fixture
def mock_model_response():
    """Provide a mock model response."""
    return {
        "choices": [{
            "message": {
                "content": "<think>I will tap on the button.</think>do(action=\"Tap\", element=[500, 300])"
            }
        }]
    }


# =============================================================================
# ADB fixtures
# =============================================================================

@pytest.fixture
def mock_adb_process():
    """Mock an ADB subprocess."""
    mock_proc = AsyncMock()
    mock_proc.wait = AsyncMock(return_value=0)
    mock_proc.communicate = AsyncMock(return_value=(b"", b""))
    return mock_proc


@pytest.fixture
def mock_screenshot():
    """Provide a mock screenshot object."""
    from phone_agent.adb.screenshot import Screenshot
    return Screenshot(
        base64_data="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        width=1080,
        height=2400,
        is_sensitive=False
    )


# =============================================================================
# Action fixtures
# =============================================================================

@pytest.fixture
def sample_tap_action():
    """Provide a sample tap action."""
    return {
        "_metadata": "do",
        "action": "Tap",
        "element": [500, 300]
    }


@pytest.fixture
def sample_swipe_action():
    """Provide a sample swipe action."""
    return {
        "_metadata": "do",
        "action": "Swipe",
        "start": [500, 800],
        "end": [500, 200]
    }


@pytest.fixture
def sample_type_action():
    """Provide a sample type action."""
    return {
        "_metadata": "do",
        "action": "Type",
        "text": "Hello World"
    }


@pytest.fixture
def sample_finish_action():
    """Provide a sample finish action."""
    return {
        "_metadata": "finish",
        "message": "Task completed successfully"
    }
