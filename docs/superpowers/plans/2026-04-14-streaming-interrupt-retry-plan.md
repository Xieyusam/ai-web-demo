# Streaming Interrupt & Retry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现一个完整的流式接口教学 Demo，支持 SSE/WebSocket 基础流及中断/重试，Node/ Python 双语言，步骤引导页面。

**Architecture:** 单 HTML 页面（Vue3 CDN + Tailwind CDN）+ 两个独立后端服务（Node Express + Python FastAPI）。前端纯展示，后端各自实现 SSE 和 WebSocket 两种协议。

**Tech Stack:** Vue3 (CDN), Tailwind CSS (CDN), Express, ws, cors (Node) | FastAPI, uvicorn (Python)

---

## File Structure

```
demos/streaming-interrupt-retry/
├── demo.html                          # 主页面（Vue3 + Tailwind CDN）
├── server/
│   ├── node/
│   │   ├── package.json
│   │   └── server.js                  # Express + ws，含 SSE + WebSocket
│   └── python/
│       ├── .venv/                    # Python 虚拟环境
│       ├── requirements.txt
│       └── server.py                  # FastAPI，含 SSE + WebSocket
└── docs/
    └── tutorial.md                   # 进阶教程（Step 完成后补充）
```

---

## Task 1: 搭建 Node 后端基础结构

**Files:**
- Create: `demos/streaming-interrupt-retry/server/node/package.json`
- Create: `demos/streaming-interrupt-retry/server/node/server.js`

- [ ] **Step 1: 创建 package.json**

```json
{
  "name": "streaming-demo-server",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "start": "node server.js"
  },
  "dependencies": {
    "express": "^4.18.2",
    "ws": "^8.14.2",
    "cors": "^2.8.5"
  }
}
```

- [ ] **Step 2: 创建 server.js 骨架（Express 基础）**

```js
import express from 'express';
import cors from 'cors';
import { WebSocketServer } from 'ws';

const app = express();
const PORT = 3000;

app.use(cors());
app.use(express.json());

app.get('/', (req, res) => {
  res.json({ status: 'ok', server: 'node' });
});

const server = app.listen(PORT, () => {
  console.log(`Node server running on http://localhost:${PORT}`);
});
```

- [ ] **Step 3: 安装依赖**

Run: `cd demos/streaming-interrupt-retry/server/node && npm install`
Expected: node_modules 下有 express, ws, cors

- [ ] **Step 4: 验证服务启动**

Run: `node server.js`
Expected: 服务启动，访问 http://localhost:3000 返回 `{"status":"ok","server":"node"}`

- [ ] **Step 5: Commit**

```bash
git add demos/streaming-interrupt-retry/server/node/
git commit -m "feat(demo1-node): init express server with ws support"
```

---

## Task 2: 实现 Node SSE 端点（Step 1 & Step 2）

**Files:**
- Modify: `demos/streaming-interrupt-retry/server/node/server.js`

- [ ] **Step 1: 实现 SSE 基础流端点**

```js
// GET /sse/stream
app.get('/sse/stream', (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders();

  let count = 0;
  const interval = setInterval(() => {
    if (count >= 20) {
      clearInterval(interval);
      res.write(`event: done\ndata: stream complete\n\n`);
      res.end();
      return;
    }
    res.write(`id: ${count}\nevent: message\ndata: message ${count} at ${new Date().toISOString()}\n\n`);
    count++;
  }, 500);

  req.on('close', () => {
    clearInterval(interval);
    console.log(`SSE client disconnected at count ${count}`);
  });
});
```

- [ ] **Step 2: 测试 SSE 端点**

Run: `curl http://localhost:3000/sse/stream`
Expected: 20 条消息，每 500ms 一条，包含 id、event、data

- [ ] **Step 3: 实现带 Last-Event-ID 的 SSE 续传端点**

