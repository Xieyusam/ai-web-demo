"""
Python AI Agent - MCP Client 实现

功能：
1. 接收用户对话
2. 调用 LLM 判断是否需要使用工具
3. 通过 MCP Client 调用 MCP Server 的工具
4. 返回结果给用户

MCP 调用流程：
┌─────────────────────────────────────────────────────────────────┐
│                      AI Agent Service                            │
│   ┌─────────────────────┐    ┌─────────────────────────────┐   │
│   │   AI Agent          │───►│   MCP Server (端口 8100)     │   │
│   │   (MCP Client)      │    │   提供 calculate_bmi 工具    │   │
│   └─────────────────────┘    └─────────────────────────────┘   │
│           │                                                 │
│   ┌───────┴───────┐                                        │
│   │  LLM API     │  ◄── OPENAI_API_KEY / ANTHROPIC_API_KEY │
│   └───────────────┘                                        │
└─────────────────────────────────────────────────────────────────┘

启动：
python agent.py

测试：
curl -X POST http://localhost:8200/chat -H "Content-Type: application/json" -d '{"message":"计算身高170体重65的BMI"}'
"""

import os
import json
import httpx
import uvicorn
from dotenv import load_dotenv

# 加载 .env 文件（从脚本所在目录）
script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(script_dir, '../../.env'))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# =============================================================================
# 配置
# =============================================================================
# 读取环境变量
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY", "")
DEFAULT_PROVIDER = os.environ.get("DEFAULT_PROVIDER", "openai")

# MCP Server 地址
MCP_SERVER_URL = "http://localhost:8100"

# Agent 服务端口
AGENT_PORT = 8200

# =============================================================================
# MCP Client 实现
# =============================================================================
class MCPClient:
    """简单的 MCP Client 实现，用于调用 MCP Server 的工具"""

    def __init__(self, server_url: str):
        self.server_url = server_url
        self.tools = []
        self.httpx_client = httpx.AsyncClient(timeout=30.0)

    async def list_tools(self):
        """调用 tools/list 发现可用工具"""
        response = await self.httpx_client.post(
            f"{self.server_url}/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/list",
                "id": 1
            }
        )
        data = response.json()
        if "result" in data and "tools" in data["result"]:
            self.tools = data["result"]["tools"]
        return self.tools

    async def call_tool(self, tool_name: str, arguments: dict):
        """调用 tools/call 执行工具"""
        response = await self.httpx_client.post(
            f"{self.server_url}/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                },
                "id": 2
            }
        )
        data = response.json()
        if "result" in data and "content" in data["result"]:
            return json.loads(data["result"]["content"][0]["text"])
        return data

    async def close(self):
        await self.httpx_client.aclose()


# =============================================================================
# LLM 调用
# =============================================================================
async def call_llm(provider: str, messages: list, tools: list = None) -> str:
    """调用 LLM API"""

    if provider == "openai" and OPENAI_API_KEY:
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4o",
            "messages": messages,
            "temperature": 0.7
        }
        if tools:
            payload["tools"] = tools

        response = await httpx.AsyncClient().post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60.0
        )
        result = response.json()

        choices = result.get("choices")
        if choices and len(choices) > 0:
            choice = choices[0]
            if choice.get("finish_reason") == "tool_calls":
                return json.dumps(choice["message"]["tool_calls"])
            return choice["message"]["content"]
        return ""

    elif provider == "anthropic" and ANTHROPIC_API_KEY:
        headers = {
            "x-api-key": ANTHROPIC_API_KEY,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
        payload = {
            "model": "claude-sonnet-4-20250514",
            "messages": messages,
            "max_tokens": 1024
        }
        if tools:
            payload["tools"] = tools

        response = await httpx.AsyncClient().post(
            f"{base_url}/v1/messages",
            headers=headers,
            json=payload,
            timeout=60.0
        )
        result = response.json()

        if "content" in result and len(result["content"]) > 0:
            for content in result["content"]:
                if content.get("type") == "text":
                    return content["text"]
                elif content.get("type") == "tool_use":
                    return json.dumps([{"function": content["name"], "arguments": content["input"]}])
        return ""

    elif provider == "minimax" and MINIMAX_API_KEY:
        headers = {
            "Authorization": f"Bearer {MINIMAX_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "MiniMax-M2.7",
            "messages": messages,
            "max_tokens": 1024
        }
        if tools:
            payload["tools"] = tools

        response = await httpx.AsyncClient().post(
            "https://api.minimaxi.com/v1/text/chatcompletion_v2",
            headers=headers,
            json=payload,
            timeout=60.0
        )
        result = response.json()
        print(f"[MiniMax Debug] status={response.status_code}, result={result}")

        if "error" in result:
            return f"MiniMax API Error: {result['error']}"

        # MiniMax native format: choices[0].message.content or tool_calls
        choices = result.get("choices")
        if choices and len(choices) > 0:
            choice = result["choices"][0]
            message = choice.get("message", {})

            # Check for tool_calls first (MiniMax returns tool_calls when it wants to use a tool)
            if "tool_calls" in message and message["tool_calls"]:
                return json.dumps(message["tool_calls"])

            # Then check content
            content = message.get("content", "").strip()
            if content:
                return content

        return "MiniMax returned empty response"


def build_tools_for_llm(mcp_tools: list) -> list:
    """将 MCP 工具格式转换为 LLM 工具格式"""

    openai_tools = []
    for tool in mcp_tools:
        openai_tools.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get("inputSchema", {"type": "object", "properties": {}})
            }
        })
    return openai_tools


