"""Screen streaming via ADB screencap."""

import io
import os
import subprocess
import time
from typing import Generator, Optional

from PIL import Image

from web.state import app_state
from phone_agent.adb.connection import list_devices


def video_stream_generator() -> Generator[bytes, None, None]:
    """
    Yields MJPEG frames using ADB screencap.
    
    This is a reliable fallback that works with any device.
    Each frame is captured via `adb exec-out screencap -p`.
    
    Yields:
        MJPEG frame bytes with multipart boundaries.
    """
    # Find device
    devices = list_devices()
    if not devices:
        print("No devices found for streaming.")
        # Fallback to black screen
        yield from _yield_placeholder_frames()
        return
    
    device_id = devices[0].device_id
    adb_prefix = ["adb", "-s", device_id]
    
    print(f"Starting ADB Screencap Stream for {device_id}...")
    
    frame_count = 0
    while True:
        try:
            # Capture screenshot via ADB
            result = subprocess.run(
                adb_prefix + ["exec-out", "screencap", "-p"],
                capture_output=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout:
                frame_data = _process_screenshot(result.stdout)
                if frame_data:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')
                    
                    frame_count += 1
                    if frame_count % 30 == 0:
                        print(f"Stream: {frame_count} frames captured.")
            else:
                stderr = result.stderr[:100] if result.stderr else 'unknown'
                print(f"Stream: screencap failed: {stderr}")
                
            # ~10 FPS for preview
            time.sleep(0.1)
            
        except subprocess.TimeoutExpired:
            print("Stream: screencap timeout")
            time.sleep(0.5)
        except Exception as e:
            print(f"Stream Error: {e}")
            time.sleep(1)


def _process_screenshot(png_data: bytes) -> Optional[bytes]:
    """
    Process PNG screenshot data: convert to JPEG, resize, cache.
    
    Args:
        png_data: Raw PNG bytes from screencap.
        
    Returns:
        JPEG bytes or None on error.
    """
    try:
        img = Image.open(io.BytesIO(png_data))
        
        # Convert RGBA to RGB (JPEG doesn't support alpha)
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        
        # ⚠️ IMPORTANT: Save original screen size BEFORE resize
        # This is needed for accurate coordinate mapping in the agent
        app_state.original_screen_size = (img.width, img.height)
        
        # Resize for web preview (smaller = faster)
        max_height = 800
        if img.height > max_height:
            scale = max_height / img.height
            new_size = (int(img.width * scale), max_height)
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Store latest frame for agent (resized for display)
        app_state.latest_frame = img
        
        # Convert to JPEG
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=70)
        return out.getvalue()
        
    except Exception as e:
        print(f"Stream: Image processing error: {e}")
        return None


def _yield_placeholder_frames() -> Generator[bytes, None, None]:
    """Yield black placeholder frames when no device connected."""
    img = Image.new('RGB', (360, 800), color='black')
    out = io.BytesIO()
    img.save(out, format="JPEG")
    frame_data = out.getvalue()
    
    while True:
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')
        time.sleep(1)
