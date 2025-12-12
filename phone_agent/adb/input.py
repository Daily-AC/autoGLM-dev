"""Input utilities for Android device text input."""

import base64
import subprocess
from typing import Optional


def type_text(text: str, device_id: str | None = None) -> None:
    """
    Type text into the currently focused input field using ADB Keyboard.

    Args:
        text: The text to type.
        device_id: Optional ADB device ID for multi-device setups.

    Note:
        Requires ADB Keyboard to be installed on the device.
        See: https://github.com/nicnocquee/AdbKeyboard
    """
    adb_prefix = _get_adb_prefix(device_id)
    encoded_text = base64.b64encode(text.encode("utf-8")).decode("utf-8")

    subprocess.run(
        adb_prefix
        + [
            "shell",
            "am",
            "broadcast",
            "-a",
            "ADB_INPUT_B64",
            "--es",
            "msg",
            encoded_text,
        ],
        capture_output=True,
        text=True,
    )


def clear_text(device_id: str | None = None) -> None:
    """
    Clear text in the currently focused input field.

    Args:
        device_id: Optional ADB device ID for multi-device setups.
    """
    adb_prefix = _get_adb_prefix(device_id)

    subprocess.run(
        adb_prefix + ["shell", "am", "broadcast", "-a", "ADB_CLEAR_TEXT"],
        capture_output=True,
        text=True,
    )


def detect_and_set_adb_keyboard(device_id: str | None = None) -> str:
    """
    Detect current keyboard and switch to ADB Keyboard if needed.

    Args:
        device_id: Optional ADB device ID for multi-device setups.

    Returns:
        The original keyboard IME identifier for later restoration.
    """
    adb_prefix = _get_adb_prefix(device_id)

    # Get current IME
    result = subprocess.run(
        adb_prefix + ["shell", "settings", "get", "secure", "default_input_method"],
        capture_output=True,
        text=True,
    )
    current_ime = (result.stdout + result.stderr).strip()

    # Switch to ADB Keyboard if not already set
    if "com.android.adbkeyboard/.AdbIME" not in current_ime:
        subprocess.run(
            adb_prefix + ["shell", "ime", "set", "com.android.adbkeyboard/.AdbIME"],
            capture_output=True,
            text=True,
        )

    # Warm up the keyboard
    type_text("", device_id)

    return current_ime


def restore_keyboard(ime: str, device_id: str | None = None) -> None:
    """
    Restore the original keyboard IME.

    Args:
        ime: The IME identifier to restore.
        device_id: Optional ADB device ID for multi-device setups.
    """
    adb_prefix = _get_adb_prefix(device_id)

    subprocess.run(
        adb_prefix + ["shell", "ime", "set", ime], capture_output=True, text=True
    )


def _get_adb_prefix(device_id: str | None) -> list:
    """Get ADB command prefix with optional device specifier."""
    if device_id:
        return ["adb", "-s", device_id]
    return ["adb"]


# =============================================================================
# Async Input Functions
# =============================================================================

async def _async_run_adb(args: list) -> None:
    """Run ADB command asynchronously."""
    import asyncio
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.wait()


async def async_type_text(text: str, device_id: str | None = None) -> None:
    """
    Type text asynchronously using ADB Keyboard.
    """
    import base64
    adb_prefix = _get_adb_prefix(device_id)
    encoded_text = base64.b64encode(text.encode("utf-8")).decode("utf-8")
    
    await _async_run_adb(
        adb_prefix + [
            "shell", "am", "broadcast", "-a", "ADB_INPUT_B64",
            "--es", "msg", encoded_text
        ]
    )


async def async_clear_text(device_id: str | None = None) -> None:
    """Clear text asynchronously in the focused input field."""
    adb_prefix = _get_adb_prefix(device_id)
    await _async_run_adb(
        adb_prefix + ["shell", "am", "broadcast", "-a", "ADB_CLEAR_TEXT"]
    )


async def async_detect_and_set_adb_keyboard(device_id: str | None = None) -> str:
    """Detect current keyboard and switch to ADB Keyboard asynchronously."""
    import asyncio
    adb_prefix = _get_adb_prefix(device_id)
    
    # Get current IME
    proc = await asyncio.create_subprocess_exec(
        *adb_prefix, "shell", "settings", "get", "secure", "default_input_method",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    current_ime = (stdout + stderr).decode('utf-8', errors='ignore').strip()
    
    # Switch to ADB Keyboard if not already set
    if "com.android.adbkeyboard/.AdbIME" not in current_ime:
        await _async_run_adb(
            adb_prefix + ["shell", "ime", "set", "com.android.adbkeyboard/.AdbIME"]
        )
    
    # Warm up
    await async_type_text("", device_id)
    
    return current_ime


async def async_restore_keyboard(ime: str, device_id: str | None = None) -> None:
    """Restore the original keyboard asynchronously."""
    adb_prefix = _get_adb_prefix(device_id)
    await _async_run_adb(adb_prefix + ["shell", "ime", "set", ime])

