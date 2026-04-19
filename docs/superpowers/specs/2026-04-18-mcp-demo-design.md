# MCP 协议教学 Demo — 设计规格（修订版）

> **MVP:** MCP (Model Context Protocol) BMI 计算服务教学演示
> **Status:** 设计中
> **Date:** 2026-04-18
> **面试目标:** 两天后面试，简历写了"熟悉 MCP 协议"

---

## 1. Concept & Vision

一个真实的 MCP 协议教学 Demo，展示：
- 如何用官方 MCP SDK 编写规范的 MCP Server
- MCP Server 和 MCP Client 的真实调用关系
- 在同一个 AI Agent 服务内，如何调用本服务的 MCP Server
- BMI 计算作为示例工具（更贴合面试场景）

目标：面试时能展示真实代码，解释 MCP 的 Client-Server 架构原理。

---

## 2. MCP 核心概念

### 2.1 MCP 是什么？

MCP (Model Context Protocol) 是 AI 应用连接外部工具的标准化协议。

```
┌─────────────────────────────────────────────────────────────────┐
│                      AI Application (Host)                        │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                    MCP Client                             │   │
│   │   1. 发现工具 → tools/list                               │   │
│   │   2. 调用工具 → tools/call                               │   │
│   └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                               │
                               │ stdio (本地) / SSE (远程)
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      MCP Server                                  │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  @mcp.tool() / server.tool()                           │   │
│   │  BMI 计算工具: calculate_bmi(height, weight)           │   │
│   └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 同服务内调用场景

```
┌─────────────────────────────────────────────────────────────────┐
│                      AI Agent Service                            │
│   ┌─────────────────────┐    ┌─────────────────────────────┐   │
│   │   MCP Client        │───►│   MCP Server                │   │
│   │   (调用工具)         │    │   (提供 BMI 计算工具)        │   │
│   └─────────────────────┘    └─────────────────────────────┘   │
│           ▲                                                 │
│           │                                                 │
│   ┌───────┴───────┐                                        │
│   │  LLM (API)    │  ◄── 这里可以用模拟的 API key          │
│   └───────────────┘                                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Project Structure

```
demos/mcp-demo/
├── demo.html                         # 统一教学页面（直接打开）
├── start-python.sh                   # Python 服务启动脚本
├── start-node.sh                     # Node.js 服务启动脚本
├── server/
│   ├── python/
│   │   ├── main.py                  # MCP Server (fastmcp SDK)
│   │   ├── client_demo.py           # MCP Client 演示（同服务内调用）
│   │   ├── requirements.txt
│   │   ├── start.sh                 # Python 启动脚本
│   │   └── static/index.html        # Python 版演示页面
│   └── node/
│       ├── server.js               # MCP Server (@modelcontextprotocol/sdk)
│       ├── client_demo.js           # MCP Client 演示
│       ├── package.json
│       ├── start.sh                 # Node.js 启动脚本
│       └── static/index.html        # Node.js 版演示页面
└── docs/
    └── README.md                   # 面试要点 + 教学文档
```

**端口分配：**
- Python MCP Server: `http://localhost:8100`
- Node.js MCP Server: `http://localhost:8101`

---

## 4. 工具设计：BMI 计算

### 4.1 calculate_bmi

**参数：**
```json
{
  "height_cm": 170,    // 身高（厘米）
  "weight_kg": 65      // 体重（公斤）
}
```

**返回值：**
```json
{
  "bmi": 22.49,
  "category": "正常",
  "suggestion": "继续保持健康的饮食和运动习惯"
}
```

**BMI 分类标准（中国标准）：**
| BMI 范围 | 分类 |
|----------|------|
| < 18.5 | 偏瘦 |
| 18.5 - 24 | 正常 |
| 24 - 28 | 偏胖 |
| >= 28 | 肥胖 |

---

## 5. MCP SDK 用法（标准写法）

### 5.1 Python (fastmcp SDK)

