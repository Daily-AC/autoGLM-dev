"""
Structured logging for Open-AutoGLM.

This module provides a structured logging system that outputs JSON-formatted
logs, enabling easy parsing by both terminals and web frontends.

Usage:
    from phone_agent.logging import get_logger
    
    logger = get_logger("agent")
    logger.info("Task started", task="打开微信")
    logger.thought("分析屏幕内容...")
    logger.action("Tap", element=[500, 500])
    logger.result("任务完成")
"""

import json
import sys
import time
from enum import Enum
from typing import Any, Optional
from dataclasses import dataclass, asdict


class LogLevel(Enum):
    """Log severity levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    AGENT = "AGENT"  # Special level for agent activities


@dataclass
class LogEntry:
    """Structured log entry."""
    ts: float           # Unix timestamp
    module: str         # Module name
    level: str          # Log level
    msg: str            # Message
    tag: Optional[str] = None      # Semantic tag (THOUGHT/ACTION/RESULT)
    details: Optional[dict] = None  # Additional data
    
    def to_json(self) -> str:
        """Convert to JSON string, omitting None fields."""
        data = {k: v for k, v in asdict(self).items() if v is not None}
        return json.dumps(data, ensure_ascii=False)
    
    def to_console(self) -> str:
        """Format for console output with colors."""
        # ANSI colors
        colors = {
            "DEBUG": "\033[90m",    # Gray
            "INFO": "\033[97m",     # White
            "WARN": "\033[93m",     # Yellow
            "ERROR": "\033[91m",    # Red
            "AGENT": "\033[92m",    # Green
        }
        reset = "\033[0m"
        
        color = colors.get(self.level, "")
        timestamp = time.strftime("%H:%M:%S", time.localtime(self.ts))
        
        # Format based on tag
        if self.tag == "THOUGHT":
            return f"{color}[{timestamp}] 💭 {self.msg}{reset}"
        elif self.tag == "ACTION":
            # Get action_details from details dict
            action_data = self.details.get("action_details") if self.details else None
            details_str = json.dumps(action_data, ensure_ascii=False) if action_data else ""
            return f"{color}[{timestamp}] 🎯 {self.msg}: {details_str}{reset}"
        elif self.tag == "RESULT":
            return f"{color}[{timestamp}] ✅ {self.msg}{reset}"
        else:
            return f"{color}[{timestamp}] [{self.level}] [{self.module}] {self.msg}{reset}"


class StructuredLogger:
    """
    Structured logger with JSON output.
    
    Features:
    - Multiple log levels (DEBUG → ERROR)
    - JSON format for programmatic parsing
    - Dual output: terminal + optional queue
    - Agent-specific tags (THOUGHT/ACTION/RESULT)
    
    Args:
        module: Module name for identification
        queue: Optional queue for web frontend
        min_level: Minimum level to log (default: INFO)
    """
    
    _LEVEL_ORDER = {
        LogLevel.DEBUG: 0,
        LogLevel.INFO: 1,
        LogLevel.WARN: 2,
        LogLevel.ERROR: 3,
        LogLevel.AGENT: 1,  # Same as INFO
    }
    
    def __init__(
        self, 
        module: str, 
        queue: Optional[Any] = None,
        min_level: LogLevel = LogLevel.INFO
    ):
        self.module = module
        self.queue = queue
        self.min_level = min_level
    
    def _should_log(self, level: LogLevel) -> bool:
        """Check if level meets minimum threshold."""
        return self._LEVEL_ORDER.get(level, 0) >= self._LEVEL_ORDER.get(self.min_level, 0)
    
    def log(
        self, 
        level: LogLevel, 
        msg: str, 
        tag: Optional[str] = None,
        **extra
    ) -> None:
        """
        Log a message with optional extra fields.
        
        Args:
            level: Log level
            msg: Log message
            tag: Optional semantic tag
            **extra: Additional fields to include
        """
        if not self._should_log(level):
            return
        
        entry = LogEntry(
            ts=time.time(),
            module=self.module,
            level=level.value,
            msg=msg,
            tag=tag,
            details=extra if extra else None
        )
        
        # Output to terminal
        try:
            print(entry.to_console())
        except Exception:
            # Fallback if color codes fail
            sys.__stdout__.write(entry.to_json() + "\n")
            sys.__stdout__.flush()
        
        # Output to queue (for web frontend)
        if self.queue:
            try:
                self.queue.put(entry.to_json())
            except Exception:
                pass  # Silently ignore queue errors
    
    # ========== Standard Levels ==========
    
    def debug(self, msg: str, **extra) -> None:
        """Log debug message."""
        self.log(LogLevel.DEBUG, msg, **extra)
    
    def info(self, msg: str, **extra) -> None:
        """Log info message."""
        self.log(LogLevel.INFO, msg, **extra)
    
    def warn(self, msg: str, **extra) -> None:
        """Log warning message."""
        self.log(LogLevel.WARN, msg, **extra)
    
    def error(self, msg: str, **extra) -> None:
        """Log error message."""
        self.log(LogLevel.ERROR, msg, **extra)
    
    # ========== Agent-Specific Methods ==========
    
    def thought(self, msg: str) -> None:
        """Log agent thinking process."""
        self.log(LogLevel.AGENT, msg, tag="THOUGHT")
    
    def action(self, action_name: str, details: Optional[dict] = None) -> None:
        """Log agent action execution."""
        # Pass details as a nested dict, not expanded
        self.log(LogLevel.AGENT, action_name, tag="ACTION", action_details=details)
    
    def result(self, msg: str) -> None:
        """Log task result."""
        self.log(LogLevel.AGENT, msg, tag="RESULT")
    
    def cancelled(self, msg: str = "Task cancelled by user") -> None:
        """Log task cancellation."""
        self.log(LogLevel.WARN, msg, tag="CANCELLED")


# ========== Logger Factory ==========

_loggers: dict[str, StructuredLogger] = {}
_global_queue: Optional[Any] = None


def set_global_queue(queue: Any) -> None:
    """Set the global queue for all loggers."""
    global _global_queue
    _global_queue = queue
    # Update existing loggers
    for logger in _loggers.values():
        logger.queue = queue


def get_logger(module: str, min_level: LogLevel = LogLevel.INFO) -> StructuredLogger:
    """
    Get or create a logger for the given module.
    
    Args:
        module: Module name
        min_level: Minimum log level
        
    Returns:
        StructuredLogger instance
    """
    if module not in _loggers:
        _loggers[module] = StructuredLogger(module, _global_queue, min_level)
    return _loggers[module]
