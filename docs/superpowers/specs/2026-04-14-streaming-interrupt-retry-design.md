# Streaming Interrupt & Retry Demo — Design Specification

> **MVP:** MVP1 — 流式接口中断与重试教学 Demo
> **Status:** ✅ 已完成

---

## 1. Concept & Vision

一个面向教学的多语言流式接口 Demo，同时覆盖 Node.js (Express + ws) 和 Python (FastAPI)，按 SSE 基础 → SSE 中断/重试 → WebSocket 基础 → WebSocket 中断/重试 → AI 流式模拟 五步骤递进。

前端使用 `fetch()` + `ReadableStream` 替代 EventSource，实现对中断和续传的精确控制。教学目标：让初学者理解流式接口基础，让进阶用户掌握企业级 AI Agent 断点续传的实现方式。

---

## 2. Project Structure

```
ai-web-demo/
├── README.md                          # 所有 demo 索引
│
└── demos/
    └── streaming-interrupt-retry/    # 本 demo（完全独立）
        ├── demo.html                 # 主页面（Vue3 CDN + Tailwind CDN，无构建）
        ├── start-node.bat            # 启动 Node 服务
        ├── start-python.bat          # 启动 Python 服务
        │
        ├── server/
        │   ├── node/
        │   │   ├── package.json
        │   │   ├── node_modules/
        │   │   └── server.js          # Express + ws 服务器（端口 8089）
        │   │
        │   └── python/
        │       ├── .venv/
        │       ├── requirements.txt
        │       └── server.py          # FastAPI 服务器（端口 8088）
        │
        └── docs/
            └── tutorial.md           # 进阶教程（企业级 AI 断点续传详解）
```

**端口分配：**
- Node.js server: `http://localhost:8089`
- Python server: `http://localhost:8088`

---

## 3. Technical Stack

### Node (server)

| | |
|---|---|
| 框架 | Express 4 |
| SSE | 原生 `res.write()`，`text/event-stream` |
| WebSocket | `ws` 包（`WebSocketServer`） |
| 依赖 | `express`, `ws`, `cors` |
| 端口 | 8089 |

### Python (server)

| | |
|---|---|
| 框架 | FastAPI |
| SSE | `StreamingResponse` |
| WebSocket | FastAPI 原生 `@app.websocket` |
| 端口 | 8088 |

### Frontend

| | |
|---|---|
| 框架 | Vue3（CDN，无构建）|
| CSS | Tailwind CSS（CDN）|
| SSE 方式 | `fetch()` + `ReadableStream`（替代 EventSource）|
| 中断方式 | `AbortController` |

---

## 4. Five-Step Page Structure

```
┌─────────────────────────────────────────────────────────┐
│  [Step 1] [Step 2] [Step 3] [Step 4] [Step 5]  [Node|Python]│
├─────────────────────────────────────────────────────────┤
│  步骤说明区                                               │
│  - 原理讲解（3-5 句）                                   │
│  - 关键代码片段（带注释，当前语言）                      │
│  - 演示要点                                             │
├─────────────────────────────────────────────────────────┤
│  文本阅读区 / WebSocket 推送区 / AI 对话区               │
├─────────────────────────────────────────────────────────┤
│  [▶ 开始流]  [⏹ 中断]  [↺ 续传]  [↺ 重头]   [状态]      │
├─────────────────────────────────────────────────────────┤
│  📋 原始日志（实时滚动）                                  │
└─────────────────────────────────────────────────────────┘
```

**步骤划分：**

| Step | 内容 | 技术方案 |
|------|------|---------|
| Step 1 | SSE 基础流（8 段文本，1.2s/段） | EventSource 原生 |
| Step 2 | SSE 中断与续传 | URL `?lastEventId=N` query 参数 |
| Step 3 | WebSocket 基础流（服务器主动推送） | `ws` 库 / FastAPI WebSocket |
| Step 4 | WebSocket 中断与续传 | URL `?sessionId=xxx&lastId=N` |
| Step 5 | AI 流式模拟（90 tokens，企业级方案） | **fetch + ReadableStream（ SSE）** 和 **WebSocket 双协议** |

---