# =============================================================================
# AI Agent 实现
# =============================================================================
class AIAgent:
    """AI Agent：处理对话和工具调用"""

    def __init__(self, mcp_client: MCPClient, provider: str = "openai"):
        self.mcp_client = mcp_client
        self.provider = provider
        self.conversation_history = []

    async def chat(self, user_message: str) -> dict:
        """处理用户消息"""

        # 添加用户消息到历史
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        # 发现可用工具
        tools = await self.mcp_client.list_tools()
        llm_tools = build_tools_for_llm(tools)

        # 调用 LLM
        response = await call_llm(self.provider, self.conversation_history, llm_tools)

        # 检查是否需要调用工具
        if response.startswith("[") or (response.startswith("{") and "function" in response):
            try:
                tool_calls = json.loads(response)
                if isinstance(tool_calls, list) and len(tool_calls) > 0:
                    tool_call = tool_calls[0]
                    if "function" in tool_call:
                        func_obj = tool_call["function"]
                        tool_name = func_obj.get("name", "") if isinstance(func_obj, dict) else func_obj
                        raw_args = func_obj.get("arguments", "{}") if isinstance(func_obj, dict) else "{}"

                        # Parse arguments if it's a JSON string
                        if isinstance(raw_args, str):
                            try:
                                arguments = json.loads(raw_args)
                            except:
                                arguments = {}
                        else:
                            arguments = raw_args

                        # 调用 MCP 工具
                        tool_result = await self.mcp_client.call_tool(tool_name, arguments)

                        # 直接返回工具结果，不再进行第二轮 LLM 调用
                        # 因为 MiniMax 对 tool_call_id 有严格要求
                        response_text = f"{tool_name} 执行结果：\n{json.dumps(tool_result, ensure_ascii=False, indent=2)}"

                        self.conversation_history.append({
                            "role": "assistant",
                            "content": response_text
                        })

                        return {
                            "response": response_text,
                            "tool_used": tool_name,
                            "tool_result": tool_result
                        }
            except json.JSONDecodeError:
                pass

        # 普通回复
        self.conversation_history.append({
            "role": "assistant",
            "content": response
        })

        return {
            "response": response,
            "tool_used": None,
            "tool_result": None
        }

    def reset(self):
        """重置对话历史"""
        self.conversation_history = []


# =============================================================================
# FastAPI 应用
# =============================================================================
app = FastAPI(title="Python AI Agent")

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")

# 全局 MCP Client 和 Agent
mcp_client = MCPClient(MCP_SERVER_URL)
agent = AIAgent(mcp_client, DEFAULT_PROVIDER)


class ChatRequest(BaseModel):
    message: str
    provider: str = "openai"


@app.get("/")
async def root():
    """返回演示页面"""
    return FileResponse("static/index.html")


@app.get("/health")
async def health():
    """健康检查端点"""
    return {
        "status": "healthy",
        "service": "Python AI Agent",
        "version": "1.0.0",
        "port": AGENT_PORT,
        "mcp_server": MCP_SERVER_URL,
        "llm_provider": DEFAULT_PROVIDER,
        "has_openai_key": bool(OPENAI_API_KEY),
        "has_anthropic_key": bool(ANTHROPIC_API_KEY)
    }


@app.post("/chat")
async def chat(request: ChatRequest):
    """处理聊天消息"""
    if request.provider:
        agent.provider = request.provider

    result = await agent.chat(request.message)
    return result


@app.post("/reset")
async def reset():
    """重置对话"""
    agent.reset()
    return {"status": "reset"}


@app.get("/tools")
async def list_tools():
    """列出可用工具"""
    tools = await mcp_client.list_tools()
    return {"tools": tools}


if __name__ == "__main__":
    print(f"""
============================================================
Python AI Agent (MCP Client)
============================================================
Agent Port: {AGENT_PORT}
MCP Server: {MCP_SERVER_URL}
LLM Provider: {DEFAULT_PROVIDER}

API Keys:
  OpenAI:    {'✓ 已配置' if OPENAI_API_KEY else '✗ 未配置'}
  Anthropic: {'✓ 已配置' if ANTHROPIC_API_KEY else '✗ 未配置'}

使用说明:
  1. 启动服务: python agent.py
  2. 打开页面: http://localhost:{AGENT_PORT}
  3. 健康检查: http://localhost:{AGENT_PORT}/health
  4. 聊天: POST http://localhost:{AGENT_PORT}/chat

API 端点:
  GET  /           - 演示页面
  GET  /health     - 健康检查
  POST /chat       - 发送消息
  POST /reset      - 重置对话
  GET  /tools      - 列出可用工具

============================================================
    """)

    uvicorn.run(app, host="0.0.0.0", port=AGENT_PORT)