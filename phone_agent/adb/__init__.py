"""ADB utilities for Android device interaction."""

from phone_agent.adb.connection import (
    ADBConnection,
    ConnectionType,
    DeviceInfo,
    list_devices,
    quick_connect,
)
from phone_agent.adb.device import (
    back,
    double_tap,
    get_current_app,
    home,
    launch_app,
    long_press,
    swipe,
    tap,
    # Async versions
    async_tap,
    async_double_tap,
    async_long_press,
    async_swipe,
    async_back,
    async_home,
    async_launch_app,
    async_get_current_app,
)
from phone_agent.adb.input import (
    clear_text,
    detect_and_set_adb_keyboard,
    restore_keyboard,
    type_text,
    # Async versions
    async_type_text,
    async_clear_text,
    async_detect_and_set_adb_keyboard,
    async_restore_keyboard,
)
from phone_agent.adb.screenshot import get_screenshot, async_get_screenshot

__all__ = [
    # Screenshot (sync + async)
    "get_screenshot",
    "async_get_screenshot",
    # Input (sync)
    "type_text",
    "clear_text",
    "detect_and_set_adb_keyboard",
    "restore_keyboard",
    # Input (async)
    "async_type_text",
    "async_clear_text",
    "async_detect_and_set_adb_keyboard",
    "async_restore_keyboard",
    # Device control (sync)
    "get_current_app",
    "tap",
    "swipe",
    "back",
    "home",
    "double_tap",
    "long_press",
    "launch_app",
    # Device control (async)
    "async_tap",
    "async_double_tap",
    "async_long_press",
    "async_swipe",
    "async_back",
    "async_home",
    "async_launch_app",
    "async_get_current_app",
    # Connection management
    "ADBConnection",
    "DeviceInfo",
    "ConnectionType",
    "quick_connect",
    "list_devices",
]
