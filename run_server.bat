@echo off
title Open-AutoGLM Model Server
set HF_ENDPOINT=https://hf-mirror.com
echo Starting Local Model Server...
echo Model will be downloaded on first run (this may take a while).
.\.venv\Scripts\python.exe local_model_server.py
pause
