# MCP 协议教学 Demo — 设计规格

> **MVP:** MCP (Model Context Protocol) 协议教学演示
> **Status:** 设计中
> **Date:** 2026-04-18
> **面试目标:** 两天后面试，简历写了"熟悉 MCP 协议"

---

## 1. Concept & Vision

一个极简的 MCP 协议教学 Demo，通过浏览器可视化 + 代码注释，让学生理解：
- MCP 的 Client-Server 架构
- `stdio` 传输（本地进程）vs `SSE` 传输（远程 HTTP）的适用场景
- MCP 工具调用 vs 代码写死 `@tool` 装饰器的区别

目标：面试时能现场运行 Demo，并解释 MCP 协议原理。

---

## 2. Project Structure

```
ai-web-demo/.worktrees/feature-mcp-demo/
demos/mcp-demo/
├── demo.html                         # 统一教学页面（Vue3 CDN + Tailwind CDN）
│                                       # 点击触发，连接 Python/Node MCP Client，展示结果
├── server/
│   ├── python/
│   │   ├── main.py                  # MCP Server（mcp SDK + SSE，端口 8100）
│   │   ├── client.py                 # MCP Client（mcp SDK，调 Server）
│   │   ├── requirements.txt
│   │   └── .venv/                    # Python 虚拟环境
│   └── node/
│       ├── server.js                 # MCP Server（@modelcontextprotocol/sdk + SSE，端口 8101）
│       ├── client.js                 # MCP Client
│       ├── package.json
│       └── .venv/                    # Node 虚拟环境
└── docs/
    └── README.md                     # 面试要点 + MCP 原理 + 对比表格
```

**端口分配：**
- Python MCP Server SSE: `http://localhost:8100`
- Node.js MCP Server SSE: `http://localhost:8101`
- demo.html: 直接打开文件或通过任意服务托管

---

## 3. MCP 核心概念

### 3.1 MCP 是什么？

MCP (Model Context Protocol) 是一个标准协议，让 AI 模型（如 Claude、GPT）能调用外部工具。

```
传统：AI → 代码写死的工具（硬编码）
MCP：  AI → MCP Client → MCP Server → 外部工具（标准化）
```

### 3.2 Client-Server 架构

```
┌─────────────────────────────────────────────────────────────┐
│                        Host (AI Application)               │
│                                                             │
│   ┌─────────────┐         ┌─────────────┐                   │
│   │ MCP Client  │◄───────►│  Tool Code  │                   │
│   └──────┬──────┘         └─────────────┘                   │
│          │                                                    │
│          │ stdio / SSE                                        │
└──────────┼──────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│                      MCP Server                              │
│   ┌─────────────┐         ┌─────────────┐                  │
│   │  Tool Handler │◄──────►│  External   │                  │
│   │  (get_weather)│        │  API / DB   │                  │
│   └─────────────┘         └─────────────┘                  │
└──────────────────────────────────────────────────────────────┘
```

**架构要点：**
- Host = AI 应用（如 Claude Desktop）
- Client = MCP SDK，负责和 Server 通信
- Server = 工具提供者（如天气 API）
- stdio = 本地进程间通信（Client 和 Server 在同一台机器）
- SSE = 远程 HTTP 通信（Client 和 Server 通过 HTTP）

### 3.3 传输层对比

| 传输方式 | 原理 | 适用场景 | 示例 |
|----------|------|----------|------|
| **stdio** | 标准输入/输出，本地进程通信 | Claude Desktop 插件、本地工具 | `python server.py` 作为子进程启动 |
| **SSE** | HTTP + Server-Sent Events，长连接 | 远程服务、Web 前端 | `http://localhost:8100/sse` |

**本 Demo 用 SSE 传输**，原因：
1. 可以被浏览器 JS 直接调用（展示更直观）
2. 适合教学，能看到 HTTP 请求
3. 真实场景中，很多 MCP Server 部署为远程服务

---

## 4. 工具设计

### 4.1 get_current_weather

**参数：**
```json
{
  "city": "string"  // 城市名，如 "北京"
}
```

**返回值：**
```json
{
  "city": "北京",
  "weather": "晴天",
  "temperature": "25°C"
}
```

