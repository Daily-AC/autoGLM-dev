@echo off
title Open-AutoGLM Agent
echo Starting Open-AutoGLM Agent...
python main.py --base-url http://localhost:8000/v1 --model "autoglm-phone-9b"
pause
