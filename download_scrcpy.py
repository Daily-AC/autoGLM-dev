import os
import requests

URL = "https://github.com/Genymobile/scrcpy/releases/download/v2.3/scrcpy-server-v2.3"
DEST = "scrcpy-server.jar"

def download():
    print(f"Downloading {URL}...")
    try:
        r = requests.get(URL, stream=True)
        r.raise_for_status()
        with open(DEST, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Downloaded to {os.path.abspath(DEST)}")
        print(f"Size: {os.path.getsize(DEST)} bytes")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    download()
