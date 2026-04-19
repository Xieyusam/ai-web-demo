"""
Python MCP Server with SSE Transport

MCP Client-Server Architecture:
┌─────────────────────────────────────────────────────────────┐
│                        Host (Browser/AI)                    │
│   ┌─────────────┐                                           │
│   │ MCP Client  │ ◄──── SSE (HTTP)                         │
│   │ (JS in page)│                                           │
│   └─────────────┘                                           │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│   Python MCP Server (port 8100)                              │
│   ┌─────────────────────────────────────────┐               │
│   │ Tool: get_current_weather(city: str)    │               │
│   │ - FastAPI 模拟 MCP 协议                  │               │
│   │ - Returns fixed weather data            │               │
│   └─────────────────────────────────────────┘               │
└──────────────────────────────────────────────────────────────┘

Transport Layer Choice:
- stdio: 本地进程通信，Claude Desktop 插件用
- SSE:  远程HTTP通信，浏览器/Web服务用 ◄── 本Demo选择

MCP Protocol Overview (JSON-RPC 2.0):
- tools/list: 列出服务器上所有可用工具
- tools/call: 调用指定工具并返回结果
- 消息格式: {"jsonrpc": "2.0", "id": int|str, "method": str, "params": object?}
"""

import asyncio
import json
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
import uvicorn

# =============================================================================
# MCP Server Implementation
# =============================================================================

app = FastAPI(
    title="MCP Weather Server",
    description="A teaching demo MCP server with SSE transport",
    version="1.0.0"
)

# In-memory storage for connected SSE clients (for demo purposes)
# In production, you'd use a proper message queue or pub/sub system
connected_clients: Dict[str, asyncio.Queue] = {}

# =============================================================================
# MCP Tool Definition
# =============================================================================

async def get_current_weather(city: str) -> Dict[str, Any]:
    """
    获取当前天气信息

    Args:
        city: 城市名称

    Returns:
        包含城市、天气、温度和湿度的字典
    """
    # 模拟天气数据（实际项目中会调用外部API）
    weather_data = {
        "city": city,
        "weather": "晴天",
        "temperature": "25°C",
        "humidity": "50%"
    }
    return weather_data


# MCP Protocol: 可用工具列表
# 每个工具定义包含: name(工具名), description(描述), inputSchema(输入参数模式)
MCP_TOOLS = [
    {
        "name": "get_current_weather",
        "description": "获取指定城市的当前天气信息，返回城市名、天气状况、温度和湿度",
        "inputSchema": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称，例如：北京、上海、东京"
                }
            },
            "required": ["city"]
        }
    }
]

# =============================================================================
# MCP Protocol Handlers
# =============================================================================

async def handle_tools_list(params: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    处理 tools/list 请求

    MCP Protocol:
    Request:  {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    Response: {"jsonrpc": "2.0", "id": 1, "result": {"tools": [...]}}
    """
    return MCP_TOOLS


async def handle_tools_call(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    处理 tools/call 请求

    MCP Protocol:
    Request:  {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
               "params": {"name": "get_current_weather", "arguments": {"city": "北京"}}}
    Response: {"jsonrpc": "2.0", "id": 2, "result": {"content": [{"type": "text", "text": "..."}]}}
    """
    if tool_name == "get_current_weather":
        result = await get_current_weather(**arguments)
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, ensure_ascii=False, indent=2)
                }
            ]
        }
    else:
        raise ValueError(f"Unknown tool: {tool_name}")


# =============================================================================
# SSE Endpoint - Server-Sent Events for client notifications
# =============================================================================

@app.get("/sse")
async def sse_endpoint(request: Request):
    """
    SSE endpoint for browser/Web clients

    Server-Sent Events (SSE) 是一种基于HTTP的单向通信协议，
    服务器通过这个端点向浏览器客户端推送事件。

    MCP SSE 流程:
    1. 客户端连接 /sse 端点，建立长连接
    2. 服务器可随时通过此连接向客户端发送事件
    3. 客户端通过 POST /mcp 发送请求

    注意: 这是一个简化的教学演示。
    真正的MCP SSE实现使用更复杂的流式响应机制。
    """
    client_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()
    connected_clients[client_id] = queue

    async def event_generator() -> AsyncGenerator[Dict[str, Any], None]:
        """生成SSE事件流"""
        try:
            # 发送连接建立事件
            yield {
                "event": "connected",
                "data": json.dumps({"client_id": client_id, "status": "connected"})
            }

            # 保持连接并等待消息
            while True:
                try:
                    # 等待消息，超时后发送心跳
                    message = await asyncio.wait_for(queue.get(), timeout=30)
                    yield {
                        "event": "message",
                        "data": json.dumps(message)
                    }
                except asyncio.TimeoutError:
                    # 发送心跳保持连接
                    yield {"event": "heartbeat", "data": json.dumps({"status": "alive"})}
        except asyncio.CancelledError:
            pass
        finally:
            connected_clients.pop(client_id, None)

    return EventSourceResponse(event_generator())


# =============================================================================
# MCP Protocol Endpoint - JSON-RPC over HTTP
# =============================================================================

class MCPRequest(BaseModel):
    """MCP JSON-RPC 2.0 请求格式"""
    jsonrpc: str = "2.0"
    id: Union[int, str]
    method: str
    params: Optional[Dict[str, Any]] = None


@app.post("/mcp")
async def mcp_endpoint(request: MCPRequest):
    """
    MCP Protocol Endpoint

    处理 MCP JSON-RPC 2.0 请求:
    - tools/list: 列出所有可用工具
    - tools/call: 调用指定工具

    请求格式:
    {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",           // 或 "tools/call"
        "params": {}                       // tools/call 时需要 name 和 arguments
    }

    响应格式:
    {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {...}                    // 成功时
    }
    或
    {
        "jsonrpc": "2.0",
        "id": 1,
        "error": {...}                     // 失败时
    }
    """
    try:
        if request.method == "tools/list":
            result = await handle_tools_list(request.params)
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request.id,
                "result": {"tools": result}
            })

        elif request.method == "tools/call":
            if not request.params or "name" not in request.params:
                raise ValueError("Missing 'name' in params")
            tool_name = request.params["name"]
            arguments = request.params.get("arguments", {})
            result = await handle_tools_call(tool_name, arguments)
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request.id,
                "result": result
            })

        else:
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request.id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {request.method}"
                }
            }, status_code=404)

    except ValueError as e:
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": request.id,
            "error": {
                "code": -32602,
                "message": str(e)
            }
        }, status_code=400)
    except Exception as e:
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": request.id,
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }, status_code=500)


# =============================================================================
# Health Check Endpoint
# =============================================================================

@app.get("/health")
async def health_check():
    """
    健康检查端点

    用于验证服务器是否正常运行
    """
    return {
        "status": "healthy",
        "service": "MCP Weather Server",
        "version": "1.0.0",
        "port": 8100
    }


# =============================================================================
# Server Startup
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("MCP Weather Server with SSE Transport")
    print("=" * 60)
    print("Server running on http://localhost:8100")
    print("")
    print("Endpoints:")
    print("  GET  /sse   - SSE endpoint for browser clients")
    print("  POST /mcp   - MCP protocol endpoint (JSON-RPC)")
    print("  GET  /health - Health check")
    print("")
    print("Available Tools:")
    for tool in MCP_TOOLS:
        print(f"  - {tool['name']}: {tool['description']}")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8100)