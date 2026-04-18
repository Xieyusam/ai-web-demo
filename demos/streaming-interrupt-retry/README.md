# Streaming Interrupt & Retry Demo

流式接口中断与重试教学 Demo，同时覆盖 Node.js 和 Python 语言，SSE 和 WebSocket 两种协议。

## 快速开始

### 启动 Node.js 服务

```bash
cd demos/streaming-interrupt-retry/server/node
npm install
npm start
# 服务运行在 http://localhost:8089
```

### 启动 Python 服务

```bash
cd demos/streaming-interrupt-retry/server/python
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
python server.py
# 服务运行在 http://localhost:8088
```

### 打开 Demo 页面

启动任一后端服务后，直接访问服务地址即可打开 Demo 页面：

```bash
# 启动 Node.js 后端 → 访问 http://localhost:8089
cd demos/streaming-interrupt-retry/server/node && npm start

# 或启动 Python 后端 → 访问 http://localhost:8088
cd demos/streaming-interrupt-retry/server/python && .venv\Scripts\activate && python server.py
```

页面右上角可切换 Node.js / Python 语言。

## 步骤说明

| Step | 内容 | 说明 |
|------|------|------|
| Step 1 | SSE 基础流 | 了解什么是 Server-Sent Events |
| Step 2 | SSE 中断与重试 | 学会用 EventSource 中断 + 续传 |
| Step 3 | WebSocket 基础流 | 了解双向通信，与 SSE 对比 |
| Step 4 | WebSocket 中断与重试 | 学会重连 + 状态恢复 |
| Step 5 | AI 流式模拟 | 企业级 LLM 流式响应，fetch+ReadableStream / WS 双协议，支持断点续传 |

## 技术栈

- 前端: Vue3 (CDN), Tailwind CSS (CDN)
- Node.js: Express, ws, cors
- Python: FastAPI, uvicorn, asyncio

## Step 5 — AI 流式模拟详解

本 Demo 的 Step 5 模拟企业级 AI Agent 流式场景，完整覆盖两种传输协议：

### 传输协议

| 协议 | 中断方式 | 续传方式 |
|------|---------|---------|
| **SSE (fetch)** | `AbortController.abort()` | fetch 手动带 `Last-Event-ID` header |
| **WebSocket** | `ws.close()` | URL 带 `lastChunkId=N` 参数 |

### 工作流程

1. **创建 session**：POST `/api/ai/sse/start` 或 `/api/ai/ws/start`，服务端创建 `aiSessions[sessionId]`（模拟 Redis）
2. **流式推送**：SSE 用 `fetch + ReadableStream`，WS 用原生 WebSocket，逐 token 推送
3. **中断**：客户端中断，服务端 `req.on('close')` 记录 `lastSentIndex`
4. **续传**：带断点参数重连，服务端从 `lastSentIndex + 1` 继续推送（**不重新调用 LLM**）
5. **回填**：WS 续传时，服务端先回填已缓冲 token（`buffered: true`），避免重复显示

### 核心配置

- **AI Token 总数**：90 个（`AI_CHUNKS` 数组）
- **SSE 推送间隔**：60-200ms 随机（模拟真实 LLM token 生成速度）
- **WS 推送间隔**：60-200ms 随机
- **Session 存储**：Node.js `Map` / Python `dict`（生产环境替换为 Redis）

详细原理见 [docs/tutorial.md](docs/tutorial.md)。

## 端口说明

- Node.js 服务: `http://localhost:8089`
- Python 服务: `http://localhost:8088`

demo.html 默认连接 Node.js 服务，切换语言后改为 Python 服务。
