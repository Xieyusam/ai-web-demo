#!/bin/bash
# MCP Demo 启动脚本 - 一键启动所有服务
# 端口分配：
#   8100 - Python MCP Server
#   8101 - Node.js MCP Server
#   8200 - Python AI Agent
#   8201 - Node.js AI Agent

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================"
echo "MCP Demo - 启动所有服务"
echo "============================================================"

# 加载环境变量
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# 停止现有服务
echo "停止现有服务..."
pkill -f "python.*main.py" 2>/dev/null || true
pkill -f "node.*server.js" 2>/dev/null || true
pkill -f "python.*agent.py" 2>/dev/null || true
pkill -f "node.*agent.js" 2>/dev/null || true
sleep 1

# 设置 env 文件路径
ENV_FILE="$SCRIPT_DIR/.env"

# 启动 Python MCP Server (8100)
echo ""
echo "启动 Python MCP Server (端口 8100)..."
cd server/python
python3 -m pip install -q -r requirements.txt 2>/dev/null || true
ANTHROPIC_BASE_URL="$ANTHROPIC_BASE_URL" ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" DEFAULT_PROVIDER="$DEFAULT_PROVIDER" OPENAI_API_KEY="$OPENAI_API_KEY" python3 main.py > /tmp/mcp-python-mcp.log 2>&1 &
cd ../..

# 启动 Node.js MCP Server (8101)
echo "启动 Node.js MCP Server (端口 8101)..."
cd server/node
npm install --silent 2>/dev/null || true
node server.js > /tmp/mcp-node-mcp.log 2>&1 &
cd ../..

# 启动 Python AI Agent (8200)
echo "启动 Python AI Agent (端口 8200)..."
cd server/python
ANTHROPIC_BASE_URL="$ANTHROPIC_BASE_URL" ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" DEFAULT_PROVIDER="$DEFAULT_PROVIDER" OPENAI_API_KEY="$OPENAI_API_KEY" python3 agent.py > /tmp/mcp-python-agent.log 2>&1 &
cd ../..

# 启动 Node.js AI Agent (8201)
echo "启动 Node.js AI Agent (端口 8201)..."
cd server/node
ANTHROPIC_BASE_URL="$ANTHROPIC_BASE_URL" ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" DEFAULT_PROVIDER="$DEFAULT_PROVIDER" OPENAI_API_KEY="$OPENAI_API_KEY" node agent.js > /tmp/mcp-node-agent.log 2>&1 &
cd ../..

# 等待服务启动
sleep 3

echo ""
echo "============================================================"
echo "服务状态检查"
echo "============================================================"

# 检查各服务健康状态
check_service() {
    local name=$1
    local url=$2
    if curl -s --max-time 2 "$url" > /dev/null 2>&1; then
        echo "✓ $name - 运行中"
        return 0
    else
        echo "✗ $name - 未运行 (尝试访问 $url)"
        return 1
    fi
}

check_service "Python MCP Server" "http://localhost:8100/health"
check_service "Node.js MCP Server" "http://localhost:8101/health"
check_service "Python AI Agent" "http://localhost:8200/health"
check_service "Node.js AI Agent" "http://localhost:8201/health"

echo ""
echo "============================================================"
echo "启动完成！"
echo "============================================================"
echo ""
echo "访问地址："
echo "  统一演示页面: file://$SCRIPT_DIR/demo.html"
echo "  或直接打开: http://localhost:8200 (Python Agent)"
echo ""
echo "日志文件："
echo "  Python MCP:   /tmp/mcp-python-mcp.log"
echo "  Node.js MCP:  /tmp/mcp-node-mcp.log"
echo "  Python Agent: /tmp/mcp-python-agent.log"
echo "  Node.js Agent: /tmp/mcp-node-agent.log"
echo ""
echo "停止所有服务: pkill -f 'mcp-demo'"
echo "============================================================"