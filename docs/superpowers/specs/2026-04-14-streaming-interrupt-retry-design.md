# Streaming Interrupt & Retry Demo — Design Specification

> **MVP:** MVP1 — 流式接口中断与重试教学 Demo

---

## 1. Concept & Vision

一个面向教学的多语言流式接口 Demo，同时覆盖 Node.js (Express + ws) 和 Python (FastAPI)，按 SSE 基础 → SSE 中断/重试 → WebSocket 基础 → WebSocket 中断/重试 四步骤递进。用户通过可交互的页面实时观察流式行为，零门槛理解中断和重试的原理与实现。

定位：让初学者理解流式接口基础，让进阶用户掌握中断/重试机制。

---

## 2. Project Structure

```
ai-web-demo/                          # 根目录（干净，仅文档）
├── README.md                          # 所有 demo 索引
│
└── demos/
    └── streaming-interrupt-retry/    # 本 demo（完全独立）
        ├── demo.html                 # 主页面（Vue3 CDN + Tailwind CDN，无构建）
        │
        ├── server/
        │   ├── node/
        │   │   ├── package.json
        │   │   ├── node_modules/
        │   │   └── server.js          # Express + ws 服务器
        │   │
        │   └── python/
        │       ├── .venv/            # Python 虚拟环境
        │       ├── requirements.txt
        │       └── server.py          # FastAPI 服务器
        │
        └── docs/
            └── tutorial.md           # 进阶教程文档
```

**依赖隔离规则：**
- 本 demo 的 Node 依赖安装在自己的 `node_modules/` 下
- 本 demo 的 Python 依赖装在自己的 `.venv/` 下
- demo.html 所需 Vue3 + Tailwind 均为 CDN 引入，无本地 npm 依赖
- 根目录不放任何代码依赖

---

## 3. Technical Stack

### Node (server)

| | |
|---|---|
| 框架 | Express |
| SSE | 手写 `StreamingResponse`（原生 `res.write()`） |
| WebSocket | `ws` 包 |
| 依赖 | `express`, `ws`, `cors` |
| 安装 | `npm install`（在 `server/node/` 下） |

### Python (server)

| | |
|---|---|
| 框架 | FastAPI |
| SSE | `StreamingResponse` |
| WebSocket | FastAPI 原生 `WebSocket` |
| 依赖 | `fastapi`, `uvicorn` |
| 安装 | `pip install -r requirements.txt`（在 `.venv/` 下） |

---

## 4. Page Structure

单 HTML 文件，四步骤引导。

```
┌─────────────────────────────────────────────────────┐
│  [Step 1] [Step 2] [Step 3] [Step 4]   [Node|Python]│  ← 顶部 Tab
├─────────────────────────────────────────────────────┤
│                                                     │
│  步骤说明区                                          │
│  - 原理讲解（3-5 句）                               │
│  - 关键代码片段（带注释）                            │
│  - 演示要点                                         │
│                                                     │
├─────────────────────────────────────────────────────┤
│  [▶ 开始流]  [⏹ 中断]  [↺ 重试]   [状态: idle]     │  ← 控制面板
├─────────────────────────────────────────────────────┤
│  输出日志区（实时滚动）                              │
│  - 时间戳 + 来源 + 内容                              │
│  - 中断时标红提示                                    │
│  - 重试时显示次数和间隔                              │
└─────────────────────────────────────────────────────┘
```

**步骤划分：**

| Step | 内容 | 功能 |
|------|------|------|
| Step 1 | SSE 基础流 | 开始 → 实时输出 → 自然结束 |
| Step 2 | SSE 中断与重试 | 开始 → 中断 → 可重试（续传/重头） |
| Step 3 | WebSocket 基础流 | 开始 → 双向日志（上发/下收）→ 自然结束 |
| Step 4 | WebSocket 中断与重试 | 开始 → 中断 → 可重试（续传/重头） |

**语言切换：** 顶部右侧 [Node | Python] 切换，影响服务器地址和代码示例显示。

---

## 5. Explanation Content Per Step

每个步骤说明区包含三部分：