```js
// 修改 /sse/stream 端点，支持续传
app.get('/sse/stream', (req, res) => {
  const lastEventId = req.headers['last-event-id'] || '0';
  const startIndex = parseInt(lastEventId) || 0;

  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders();

  let count = startIndex;
  const interval = setInterval(() => {
    if (count >= 20) {
      clearInterval(interval);
      res.write(`event: done\ndata: stream complete\n\n`);
      res.end();
      return;
    }
    res.write(`id: ${count}\nevent: message\ndata: message ${count} (resumed from ${startIndex})\n\n`);
    count++;
  }, 500);

  req.on('close', () => {
    clearInterval(interval);
  });
});
```

- [ ] **Step 4: Commit**

```bash
git add demos/streaming-interrupt-retry/server/node/server.js
git commit -m "feat(demo1-node): add SSE stream endpoint with resume support"
```

---

## Task 3: 实现 Node WebSocket 端点（Step 3 & Step 4）

**Files:**
- Modify: `demos/streaming-interrupt-retry/server/node/server.js`

- [ ] **Step 1: 创建 WebSocket 服务器**

```js
const wss = new WebSocketServer({ server });

wss.on('connection', (ws, req) => {
  const clientIp = req.socket.remoteAddress;
  console.log(`WebSocket client connected from ${clientIp}`);

  ws.on('message', (msg) => {
    try {
      const data = JSON.parse(msg.toString());
      if (data.type === 'ping') {
        ws.send(JSON.stringify({ type: 'pong' }));
        return;
      }
      if (data.type === 'message') {
        ws.send(JSON.stringify({
          type: 'message',
          data: `echo: ${data.data}`,
          timestamp: new Date().toISOString()
        }));
      }
    } catch (e) {
      ws.send(JSON.stringify({ type: 'error', data: 'invalid json' }));
    }
  });

  ws.on('close', () => {
    console.log('WebSocket client disconnected');
  });

  ws.send(JSON.stringify({ type: 'connected', data: 'welcome' }));
});
```

- [ ] **Step 2: 测试 WebSocket 端点**

使用浏览器开发者工具或 `wscat` 连接 `ws://localhost:3000`，验证：
- 连接成功后收到 `{"type":"connected","data":"welcome"}`
- 发送 `{"type":"message","data":"hello"}` 收到 `{"type":"message","data":"echo: hello",...}`
- 发送 `{"type":"ping"}` 收到 `{"type":"pong"}`

- [ ] **Step 3: Commit**

```bash
git add demos/streaming-interrupt-retry/server/node/server.js
git commit -m "feat(demo1-node): add WebSocket echo endpoint"
```

---

## Task 4: 搭建 Python 后端基础结构

**Files:**
- Create: `demos/streaming-interrupt-retry/server/python/requirements.txt`
- Create: `demos/streaming-interrupt-retry/server/python/server.py`

- [ ] **Step 1: 创建 requirements.txt**

```
fastapi==0.109.0
uvicorn==0.27.0
```

- [ ] **Step 2: 创建 FastAPI 骨架**

```python
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/")
def root():
    return JSONResponse({"status": "ok", "server": "python"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

- [ ] **Step 3: 创建虚拟环境并安装依赖**

Run: `cd demos/streaming-interrupt-retry/server/python && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
Expected: `.venv/` 下有 fastapi, uvicorn

- [ ] **Step 4: 验证服务启动**

Run: `source .venv/bin/activate && python server.py`
Expected: 服务启动，访问 http://localhost:8000 返回 `{"status":"ok","server":"python"}`

- [ ] **Step 5: Commit**

```bash
git add demos/streaming-interrupt-retry/server/python/requirements.txt
git add demos/streaming-interrupt-retry/server/python/server.py
git commit -m "feat(demo1-python): init fastapi server"
```

---

## Task 5: 实现 Python SSE 端点

**Files:**
- Modify: `demos/streaming-interrupt-retry/server/python/server.py`

- [ ] **Step 1: 实现 SSE 基础流（含 Last-Event-ID 续传）**