```python
from fastmcp import FastMCP

# 创建 MCP Server
mcp = FastMCP("bmi-server")

# 定义工具
@mcp.tool()
def calculate_bmi(height_cm: float, weight_kg: float) -> dict:
    """计算 BMI 值并返回健康建议

    Args:
        height_cm: 身高（厘米）
        weight_kg: 体重（公斤）
    """
    bmi = weight_kg / (height_cm / 100) ** 2
    # ... 分类逻辑
    return {"bmi": round(bmi, 2), "category": category, ...}

# 运行（支持 stdio 和 SSE）
if __name__ == "__main__":
    mcp.run()  # 默认 stdio
    # mcp.run(transport="sse")  # SSE 模式
```

### 5.2 Node.js (@modelcontextprotocol/sdk)

```javascript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const server = new McpServer({ name: "bmi-server", version: "1.0.0" });

server.tool(
  "calculate_bmi",
  "计算 BMI 值并返回健康建议",
  {
    height_cm: z.number(),
    weight_kg: z.number()
  },
  async ({ height_cm, weight_kg }) => {
    const bmi = weight_kg / Math.pow(height_cm / 100, 2);
    // ... 分类逻辑
    return { content: [{ type: "text", text: JSON.stringify(result) }] };
  }
);

const transport = new StdioServerTransport();
await server.run(transport);
```

---

## 6. MCP Client 调用（同服务内）

### 6.1 Python Client 调用

```python
from mcp import Client

async def call_mcp_tool():
    # 创建 Client，连接本服务的 SSE 端点
    async with Client("http://localhost:8100/sse") as client:
        # 发现可用工具
        tools = await client.list_tools()
        print(f"可用工具: {[t.name for t in tools]}")

        # 调用工具
        result = await client.call_tool(
            "calculate_bmi",
            {"height_cm": 170, "weight_kg": 65}
        )
        print(f"BMI 结果: {result}")
```

### 6.2 Node.js Client 调用

```javascript
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { HttpClientTransport } from "@modelcontextprotocol/sdk/client/streamable-http.js";

async function callBmiTool() {
  const transport = new HttpClientTransport("http://localhost:8100/sse");
  const client = new Client({ name: "bmi-client", version: "1.0.0" }, { capabilities: {} });

  await client.connect(transport);

  // 发现工具
  const tools = await client.listTools();
  console.log("可用工具:", tools.map(t => t.name));

  // 调用工具
  const result = await client.callTool({
    name: "calculate_bmi",
    arguments: { height_cm: 170, weight_kg: 65 }
  });
  console.log("BMI 结果:", result);
}
```

---

## 7. 传输层：stdio vs SSE

| 传输方式 | 原理 | 适用场景 | 本 Demo |
|----------|------|----------|---------|
| **stdio** | 本地进程 stdin/stdout | Claude Desktop 插件 | ❌ |
| **SSE** | HTTP + Server-Sent Events | Web 服务、远程调用 | ✅ |

**为什么用 SSE：**
1. 可以在浏览器页面演示
2. 可以被同服务内的 Client 调用
3. 更适合教学，能看到 HTTP 请求

---

## 8. 验收标准

1. **Python Server** 启动后，`curl http://localhost:8100/health` 返回正常
2. **Node.js Server** 启动后，`curl http://localhost:8101/health` 返回正常
3. **demo.html** 可以打开，点击按钮调用工具并显示结果
4. **client_demo.py/js** 可以演示同服务内调用
5. **README.md** 包含：
   - MCP 核心概念解释
   - Python/Node.js 标准写法
   - Client-Server 调用流程
   - 面试 Q&A

---

## 9. 文件清单

```
demos/mcp-demo/
├── demo.html                      # 统一演示页面
├── start-python.sh               # Python 启动脚本
├── start-node.sh                 # Node.js 启动脚本
├── server/
│   ├── python/
│   │   ├── main.py              # MCP Server (fastmcp)
│   │   ├── client_demo.py       # MCP Client 演示
│   │   ├── requirements.txt
│   │   ├── start.sh
│   │   └── static/index.html
│   └── node/
│       ├── server.js            # MCP Server
│       ├── client_demo.js       # MCP Client 演示
│       ├── package.json
│       ├── start.sh
│       └── static/index.html
└── docs/
    └── README.md
```
