# MCP (Model Context Protocol) 教学演示

## 快速开始

### 启动 Python 服务器 (port 8100)

```bash
cd demos/mcp-demo/server/python
source .venv/bin/activate  # 激活虚拟环境
python main.py
```

服务器启动后访问:
- MCP 端点: `POST http://localhost:8100/mcp`
- SSE 端点: `GET http://localhost:8100/sse`
- 健康检查: `GET http://localhost:8100/health`

### 启动 Node.js 服务器 (port 8101)

```bash
cd demos/mcp-demo/server/node
npm install  # 仅首次
node server.js
```

服务器启动后访问:
- MCP 端点: `POST http://localhost:8101/mcp`
- SSE 端点: `GET http://localhost:8101/sse`
- 健康检查: `GET http://localhost:8101/health`

---

## MCP 核心概念

### 什么是 MCP (Model Context Protocol)?

MCP 是 Anthropic 提出的开放协议，用于标准化 AI 模型与外部工具/数据源的通信。它采用 **Client-Server 架构**，允许 AI 应用动态发现和调用外部工具。

**核心特点:**
- **开放标准**: 任何人都可以实现 MCP 服务器
- **动态发现**: 客户端可运行时查询可用工具
- **热插拔**: 无需修改客户端代码即可添加/移除工具
- **语言无关**: 可用任何语言实现服务器

### Client-Server 架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Host (浏览器/AI 应用)                       │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                      MCP Client (SDK)                          ││
│  │                                                                  ││
│  │   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐   ││
│  │   │  tools/list  │────▶│  tools/call  │────▶│   results    │   ││
│  │   └──────────────┘     └──────────────┘     └──────────────┘   ││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
                    │                                    ▲
                    │ stdio / SSE                        │
                    ▼                                    │
┌─────────────────────────────────────────────────────────────────────┐
│                        MCP Server (任选语言)                         │
│                                                                      │
│   ┌──────────────────────────────────────────────────────────────┐  │
│   │                      Tool Registry                            │  │
│   │                                                               │  │
│   │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │  │
│   │   │ get_weather  │  │  search_db   │  │ call_api     │  ...  │  │
│   │   └──────────────┘  └──────────────┘  └──────────────┘       │  │
│   └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 传输层: stdio vs SSE 对比

| 特性 | stdio | SSE (Server-Sent Events) |
|------|-------|---------------------------|
| **通信方式** | 标准输入/输出流 | HTTP 长连接 |
| **使用场景** | 本地进程通信、桌面插件 | 远程服务、Web 应用 |
| **典型客户端** | Claude Desktop 插件 | 浏览器 Web 应用 |
| **连接方式** | 子进程 fork/exec | HTTP 请求 |
| **双向通信** | 否 (单向) | 否 (单向) |
| **防火墙友好** | 否 | 是 (使用标准 HTTP) |
| **延迟** | 低 | 中等 |
| **实现复杂度** | 低 | 中 |
| **本 Demo** | - | Python:8100, Node:8101 |

> **注意**: 两者都是单向通信。stdio 通过 stdin/stdout，SSE 通过 HTTP POST + SSE 流。

---

## 面试要点

### Q1: MCP 的 Client-Server 架构是怎样的？

**答:**

MCP 采用标准的 C/S 架构:

1. **Host (宿主环境)**: 运行的 AI 应用或浏览器，负责管理 MCP Client
2. **MCP Client**: 嵌入在 Host 中的 SDK，负责与 MCP Server 通信
3. **MCP Server**: 独立进程，暴露一组工具 (Tools) 给 Client 调用

**通信流程:**
```
Host ---> MCP Client ---> MCP Server (tools/list) 获取可用工具列表
Host ---> MCP Client ---> MCP Server (tools/call) 调用具体工具
Host <--- MCP Client <--- MCP Server 返回执行结果
```

**核心方法:**
- `tools/list`: 列出服务器所有可用工具
- `tools/call`: 调用指定工具并传递参数

---

### Q2: MCP 和直接调 API 有什么区别？

**答:**

| 维度 | MCP | 直接 API 调用 |
|------|-----|--------------|
| **接口标准化** | 统一的 JSON-RPC 2.0 协议 | 各服务自定义格式 |
| **动态发现** | 支持运行时查询可用工具 | 需要预先知道 API |
| **工具描述** | 自带 schema 描述 | 需要额外文档 |
| **错误处理** | 标准化的错误码 | 各家不同 |
| **可扩展性** | 热插拔，无需修改客户端 | 需要代码变更 |
| **适用场景** | AI Agent 多工具场景 | 固定 API 集成 |

**MCP 的优势:**
- AI 可自主发现和选择工具
- 一次实现，多个客户端复用
- 工具提供者可独立发布更新

---

### Q3: 什么时候用 stdio，什么时候用 SSE？

**答:**

| 场景 | 推荐传输层 | 原因 |
|------|-----------|------|
| Claude Desktop 插件 | stdio | 本地进程通信，无需网络 |
| 浏览器 Web 应用 | SSE | HTTP 协议，防火墙友好 |
| 远程服务集成 | SSE | 基于 HTTP，易于部署 |
| 工具需要长期运行 | SSE | HTTP 超时控制更灵活 |
| 简单脚本/测试 | stdio | 实现简单，延迟低 |

**本 Demo 选择 SSE 的原因:**
- 便于在浏览器中演示
- 更容易部署到服务器
- 教学目的更直观

---

### Q4: MCP 的 JSON-RPC 2.0 消息格式是怎样的？

**答:**

MCP 使用 JSON-RPC 2.0 作为消息格式规范:

