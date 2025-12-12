"""
Unit tests for structured logging.
"""
import pytest
from io import StringIO


class TestStructuredLogger:
    """Tests for StructuredLogger."""
    
    def test_get_logger(self):
        """Test getting a logger instance."""
        from phone_agent.logging import get_logger
        
        logger = get_logger("test")
        assert logger is not None
        assert logger.module == "test"
    
    def test_logger_singleton(self):
        """Test logger singleton behavior."""
        from phone_agent.logging import get_logger
        
        logger1 = get_logger("singleton_test")
        logger2 = get_logger("singleton_test")
        
        assert logger1 is logger2
    
    def test_log_levels(self):
        """Test log level methods exist."""
        from phone_agent.logging import get_logger
        
        logger = get_logger("level_test")
        
        # Should not raise
        logger.info("test info")
        logger.warn("test warn")
        logger.error("test error")
        logger.debug("test debug")
    
    def test_agent_methods(self):
        """Test agent-specific log methods."""
        from phone_agent.logging import get_logger
        
        logger = get_logger("agent_test")
        
        # Should not raise
        logger.thought("thinking...")
        logger.action("Tap", {"element": [100, 200]})
        logger.result("done")
        logger.cancelled("cancelled")
        logger.failed("failed")


class TestLogEntry:
    """Tests for LogEntry dataclass."""
    
    def test_log_entry_creation(self):
        """Test LogEntry creation."""
        from phone_agent.logging import LogEntry
        import time
        
        entry = LogEntry(
            ts=time.time(),
            module="test",
            level="INFO",
            msg="test message"
        )
        
        assert entry.module == "test"
        assert entry.level == "INFO"
        assert entry.msg == "test message"
    
    def test_log_entry_to_console(self):
        """Test LogEntry console formatting."""
        from phone_agent.logging import LogEntry
        import time
        
        entry = LogEntry(
            ts=time.time(),
            module="test",
            level="INFO",
            msg="test message"
        )
        
        console_output = entry.to_console()
        assert isinstance(console_output, str)
        assert "test message" in console_output
    
    def test_log_entry_to_json(self):
        """Test LogEntry JSON formatting."""
        from phone_agent.logging import LogEntry
        import time
        import json
        
        entry = LogEntry(
            ts=time.time(),
            module="test",
            level="INFO",
            msg="test message"
        )
        
        json_output = entry.to_json()
        parsed = json.loads(json_output)
        
        assert parsed["module"] == "test"
        assert parsed["msg"] == "test message"