```python
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import asyncio

app = FastAPI()

async def sse_generate(start_index: int = 0):
    for i in range(start_index, 20):
        await asyncio.sleep(0.5)
        yield f"id: {i}\nevent: message\ndata: message {i} at {datetime.now().isoformat()}\n\n"
    yield f"event: done\ndata: stream complete\n\n"

@app.get("/sse/stream")
async def sse_stream(request: Request):
    last_event_id = request.headers.get("Last-Event-ID", "0")
    try:
        start_index = int(last_event_id)
    except ValueError:
        start_index = 0

    return StreamingResponse(
        sse_generate(start_index),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
```

- [ ] **Step 2: 测试 SSE 端点**

Run: `curl http://localhost:8000/sse/stream`
Expected: 同 Node SSE 端点行为

- [ ] **Step 3: Commit**

```bash
git add demos/streaming-interrupt-retry/server/python/server.py
git commit -m "feat(demo1-python): add SSE stream endpoint with resume support"
```

---

## Task 6: 实现 Python WebSocket 端点

**Files:**
- Modify: `demos/streaming-interrupt-retry/server/python/server.py`

- [ ] **Step 1: 实现 WebSocket 端点**

```python
from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse
import json

app = FastAPI()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        await websocket.send_json({"type": "connected", "data": "welcome"})
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                elif msg.get("type") == "message":
                    await websocket.send_json({
                        "type": "message",
                        "data": f"echo: {msg.get('data')}",
                        "timestamp": datetime.now().isoformat()
                    })
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "data": "invalid json"})
    except Exception:
        pass
```

- [ ] **Step 2: 测试 WebSocket 端点**

验证行为同 Node WebSocket

- [ ] **Step 3: Commit**

```bash
git add demos/streaming-interrupt-retry/server/python/server.py
git commit -m "feat(demo1-python): add WebSocket echo endpoint"
```

---

## Task 7: 实现 demo.html 页面

**Files:**
- Create: `demos/streaming-interrupt-retry/demo.html`

- [ ] **Step 1: 创建 HTML 骨架（Vue3 + Tailwind CDN）**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Streaming Interrupt & Retry Demo</title>
  <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-900 text-gray-100 min-h-screen p-6">
  <div id="app"></div>
</body>
</html>
```

- [ ] **Step 2: 实现 Step Tab 和语言切换**

```html
<div id="app">
  <!-- Step Tabs -->
  <div class="flex gap-2 mb-6">
    <button
      v-for="(step, idx) in steps"
      :key="idx"
      @click="currentStep = idx"
      :class="currentStep === idx ? 'bg-blue-600' : 'bg-gray-700'"
      class="px-4 py-2 rounded font-mono text-sm"
    >{{ step.title }}</button>
  </div>

  <!-- Language Toggle -->
  <div class="flex gap-2 mb-6">
    <button @click="lang = 'node'" :class="lang === 'node' ? 'bg-green-600' : 'bg-gray-700'" class="px-4 py-2 rounded text-sm">Node</button>
    <button @click="lang = 'python'" :class="lang === 'python' ? 'bg-green-600' : 'bg-gray-700'" class="px-4 py-2 rounded text-sm">Python</button>
  </div>

  <!-- Explanation Area -->
  <div class="bg-gray-800 rounded-lg p-6 mb-6">
    <h2 class="text-xl font-bold mb-4">{{ steps[currentStep].title }}</h2>
    <p class="text-gray-300 mb-4">{{ steps[currentStep].principle }}</p>
    <!-- Code blocks and demo points -->
  </div>

  <!-- Control Panel -->
  <div class="flex gap-3 mb-6 items-center">
    <button @click="startStream" class="bg-blue-600 hover:bg-blue-700 px-6 py-2 rounded font-mono">▶ 开始流</button>
    <button @click="interruptStream" :disabled="!streamActive" class="bg-red-600 hover:bg-red-700 disabled:opacity-50 px-6 py-2 rounded font-mono">⏹ 中断</button>
    <button @click="retryStream(false)" :disabled="!canRetry" class="bg-yellow-600 hover:bg-yellow-700 disabled:opacity-50 px-6 py-2 rounded font-mono">↺ 重试（续传）</button>
    <button @click="retryStream(true)" :disabled="!canRetry" class="bg-orange-600 hover:bg-orange-700 disabled:opacity-50 px-6 py-2 rounded font-mono">↺ 重试（重头）</button>
    <span class="ml-4 text-gray-400 font-mono text-sm">状态: {{ status }}</span>
  </div>

  <!-- Log Output -->
  <div class="bg-gray-800 rounded-lg p-4 h-96 overflow-y-auto font-mono text-sm">
    <div v-for="(log, idx) in logs" :key="idx" :class="log.type === 'error' ? 'text-red-400' : 'text-gray-300'" class="mb-1">
      <span class="text-gray-500">[{{ log.time }}]</span> {{ log.msg }}
    </div>
  </div>
