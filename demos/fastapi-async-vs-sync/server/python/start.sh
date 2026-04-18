#!/bin/bash
echo "Starting Python FastAPI server on port 8091..."

cd "$(dirname "$0")"

# 创建虚拟环境（如果不存在）
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

# 激活虚拟环境并安装依赖
source .venv/bin/activate
pip install -r requirements.txt

# 启动服务
python main.py