## 5. Step 5 — AI 流式模拟详解

### 5.1 双协议架构

Step 5 同时展示 SSE 和 WebSocket 两种 AI 流式方案：

```
客户端                              服务端
  │                                  │
  │  POST /api/ai/sse/start  ──────► 创建 session，返回 sessionId
  │  POST /api/ai/ws/start   ──────► （同上）
  │                                  │
  │  GET /api/ai/sse/stream ◄──────  SSE 流，逐 token 推送
  │  WS /ws/chat?sessionId=  ◄──────  WebSocket 流，逐 token 推送
```

### 5.2 为什么用 fetch + ReadableStream 替代 EventSource

| 能力 | EventSource | fetch + ReadableStream |
|---|---|---|
| 中断 | `close()` 无法精确控制 | `AbortController.abort()` 抛出 `AbortError` |
| 手动带 Last-Event-ID | ✗ | ✓（headers 里手动指定） |
| 读取响应状态码 | ✗ | ✓ |
| 解析 SSE 格式 | 自动 | 手动（但更可控） |

### 5.3 中断原理

```
用户点击"中断"
    ↓
AbortController.abort()
    ↓
fetch 的 ReadableStream 中断 → reader.read() 抛出 AbortError
    ↓
服务器 req.on('close') 触发 → 记录 lastSentIndex 到 aiSessions
```

### 5.4 续传原理

**SSE 续传：**
```
用户点击"续传"
    ↓
fetch(url, { headers: { 'Last-Event-ID': lastEventId } })
    ↓
服务器从 lastEventId + 1 继续推送（不重调用 LLM）
```

**WebSocket 续传：**
```
用户点击"续传"
    ↓
new WebSocket('ws://...?sessionId=xxx&lastChunkId=N')
    ↓
服务器先回填已缓冲的 token，再继续推送
```

---

## 6. API Endpoints

### SSE（Step 1 & 2）

| Method | Path | Description |
|--------|------|-------------|
| GET | `/sse/stream` | SSE 流，支持 `?lastEventId=N` 续传 |
| GET | `/sse/stream` | 读 `Last-Event-ID` header 续传（EventSource 自动） |

### WebSocket Demo（Step 3 & 4）

| Path | Description |
|------|-------------|
| `/ws` | Demo WebSocket，服务器主动推送 8 段文本 |
| `/ws?sessionId=xxx&lastId=N` | 续传，从断点继续 |

### AI SSE（Step 5a）

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/ai/sse/start` | 创建 session，返回 `{ sessionId }` |
| GET | `/api/ai/sse/stream?sessionId=xxx` | SSE 流，续传时加 `?lastEventId=N` 或带 `Last-Event-ID` header |

### AI WebSocket（Step 5b）

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/ai/ws/start` | 创建 session，返回 `{ sessionId }` |
| WS | `/ws/chat?sessionId=xxx` | 新连接，从头推送 |
| WS | `/ws/chat?sessionId=xxx&lastChunkId=N` | 续传，先回填已缓冲，再继续 |

---

## 7. Server Session Storage

Node.js `aiSessions` Map 结构：
```js
aiSessions.set(sessionId, {
  prompt: String,
  model: String,
  chunks: String[],        // 已生成的 token 数组（模拟 Redis 缓存）
  lastSentIndex: Number,   // 最后发送的 token 索引
  _currentTimer: Object    // setTimeout 引用，用于清理
});
```

Python `ai_sessions` 字典结构同上。

生产环境替换为 Redis hash：
- Key: `ai:session:{sessionId}`
- Field `chunks`: JSON string
- Field `lastSentIndex`: integer
- TTL: 24 小时

---

## 8. Design Principles

- **零构建** — demo.html 纯 CDN，无 webpack/vite
- **依赖隔离** — 每个 demo 的依赖在自己目录下，不污染根目录
- **渐进展示** — 每个 Step 只展示与当前概念相关的代码
- **双语对称** — Node 和 Python 实现行为一致，方便对比
- **教学优先** — 交互是为了辅助理解原理，不是炫技
- **企业级真实** — Step 5 完整模拟 Redis 缓存、续传不重调用 LLM 的生产行为