</div>
```

- [ ] **Step 3: 实现 SSE EventSource 逻辑（Step 1 & Step 2）**

```js
// Step 1 & 2: SSE stream
startSSE() {
  const url = `${this.baseUrl}/sse/stream`;
  this.eventSource = new EventSource(url);
  this.streamActive = true;
  this.status = 'streaming';
  this.logs.push({ time: this.now(), msg: `[SSE] Connecting to ${url}`, type: 'info' });

  this.eventSource.onmessage = (e) => {
    this.logs.push({ time: this.now(), msg: `[SSE] ${e.data}`, type: 'info' });
  };

  this.eventSource.addEventListener('done', (e) => {
    this.logs.push({ time: this.now(), msg: `[SSE] Stream complete`, type: 'info' });
    this.streamActive = false;
    this.canRetry = true;
    this.eventSource.close();
  });

  this.eventSource.onerror = () => {
    this.logs.push({ time: this.now(), msg: `[SSE] Error / Disconnected`, type: 'error' });
    this.streamActive = false;
    this.canRetry = true;
  };
},

interruptSSE() {
  if (this.eventSource) {
    this.eventSource.close();
    this.streamActive = false;
    this.logs.push({ time: this.now(), msg: `[SSE] Manually interrupted`, type: 'error' });
  }
},

retrySSE(fromStart) {
  if (fromStart) {
    this.logs.push({ time: this.now(), msg: `[SSE] Retrying from start`, type: 'info' });
    this.startSSE();
  } else {
    // Resume using Last-Event-ID — EventSource auto-handles this
    this.logs.push({ time: this.now(), msg: `[SSE] Retrying with resume`, type: 'info' });
    this.startSSE();
  }
},
```

- [ ] **Step 4: 实现 WebSocket 逻辑（Step 3 & Step 4）**

```js
// Step 3 & 4: WebSocket stream
startWS() {
  this.ws = new WebSocket(`${this.wsBaseUrl}/ws`);
  this.streamActive = true;
  this.status = 'streaming';

  this.ws.onopen = () => {
    this.logs.push({ time: this.now(), msg: `[WS] Connected`, type: 'info' });
  };

  this.ws.onmessage = (e) => {
    const data = JSON.parse(e.data);
    this.logs.push({ time: this.now(), msg: `[WS] Received: ${JSON.stringify(data)}`, type: 'info' });
  };

  this.ws.onerror = () => {
    this.logs.push({ time: this.now(), msg: `[WS] Error`, type: 'error' });
  };

  this.ws.onclose = () => {
    this.logs.push({ time: this.now(), msg: `[WS] Disconnected`, type: 'error' });
    this.streamActive = false;
    this.canRetry = true;
  };
},

sendWSMessage(data) {
  if (this.ws && this.ws.readyState === WebSocket.OPEN) {
    this.ws.send(JSON.stringify({ type: 'message', data }));
    this.logs.push({ time: this.now(), msg: `[WS] Sent: ${data}`, type: 'info' });
  }
},

