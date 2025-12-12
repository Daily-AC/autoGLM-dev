import uvicorn
import webbrowser
import threading
import sys
import os

if __name__ == "__main__":
    print("Launching Open-AutoGLM Web Console...")
    
    # Open Browser after short delay
    threading.Timer(1.5, lambda: webbrowser.open("http://localhost:8000")).start()
    
    # Run Uvicorn
    # Use 'web_app:app' string to enable hot reload if needed during dev, 
    # but for production/launcher use imported app or string.
    uvicorn.run("web_app:app", host="0.0.0.0", port=8000, reload=False)
