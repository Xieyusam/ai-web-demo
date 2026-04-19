# MCP 协议教学 Demo

通过可视化 Demo + 代码演示，理解 MCP (Model Context Protocol) 协议的原理。

---

## 目录

1. [快速开始](#快速开始)
2. [MCP 核心概念](#mcp-核心概念)
3. [MCP SDK 标准写法](#mcp-sdk-标准写法)
4. [AI Agent 调用示例](#ai-agent-调用示例)
5. [面试要点](#面试要点)

---

## 快速开始

### 一键启动（推荐）

```bash
cd demos/mcp-demo
./start-all.sh
```

启动 4 个服务：
| 服务 | 端口 | 说明 |
|------|------|------|
| Python MCP Server | 8100 | MCP 工具提供者 |
| Node.js MCP Server | 8101 | MCP 工具提供者 |
| Python AI Agent | 8200 | AI Agent (MCP Client) |
| Node.js AI Agent | 8201 | AI Agent (MCP Client) |

### 打开演示页面

1. **统一页面**：直接打开 `demo.html`
2. **Python AI Agent**：http://localhost:8200/
3. **Node.js AI Agent**：http://localhost:8201/

### 健康检查

```bash
# MCP Servers
curl http://localhost:8100/health  # Python MCP
curl http://localhost:8101/health  # Node.js MCP

# AI Agents
curl http://localhost:8200/health  # Python Agent
curl http://localhost:8201/health  # Node.js Agent
```

### 停止服务

```bash
./stop-all.sh
# 或手动停止
pkill -f "python.*main.py"
pkill -f "node.*server.js"
pkill -f "python.*agent.py"
pkill -f "node.*agent.js"
```

---

## MCP 核心概念

### 什么是 MCP？

MCP (Model Context Protocol) 是 AI 应用连接外部工具的标准化协议，由 Anthropic 提出。

```
传统方式：AI → 代码写死的工具（硬编码）
MCP 方式：AI → MCP Client → MCP Server → 外部工具（标准化）
```

### Client-Server 架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      AI Agent Service                            │
│   ┌─────────────────────┐    ┌─────────────────────────────┐   │
│   │   AI Agent          │───►│   MCP Server                 │   │
│   │   (MCP Client)      │    │   提供 calculate_bmi 工具   │   │
│   └─────────────────────┘    └─────────────────────────────┘   │
│           │                                                 │
│   ┌───────┴───────┐                                        │
│   │  LLM API     │  ◄── OPENAI_API_KEY / MINIMAX_API_KEY  │
│   └───────────────┘                                        │
└─────────────────────────────────────────────────────────────────┘
```

### 传输层：stdio vs SSE

| 传输方式 | 原理 | 适用场景 |
|----------|------|----------|
| **stdio** | 本地进程 stdin/stdout | Claude Desktop 插件 |
| **SSE** | HTTP + Server-Sent Events | Web 服务、远程调用 |

---

## MCP SDK 标准写法

### Python (fastmcp SDK)

```python
from fastmcp import FastMCP

mcp = FastMCP("bmi-server")

@mcp.tool()
def calculate_bmi(height_cm: float, weight_kg: float) -> dict:
    bmi = weight_kg / (height_cm / 100) ** 2
    return {"bmi": round(bmi, 2), "category": "正常", ...}
```

### Node.js (@modelcontextprotocol/sdk)

```javascript
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';

const server = new McpServer({ name: 'bmi-server', version: '1.0.0' });

server.tool(
  'calculate_bmi',
  '计算 BMI',
  { height_cm: z.number(), weight_kg: z.number() },
  async ({ height_cm, weight_kg }) => {
    const bmi = weight_kg / Math.pow(height_cm / 100, 2);
    return { content: [{ type: 'text', text: JSON.stringify({bmi}) }] };
  }
);
```

---

## AI Agent 调用示例

### 发送对话请求

```bash
# Python Agent
curl -X POST http://localhost:8200/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"计算身高170体重65的BMI","provider":"minimax"}'

# Node.js Agent
curl -X POST http://localhost:8201/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"计算身高170体重65的BMI","provider":"minimax"}'
```

### JSON-RPC 格式

**tools/list：**
```json
{"jsonrpc":"2.0","method":"tools/list","id":1}
```

**tools/call：**
```json
{"jsonrpc":"2.0","method":"tools/call","params":{"name":"calculate_bmi","arguments":{"height_cm":170,"weight_kg":65}},"id":2}
```

---

## 环境变量配置

在 `.env` 文件中设置：

```bash
# OpenAI
OPENAI_API_KEY=sk-your-key

# MiniMax (推荐)
MINIMAX_API_KEY=your-minimax-key

# 默认提供商 (openai / anthropic / minimax)
DEFAULT_PROVIDER=minimax
```

---

## 面试要点

### Q1: "MCP 的 Client-Server 架构是怎样的？"

**答：**
- **Host**：AI 应用（如 Claude Desktop、自己的 AI Agent）
- **Client**：MCP SDK，和 Server 通信，发现/调用工具
- **Server**：工具提供者（如 BMI 计算）

### Q2: "MCP 和直接调 API 有什么区别？"

| 对比 | 直接 API 调用 | MCP |
|------|---------------|-----|
| 接口 | 定制化 | 标准化 |
| AI 感知 | AI 不知道有哪些工具 | AI 自动发现工具 |
| 动态性 | 硬编码 | 可热插拔 |

### Q3: "什么时候用 stdio，什么时候用 SSE？"

- **stdio**：本地进程通信，Claude Desktop 插件用
- **SSE**：远程 HTTP 通信，Web 服务用

### Q4: "在同一个 AI Agent 服务内，如何调用 MCP？"

```
AI Agent → MCP Client → MCP Server → 工具
                ↓
           LLM API (提供智能决策)
```

AI Agent 会：
1. 发现可用工具 (`tools/list`)
2. 让 LLM 判断是否需要调用工具
3. 调用工具 (`tools/call`)
4. 将结果返回给 LLM 生成最终回复

---

## 文件结构

```
demos/mcp-demo/
├── .env                    # 环境变量
├── .env.example            # 环境变量模板
├── demo.html               # 统一演示页面
├── start-all.sh            # 启动全部服务
├── stop-all.sh             # 停止全部服务
├── docs/
│   └── README.md           # 本文档
└── server/
    ├── python/
    │   ├── main.py         # MCP Server (8100)
    │   ├── agent.py        # AI Agent (8200)
    │   ├── requirements.txt
    │   └── static/
    │       └── index.html
    └── node/
        ├── server.js       # MCP Server (8101)
        ├── agent.js        # AI Agent (8201)
        ├── package.json
        └── static/
            └── index.html
```