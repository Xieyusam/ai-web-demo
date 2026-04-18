@echo off
echo Starting Python FastAPI server on port 8091...
cd /d "%~dp0server\python"

REM 创建虚拟环境（如果不存在）
if not exist ".venv" (
    python -m venv .venv
)

REM 激活虚拟环境并安装依赖
call .venv\Scripts\activate
pip install -r requirements.txt

REM 启动服务
python main.py
pause