interruptWS() {
  if (this.ws) {
    this.ws.close();
    this.streamActive = false;
  }
},

retryWS(fromStart) {
  this.logs.push({ time: this.now(), msg: `[WS] Reconnecting...`, type: 'info' });
  this.startWS();
},
```

- [ ] **Step 5: 在控制面板加入输入框（供 WS 发送消息）**

在 Step 3/4 时，显示输入框：

```html
<div v-if="currentStep >= 2" class="flex gap-3 mb-4">
  <input v-model="wsInput" @keyup.enter="sendWSMessage(wsInput)" placeholder="输入消息后回车发送" class="bg-gray-700 px-4 py-2 rounded flex-1 font-mono text-sm" />
  <button @click="sendWSMessage(wsInput)" class="bg-blue-600 px-4 py-2 rounded font-mono text-sm">发送</button>
</div>
```

- [ ] **Step 6: Commit**

```bash
git add demos/streaming-interrupt-retry/demo.html
git commit -m "feat(demo1): add interactive demo.html with Vue3 + Tailwind"
```

---

## Task 8: 编写根目录 README

**Files:**
- Create: `ai-web-demo/README.md`

- [ ] **Step 1: 创建 README.md**

```markdown
# AI Web Demo

一个 AI Web 开发常用代码 Demo 集合，每个子文件夹都是一个独立 Demo。

## Demo 列表

| Demo | 描述 | 状态 |
|------|------|------|
| [streaming-interrupt-retry](demos/streaming-interrupt-retry/) | 流式接口中断与重试（Node + Python， SSE + WebSocket） | 🚧 开发中 |

## 本地运行

各 Demo 的后端依赖安装在自己目录下，无需根目录安装。

详见各 Demo 的 README.md。
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add root README.md"
```

---

## Task 9: 编写 demo README

**Files:**
- Create: `demos/streaming-interrupt-retry/README.md`

- [ ] **Step 1: 创建 demo README**

```markdown
# Streaming Interrupt & Retry Demo

流式接口中断与重试教学 Demo。

## 快速开始

### 启动 Node 服务

```bash
cd demos/streaming-interrupt-retry/server/node
npm install
npm start
# 服务运行在 http://localhost:3000
```

### 启动 Python 服务

```bash
cd demos/streaming-interrupt-retry/server/python
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python server.py
# 服务运行在 http://localhost:8000
```

### 打开 Demo 页面

直接在浏览器打开 `demo.html`，选择语言后体验。

## 步骤说明

- **Step 1**: SSE 基础流（了解什么是 Server-Sent Events）
- **Step 2**: SSE 中断与重试（学会用 EventSource 手动中断 + 续传）
- **Step 3**: WebSocket 基础流（了解双向通信，与 SSE 对比）
- **Step 4**: WebSocket 中断与重试（学会重连 + 状态恢复）

## 技术栈

- 前端: Vue3 (CDN), Tailwind CSS (CDN)
- Node: Express, ws, cors
- Python: FastAPI, uvicorn
```

- [ ] **Step 2: Commit**

```bash
git add demos/streaming-interrupt-retry/README.md
git commit -m "docs(demo1): add streaming-demo README"
```

---

## Task 10: 编写 tutorial.md

**Files:**
- Create: `demos/streaming-interrupt-retry/docs/tutorial.md`

- [ ] **Step 1: 编写进阶教程文档**

内容覆盖：
- SSE vs WebSocket 选型指南
- 生产环境中断/重试注意事项（超时配置、幂等性、重试策略）
- EventSource 与 WebSocket 的高级用法

（此任务可在所有 Step 完成后补充）

- [ ] **Step 2: Commit**

```bash
git add demos/streaming-interrupt-retry/docs/tutorial.md
git commit -m "docs(demo1): add advanced tutorial"
```
