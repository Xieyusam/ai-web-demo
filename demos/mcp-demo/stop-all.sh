#!/bin/bash
# MCP Demo - 停止所有服务

echo "停止 MCP Demo 所有服务..."

# 停止所有相关进程
pkill -f "python.*main.py" 2>/dev/null || true
pkill -f "node.*server.js" 2>/dev/null || true
pkill -f "python.*agent.py" 2>/dev/null || true
pkill -f "node.*agent.js" 2>/dev/null || true

echo "所有服务已停止。"