1. **原理讲解** — 3-5 句核心概念
2. **关键代码** — 2-3 个核心片段（当前语言），带注释
3. **演示要点** — 用户应观察什么

### Step 1 — SSE 基础流

**原理：** SSE 是服务器向浏览器单向推送的技术。浏览器通过 `EventSource` API 连接，服务器持续 write 数据。连接断开后浏览器自动重连。

**关键代码（Node）：**
```js
const stream = new PassThrough();
res.setHeader('Content-Type', 'text/event-stream');
stream.on('data', chunk => res.write(`data: ${chunk}\n\n`));
```

**关键代码（Python）：**
```python
async def sse_stream():
    async def generate():
        for i in range(10):
            yield f"data: {i}\n\n"
    return StreamingResponse(generate(), media_type="text/event-stream")
```

**演示要点：** 点击"开始流"，观察右侧日志实时滚动；注意 Content-Type 是 `text/event-stream`；关闭网络卡，观察自动重连行为。

---

### Step 2 — SSE 中断与重试

**原理：** 中断是浏览器主动关闭 EventSource 连接；重试时可通过 `Last-Event-ID` 头告诉服务器从断点续传，或从头开始。服务器需要记录上次推送位置。

**关键代码（Node）：**
```js
// 读取 Last-Event-ID，实现续传
const lastId = req.headers['last-event-id'];
const startIndex = lastId ? parseInt(lastId) : 0;
```

**关键代码（Python）：**
```python
# FastAPI 读取 Last-Event-ID
last_id = request.headers.get("Last-Event-ID")
start_index = int(last_id) if last_id else 0
```

**演示要点：** 点击"中断"后，观察日志中断位置；点击"重试（续传）"观察从断点继续；点击"重试（重头）"观察从头开始。

---

### Step 3 — WebSocket 基础流

**原理：** WebSocket 是双向通信通道，建立连接后服务器和浏览器都可以随时发送消息。相比 SSE，协议本身支持双向通信。

**关键代码（Node）：**
```js
const wss = new WebSocketServer({ server });
wss.on('connection', ws => {
  ws.on('message', msg => {
    // 收到客户端消息，原样广播
    ws.send(`echo: ${msg}`);
  });
});
```

**关键代码（Python）：**
```python
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"echo: {data}")
```

**演示要点：** 点击"开始流"，在输入框输入文字，观察服务端回显；观察日志同时显示"发送"和"接收"两条记录。

---

### Step 4 — WebSocket 中断与重试

**原理：** WebSocket 中断后需要重新建立连接。可以通过 session/token 机制在重连后恢复上下文，或选择丢弃历史状态从头开始。

**关键代码（Node）：**
```js
// 服务器记录 session 状态
const sessions = new Map();
wss.on('connection', (ws, req) => {
  const sessionId = req.url.split('?session=')[1];
  ws.on('close', () => console.log('client disconnected'));
});
```

**演示要点：** 建立连接后多次交互，模拟断开；点击"重连"，观察是否恢复了之前的上下文。

---

## 6. API Endpoints

### SSE

| Method | Path | Description |
|--------|------|-------------|
| GET | `/sse/stream` | SSE 流，含 `Last-Event-ID` 续传支持 |

### WebSocket

| Path | Description |
|------|-------------|
| `/ws` | WebSocket 连接，支持 ping/pong 心跳 |

### Request Format (WS)

```json
{ "type": "message", "data": "hello" }
{ "type": "ping" }
```

### Response Format (WS)

```json
{ "type": "message", "data": "echo: hello" }
{ "type": "pong" }
```

---

## 7. Ports

- Node server: `http://localhost:3000`
- Python server: `http://localhost:8000`

demo.html 默认连接 `localhost:3000`（Node），切换语言后改为 `localhost:8000`（Python）。

---

## 8. Design Principles

- **零构建** — demo.html 纯 CDN，无 webpack/vite
- **依赖隔离** — 每个 demo 的依赖在自己目录下，不污染根目录
- **渐进展示** — 每个 Step 只展示与当前概念相关的代码，不堆砌
- **双语对称** — Node 和 Python 实现行为一致，方便对比
- **教学优先** — 交互是为了辅助理解原理，不是炫技