---

## 5. demo.html 页面设计

### 5.1 页面布局

```
┌──────────────────────────────────────────────────────────────────┐
│  MCP 协议教学 Demo                                                 │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────┐  ┌─────────────────────────┐       │
│  │  Python MCP Server      │  │  Node.js MCP Server     │       │
│  │  端口: 8100             │  │  端口: 8101             │       │
│  │                         │  │                         │       │
│  │  [连接 Server]          │  │  [连接 Server]          │       │
│  │  [获取工具列表]          │  │  [获取工具列表]          │       │
│  │                         │  │                         │       │
│  │  工具列表:               │  │  工具列表:               │       │
│  │  - get_current_weather  │  │  - get_current_weather  │       │
│  │                         │  │                         │       │
│  │  调用结果:               │  │  调用结果:               │       │
│  │  ┌───────────────────┐  │  │  ┌───────────────────┐  │       │
│  │  │ {"city": "北京",  │  │  │  │ {"city": "北京",  │  │       │
│  │  │  "weather": "晴天"│  │  │  │  "weather": "晴天"│  │       │
│  │  │  "temperature":   │  │  │  │  "temperature":   │  │       │
│  │  │  "25°C"}          │  │  │  │  "25°C"}          │  │       │
│  │  └───────────────────┘  │  │  └───────────────────┘  │       │
│  └─────────────────────────┘  └─────────────────────────┘       │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│  MCP vs @tool 装饰器 对比                                         │
│  ┌────────────────────────┬────────────────────────┐             │
│  │  MCP 协议               │  @tool 装饰器          │             │
│  ├────────────────────────┼────────────────────────┤             │
│  │  标准化接口              │  框架绑定               │             │
│  │  跨语言                 │  只在同框架内           │             │
│  │  可热插拔               │  硬编码                │             │
│  │  AI 可动态发现工具       │  编译时确定            │             │
│  └────────────────────────┴────────────────────────┘             │
└──────────────────────────────────────────────────────────────────┘
```

---

## 6. 代码注释要点（面试解释）

### 6.1 MCP Client-Server 交互流程

```python
# 1. Server 启动，注册工具
@mcp_server.list_tools()
async def list_tools():
    return [Tool(name="get_current_weather", ...)]

# 2. Client 连接 Server
client = MCPClient()
await client.connect(sse_url)

# 3. Client 获取可用工具
tools = await client.list_tools()

# 4. Client 调用工具
result = await client.call_tool("get_current_weather", {"city": "北京"})
```

### 6.2 stdio vs SSE 适用场景

```python
# stdio：本地进程，适合 Claude Desktop 插件
# Claude Desktop 调用时，MCP Client 在 Claude 进程内，
# Server 作为子进程启动，通过 stdin/stdout 通信

# SSE：远程 HTTP，适合 Web 服务
# Client 在浏览器或远程服务器上，
# Server 部署在云端，通过 HTTP SSE 连接
```

---

## 7. 技术选型

| 组件 | Python | Node.js |
|------|--------|---------|
| MCP SDK | `mcp` 官方库 | `@modelcontextprotocol/sdk` |
| 传输层 | SSE (FastAPI) | SSE (Express) |
| 工具实现 | `@mcp.server.tool` | `server.tool()` |

---

## 8. 验收标准

1. **页面可运行**：打开 demo.html，点击按钮能看到调用结果
2. **代码可解释**：面试能说出 MCP 的 Client-Server 架构
3. **对比表格能背**：MCP vs @tool 装饰器的 4 点区别
4. **传输层能讲清**：stdio 和 SSE 分别用在什么场景

---

## 9. 文件清单

```
demos/mcp-demo/
├── demo.html                      # 统一教学页面
├── server/
│   ├── python/
│   │   ├── main.py              # MCP Server (mcp SDK + SSE)
│   │   ├── client.py            # MCP Client (独立运行测试)
│   │   ├── requirements.txt
│   │   └── .venv/
│   └── node/
│       ├── server.js            # MCP Server
│       ├── client.js            # MCP Client
│       ├── package.json
│       └── .venv/
└── docs/
    └── README.md                 # 面试要点
```
