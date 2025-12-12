import subprocess
import socket
import time
import os
import sys
import threading

SCRCPY_SERVER_PATH = "scrcpy-server.jar"
DEVICE_SERVER_PATH = "/data/local/tmp/scrcpy-server.jar"
SOCKET_NAME = "scrcpy"
PORT = 27183

def debug():
    print(f"Checking {SCRCPY_SERVER_PATH}...")
    if not os.path.exists(SCRCPY_SERVER_PATH):
        print("FAIL: jar not found")
        return

    print("Pushing jar...")
    subprocess.run(["adb", "push", SCRCPY_SERVER_PATH, DEVICE_SERVER_PATH], check=True)
    
    print("Setting up forward...")
    subprocess.run(["adb", "forward", f"tcp:{PORT}", f"localabstract:{SOCKET_NAME}"], check=True)
    
    cmd = [
        "adb", "shell", 
        f"CLASSPATH={DEVICE_SERVER_PATH}", 
        "app_process", "/", "com.genymobile.scrcpy.Server", 
        "2.3",
        "log_level=debug",
        "max_size=720",
        "bit_rate=2000000",
        "max_fps=30",
        "tunnel_forward=true",
        "control=false",
        "audio=false",
        "raw_stream=true"
    ]
    
    print(f"Running: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    time.sleep(1)
    if proc.poll() is not None:
        print("Server process died!")
        print("STDERR:", proc.stderr.read().decode())
        print("STDOUT:", proc.stdout.read().decode())
        return

    print("Process alive, attempting socket connect...")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('127.0.0.1', PORT))
        print("Socket connected!")
        
        # Reader thread to show stdout/stderr from device
        def log_reader(pipe, name):
            for line in iter(pipe.readline, b''):
                print(f"[{name}] {line.decode().strip()}")
        
        t1 = threading.Thread(target=log_reader, args=(proc.stdout, "STDOUT"), daemon=True)
        t2 = threading.Thread(target=log_reader, args=(proc.stderr, "STDERR"), daemon=True)
        t1.start()
        t2.start()

        print("Reading device name...")
        name = s.recv(64)
        print(f"Device Name: {name}")
        
        print("Reading first 128 bytes of stream...")
        data = s.recv(128)
        print(f"Hex Dump: {data.hex()}")
        
        # Check for H264 start code (00 00 00 01)
        if b'\x00\x00\x00\x01' in data:
            print("Found H.264 Start Code!")
        else:
            print("WARNING: No H.264 Start Code found in first 128 bytes.")
        
    except Exception as e:
        print(f"Connection failed: {e}")
        if proc.poll() is not None:
             print("STDERR:", proc.stderr.read().decode())
    finally:
        proc.kill()
        
if __name__ == "__main__":
    debug()
