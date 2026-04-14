@echo off
echo Starting Python server...
cd /d "%~dp0server\python"
call .venv\Scripts\activate
python server.py