**请求格式:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list",
  "params": {}
}
```

**tools/call 请求示例:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "get_current_weather",
    "arguments": {
      "city": "北京"
    }
  }
}
```

**成功响应:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "get_current_weather",
        "description": "获取天气",
        "inputSchema": { ... }
      }
    ]
  }
}
```

**错误响应:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32602,
    "message": "Invalid params"
  }
}
```

---

### Q5: MCP Server 如何实现热插拔？

**答:**

"热插拔"指的是在不停止 MCP Client 的情况下，动态添加、移除或更新工具。

**实现方式:**

1. **工具注册表 (Tool Registry)**: Server 维护一个工具列表
2. **动态发现**: Client 通过 `tools/list` 实时获取最新工具列表
3. **重启 Server**: 工具变更后重启 Server，Client 重新查询即可

**本 Demo 示例:**
```python
MCP_TOOLS = [
    {
        "name": "get_current_weather",
        "description": "获取指定城市的当前天气信息",
        "inputSchema": { ... }
    }
]

async def handle_tools_list(params):
    return MCP_TOOLS  # 动态返回当前注册的工具
```

**实际生产环境建议:**
- 使用服务注册中心 (Consul, etcd)
- 实现工具的版本管理
- 添加认证和限流

---

## MCP vs @tool 装饰器

### @tool 装饰器 (以 Claude SDK 为例)

```python
from anthropic import Anthropic

client = Anthropic()

@client.tool()
def get_weather(city: str) -> str:
    """获取城市天气"""
    return f"{city} 今天晴天，25°C"
```

### 对比表格

| 维度 | MCP | @tool 装饰器 |
|------|-----|------------|
| **接口标准** | 开放协议 (JSON-RPC 2.0) | SDK 特定 (厂商绑定) |
| **动态发现** | 支持，运行时查询 `tools/list` | 不支持，编译时确定 |
| **热插拔** | 支持，Server 独立部署 | 不支持，需要重启应用 |
| **多客户端复用** | 是，一次实现多处使用 | 否，各 SDK 各自实现 |
| **协议复杂度** | 中等，需要实现协议解析 | 低，装饰器即实现 |
| **适用场景** | Agent 多工具、多方集成 | 单应用、单一 SDK |
| **调试工具** | 通用 (任何 MCP Client) | 专用 (厂商提供) |
| **第三方生态** | 已有大量开源 Server | 依赖 SDK 厂商 |
| **版本管理** | Server 版本与 Client 分离 | 一起版本化 |

### 何时选择 MCP

**选择 MCP 当:**
- 需要集成多个外部工具
- 工具提供方独立于 AI 应用开发
- 希望工具可被多个 AI 应用复用
- 需要动态控制可用工具

**选择 @tool 当:**
- 工具与 AI 应用紧耦合
- 简单场景，不需要标准化
- 不想引入额外协议复杂度

---

## 代码示例

### MCP 调用流程

本 Demo 包含一个完整的 MCP 演示页面: `demos/mcp-demo/demo.html`

#### 1. 初始化 SSE 连接

```javascript
// 建立 SSE 连接接收服务器事件
const eventSource = new EventSource('http://localhost:8100/sse');

eventSource.addEventListener('connected', (event) => {
    console.log('SSE connected:', JSON.parse(event.data));
});

// 接收心跳
eventSource.addEventListener('heartbeat', (event) => {
    console.log('Heartbeat:', JSON.parse(event.data));
});
```

#### 2. 调用 tools/list

```javascript
async function listTools() {
    const response = await fetch('http://localhost:8100/mcp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            jsonrpc: "2.0",
            id: 1,
            method: "tools/list",
            params: {}
        })
    });

    const data = await response.json();
    console.log('Available tools:', data.result.tools);
    return data.result.tools;
}
```

#### 3. 调用 tools/call

```javascript
async function callTool(name, arguments_) {
    const response = await fetch('http://localhost:8100/mcp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            jsonrpc: "2.0",
            id: 2,
            method: "tools/call",
            params: {
                name: name,
                arguments: arguments_
            }
        })
    });

    const data = await response.json();
    return data.result;
}
```

#### 4. 完整示例

```javascript
async function main() {
    // 1. 列出可用工具
    const tools = await listTools();
    console.log('Tools:', tools);

    // 2. 调用 get_current_weather 工具
    const result = await callTool('get_current_weather', { city: '北京' });
    console.log('Weather result:', result);

    // 3. 解析返回内容
    const content = JSON.parse(result.content[0].text);
    console.log('Parsed:', content);
    // Output: { city: "北京", weather: "晴天", temperature: "25°C", humidity: "50%" }
}

main();
```

### Python Server 实现要点

```python
# MCP Server 必须实现两个核心端点:

# 1. GET /sse - SSE 连接端点
#    客户端通过此端点建立长连接，接收服务器推送

# 2. POST /mcp - MCP 协议端点
#    处理 JSON-RPC 2.0 请求

@app.post("/mcp")
async def mcp_endpoint(request: MCPRequest):
    if request.method == "tools/list":
        # 返回工具列表
        return {"jsonrpc": "2.0", "id": request.id, "result": {"tools": MCP_TOOLS}}

    elif request.method == "tools/call":
        # 调用具体工具
        tool_name = request.params["name"]
        arguments = request.params.get("arguments", {})
        result = await handle_tools_call(tool_name, arguments)
        return {"jsonrpc": "2.0", "id": request.id, "result": result}
```

### 工具定义 schema

```json
{
    "name": "get_current_weather",
    "description": "获取指定城市的当前天气信息",
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
```

---

## 更多资源

- [MCP 官方文档](https://modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP JavaScript SDK](https://github.com/modelcontextprotocol/typescript-sdk)
