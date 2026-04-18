# Streaming Interrupt & Retry — 进阶教程

> 本文档是 [demo.html](../demo.html) 的配套教程，详细讲解企业级 AI Agent 流式场景下的断点续传实现原理，覆盖 SSE（fetch + ReadableStream）和 WebSocket 两种方案。

---

## 1. 概念总览

流式接口（Streaming API）允许服务器分批次将数据发送给客户端，无需等待所有数据准备完毕。AI Agent 场景下，每个 token 生成后立即推送，实现"打字机"效果。

**两种主流实现：**

| | SSE (Server-Sent Events) | WebSocket |
|---|---|---|
| 协议 | HTTP/1.1 | 独立 TCP 连接 |
| 方向 | 服务器 → 客户端（单向） | 双向 |
| 续传机制 | `Last-Event-ID` header | URL 参数（应用层） |
| 浏览器原生 | `EventSource` API | `WebSocket` API |
| 推荐替代 | `fetch()` + `ReadableStream` | — |

---

## 2. SSE 方案详解

### 2.1 EventSource 的两个关键局限

**A. 中断靠 `close()`，无法精确控制**

```js
const es = new EventSource(url);
es.close(); // 只能这样中断，没有 abort 能力
```

**B. `Last-Event-ID` 只在网络错误重连时自动发送**

EventSource 的自动重连行为：
- 网络断开 → 浏览器自动用 `Last-Event-ID` 头重连 ✓
- 手动调用 `close()` 或 `abort()` → **不会重连，不带 `Last-Event-ID`** ✗

> 这意味着：如果用户主动点击"中断"按钮，EventSource 无法续传，必须借助 URL 参数传递断点。

### 2.2 fetch + ReadableStream 解决方案

用 `fetch()` + `ReadableStream` 替代 `EventSource`，获得完全的控制能力：

```js
const abortController = new AbortController();

const res = await fetch(url, { signal: abortController.signal });
const reader = res.body.getReader();
const decoder = new TextDecoder();
let buffer = '';

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  buffer += decoder.decode(value, { stream: true });

  // 手动解析 SSE 格式：
  // event: chunk
  // data: 我
  // id: 0
  const lines = buffer.split('\n');
  buffer = lines.pop(); // 保留不完整行
  for (const line of lines) {
    if (line.startsWith('event:')) currentEvent = line.slice(7).trim();
    else if (line.startsWith('data:')) handleData(line.slice(5).trim(), currentEvent);
    else if (line.startsWith('id:')) lastEventId = line.slice(3).trim();
  }
}
```

**为什么更优：**

| 能力 | EventSource | fetch + ReadableStream |
|---|---|---|
| 中断 | `close()`（无法捕获中断状态） | `abortController.abort()`（抛出 `AbortError`） |
| 手动带 Last-Event-ID | ✗ | ✓（在 headers 里指定） |
| 读取响应状态码 | ✗ | ✓（可判断 4xx/5xx） |
| 自定义超时 | ✗ | ✓（配合 `setTimeout` + abort） |
| 读取响应头 | ✗ | ✓ |

### 2.3 中断实现（AbortController）

```js
// 启动时
this.aiAbortController = new AbortController();

// 中断时
interruptAI() {
  if (this.aiAbortController) {
    this.aiAbortController.abort();
  }
}
```

`abort()` 会：
1. 中断 `fetch` 的 `ReadableStream`，`reader.read()` 抛出 `AbortError`
2. 服务器端 `req.on('close')` 依然会触发，可记录 `lastSentIndex`
3. `catch (err)` 中通过 `err.name === 'AbortError'` 区分正常中断和其他错误

### 2.4 续传实现（手动 Last-Event-ID）

```js
// 续传时，fetch 手动带上 Last-Event-ID header
const lastId = this.aiLastEventId; // 记住最后收到的 token index
const res = await fetch(url, {
  signal: this.aiAbortController.signal,
  headers: { 'Last-Event-ID': lastId }
});
```

服务器读取方式（Node.js）：
```js
// 优先读 URL query（前端主动传），次选 header（EventSource 自动重连）
const lastEventId = req.query.lastEventId || req.headers['last-event-id'];
```

服务器读取方式（Python）：
```python
last_event_id = request.query_params.get("lastEventId") or request.headers.get("Last-Event-ID", "")
```

---

## 3. WebSocket 方案详解

### 3.1 为什么 WebSocket 需要应用层续传

WebSocket 是独立 TCP 连接，协议层没有类似 SSE `Last-Event-ID` 的机制。断开后重连，服务器没有任何上下文。

**解决方案：URL 参数传递断点信息**

```
ws://localhost:8089/ws/chat?sessionId=xxx&lastChunkId=50
```

- `sessionId`：标识会话（生产环境存 Redis）
- `lastChunkId`：告诉服务器从哪个 token 继续

### 3.2 服务器端 session 池

Node.js（内存 Map，生产环境用 Redis）：
```js
const aiSessions = new Map();

aiSessions.set(sessionId, {
  prompt: '用户输入的 prompt',
  model: 'gpt-4',
  chunks: [],        // 已生成的 token 缓存（模拟 Redis String/JSON）
  lastSentIndex: -1,  // 最后发送的 token 索引
  _currentTimer: null // 定时器引用，用于清理
});
```

Python（字典，生产环境用 Redis）：
```python
ai_sessions = {}
ai_sessions[session_id] = {
    "chunks": [],
    "last_sent_index": -1,
}
```

### 3.3 续传时回填已缓冲的 token

服务器在续传时，**先回填客户端已收到的内容**，避免重复显示：

```js
// Node: 续传时先发送已缓冲的 token
for (let i = startIndex; i <= session.lastSentIndex; i++) {
  if (session.chunks[i]) {
    ws.send(JSON.stringify({
      type: 'chunk',
      id: i,
      text: session.chunks[i],
      sessionId,
      buffered: true  // 标记为"已缓冲"，前端可选择跳过动画
    }));
  }
}
```

```python
# Python: 同理
for i in range(start_index, session["last_sent_index"] + 1):
    if session["chunks"][i]:
        await websocket.send_json({
            "type": "chunk", "id": i, "text": session["chunks"][i],
            "sessionId": session_id, "buffered": True
        })
```

---

## 4. 企业级 AI Agent 断点续传完整架构

### 4.1 完整流程时序图

```
客户端                              服务端                              存储（Redis）
  │                                  │                                    │
  │  POST /api/ai/sse/start          │                                    │
  │  { prompt, model }              │                                    │
  │ ─────────────────────────────────────────────────────────────────────>│
  │                                  │  HMSET sessionId {                  │
  │                                  │    prompt, model, chunks[],         │
  │                                  │    lastSentIndex: -1               │
  │                                  │  }                                 │
  │  { sessionId }                  │                                    │
  │ <─────────────────────────────────────────────────────────────────────│
  │                                  │                                    │
  │  GET /api/ai/sse/stream          │                                    │
  │  ?sessionId=xxx                │                                    │
  │ ─────────────────────────────────────────────────────────────────────>│
  │                                  │  LRANGE sessionId 0 lastSentIndex  │
  │  ← id:0 event:chunk data:我    │  ← 从 0 开始逐 token 推送            │
  │  ← id:1 event:chunk data:来    │                                    │
  │  ...                            │                                    │
  │  (中断)                         │  HSET lastSentIndex=25             │
  │  ✗                              │  req.on('close')                   │
  │                                  │                                    │
  │  GET /api/ai/sse/stream          │                                    │
  │  ?sessionId=xxx                │                                    │
  │  Last-Event-ID: 25            │                                    │
  │ ─────────────────────────────────────────────────────────────────────>│
  │                                  │  LRANGE sessionId 26 -1           │
  │                                  │  ← 从 chunks[26] 继续（不重调用 LLM）│
  │  ← id:26 event:chunk data:... │                                    │
```

### 4.2 为什么需要服务器端缓存（模拟 Redis）

如果服务器不缓存，每次续传都要重新调用 LLM API：

| 方案 | 续传时行为 | Token 消耗 | 延迟 |
|---|---|---|---|
| ❌ 不缓存 | 重新调用 LLM API | 双倍 | 高（重新生成所有 token） |
| ✓ 缓存（模拟 Redis） | 直接从缓存取剩余 token | 不变 | 低（只取缓存） |

生产环境 Redis 实现示例：

```js
// 创建 session
await redisClient.hSet(sessionId, {
  prompt: userPrompt,
  model: modelName,
  chunks: '[]',          // 或使用 Redis Stream 有序记录
  lastSentIndex: -1,
  createdAt: Date.now().toString()
});
await redisClient.expire(sessionId, 86400); // 24小时过期

// 续传时读取
const session = await redisClient.hGetAll(sessionId);
const chunks = JSON.parse(session.chunks || '[]');
// 从 lastSentIndex + 1 继续推送，不重新调用 LLM

// 更新进度
await redisClient.hSet(sessionId, {
  lastSentIndex: currentIndex,
  chunks: JSON.stringify(chunks)
});
```

### 4.3 SSE vs WebSocket 选型

**选 SSE 的场景：**
- 只需要服务器 → 客户端单向流（AI 打字效果）
- 需要浏览器自动重连（网络不稳定环境）
- 客户端是纯 Web（EventSource 全浏览器支持）
- 想利用 EventSource 的自动 `Last-Event-ID` 重连（但需要处理手动中断场景）

**选 WebSocket 的场景：**
- 需要双向通信（客户端实时发送指令、切换模型）
- 需要同时维持多个流（多任务并行）
- 非浏览器客户端（移动 App、CLI 工具）
- 需要自定义续传逻辑（URL 参数更灵活）

**企业级建议：**
- 纯 AI 流式输出 → SSE 更简单，配合 fetch + ReadableStream 可精确控制
- 需要交互控制（中断、发送上下文、切换模型） → WebSocket 更灵活

---

## 5. 演示页面字段详解

### 5.1 AI 对话区（Step 5）

| 字段 | 含义 |
|---|---|
| `sessionId` | 会话唯一标识（服务端 aiSessions Map 的 key） |
| `buffered tokens` | 服务器已生成的 token 数量（chunks 数组长度） |
| `lastSentIndex` | 最后发送的 token 索引（用于续传定位） |
| Token Buffer 可视化 | 蓝色=已发送，黄色=正在发送，灰色=待发送 |

### 5.2 续传 vs 重头对比

| 操作 | 行为 | 生产环境建议 |
|---|---|---|
| ↺ 续传 | 带 `lastEventId` / `lastChunkId` 重连，从断点继续 | ✅ 推荐，零浪费 |
| ↺ 重头 | 不带任何参数，新建 session，重新调用 LLM | ⚠️ 浪费 token 和延迟，应急才用 |

---

## 6. 关键代码对照

### 6.1 Node.js 服务器（server/node/server.js）

**SSE AI 端点 — 支持 query.lastEventId 和 header Last-Event-ID：**

```js
app.get('/api/ai/sse/stream', (req, res) => {
  const sessionId = req.query.sessionId || '';
  const session = aiSessions.get(sessionId);
  if (!session) { res.status(404).json({ error: 'Session not found' }); return; }

  // 优先读 URL query（前端主动传），次选 header（EventSource 自动重连）
  const lastEventId = req.query.lastEventId || req.headers['last-event-id'] || '';
  let startIndex = 0;
  if (lastEventId !== '') {
    const parsed = parseInt(lastEventId);
    if (!isNaN(parsed)) startIndex = parsed + 1;
  }

  res.setHeader('Content-Type', 'text/event-stream');
  res.flushHeaders();

  // 续传时发系统消息
  if (startIndex > 0) {
    res.write(`event: system\ndata: [RESUME] 续传成功，已跳过前 ${startIndex} 个 token\n\n`);
  }

  // scheduleNext() 逐 token 推送
});
```

**WebSocket AI 端点 — 支持 URL lastChunkId 参数：**

```js
function handleAIChat(ws, url) {
  const sessionId = url.searchParams.get('sessionId');
  const lastChunkId = url.searchParams.get('lastChunkId');
  const session = aiSessions.get(sessionId);

  let startIndex = 0;
  if (lastChunkId !== null && lastChunkId !== '') {
    startIndex = parseInt(lastChunkId) + 1;
    ws.send(JSON.stringify({ type: 'resume', sessionId, resumeFrom: startIndex }));
  }

  // 回填已缓冲的 token
  for (let i = startIndex; i <= session.lastSentIndex; i++) {
    if (session.chunks[i]) {
      ws.send(JSON.stringify({ type: 'chunk', id: i, text: session.chunks[i], buffered: true }));
    }
  }

  // 继续推送剩余 token
}
```

### 6.2 Python 服务器（server/python/server.py）

**SSE AI 端点：**

```python
@app.get("/api/ai/sse/stream")
async def ai_sse_stream(request: Request):
    session_id = request.query_params.get("sessionId", "")
    session = ai_sessions.get(session_id)
    if not session:
        return JSONResponse({"error": "Session not found"}, status_code=404)

    last_event_id = request.query_params.get("lastEventId") or request.headers.get("Last-Event-ID", "")
    start_index = int(last_event_id) + 1 if last_event_id else 0

    return StreamingResponse(
        ai_sse_generate(session_id, start_index),
        media_type="text/event-stream"
    )
```

**WebSocket AI 端点：**

```python
@app.websocket("/ws/chat")
async def ai_websocket(websocket: WebSocket):
    await websocket.accept()
    session_id = url.query_params.get("sessionId")
    last_chunk_id = url.query_params.get("lastChunkId")
    session = ai_sessions.get(session_id)

    start_index = int(last_chunk_id) + 1 if last_chunk_id else 0

    # 回填已缓冲的 token
    for i in range(start_index, session["last_sent_index"] + 1):
        if session["chunks"][i]:
            await websocket.send_json({"type": "chunk", "id": i, "text": session["chunks"][i], "buffered": True})
```

### 6.3 前端 fetch + ReadableStream 实现

**SSE 启动（_startAISSE）：**

```js
async _startAISSE(sessionId) {
  this.aiAbortController = new AbortController();
  const url = `${this.baseUrl}/api/ai/sse/stream?sessionId=${sessionId}`;
  this.aiConnected = true;

  const res = await fetch(url, { signal: this.aiAbortController.signal });
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let currentEvent = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop();

    for (const line of lines) {
      if (line.startsWith('event:')) {
        currentEvent = line.slice(7).trim();
      } else if (line.startsWith('data:')) {
        const data = line.slice(5).trim();
        if (currentEvent === 'chunk') {
          this.aiReceivedText += data;
          this.aiLastEventId = /* 从 id: 行获取 */;
        } else if (currentEvent === 'done') {
          this.aiConnected = false;
          this.aiCanRetry = true;
        }
      } else if (line.startsWith('id:')) {
        this.aiLastEventId = line.slice(3).trim();
        this.aiBufferedCount = Number(this.aiLastEventId) + 1;
      }
    }
  }
}
```

**SSE 续传（retryAI SSE 分支）：**

```js
const lastId = this.aiLastEventId;
const res = await fetch(url, {
  signal: this.aiAbortController.signal,
  headers: { 'Last-Event-ID': lastId }  // 手动带上续传位置
});
```

**中断（interruptAI）：**

```js
if (this.aiProtocol === 'sse') {
  this.aiAbortController.abort();  // 抛出 AbortError
}
```

---

## 7. 常见问题

**Q: 为什么 SSE 续传要用 URL query 参数而不是 EventSource 自动重连？**

A: EventSource 的自动重连只在**网络错误**时触发。手动 `close()` 或 `abort()` 不算网络错误，浏览器不会重连。因此需要用 URL `?lastEventId=N` 手动传递，服务器优先读 query 参数。

**Q: fetch + ReadableStream 能否完全替代 EventSource？**

A: 可以，但 EventSource 更简单（自动解析、自动重连）。fetch + ReadableStream 的优势是精确控制中断和续传 header，适合需要手动管理连接的企业级场景。

**Q: WebSocket 断开后自动重连吗？**

A: 不自动。EventSource 有自动重连机制，WebSocket 没有。应用层需要自行实现重连逻辑（指数退避、心跳保活等）。

**Q: 生产环境用什么存储 session？**

A: Redis。主 key 为 `sessionId`，hash 存 `chunks[]`、`lastSentIndex`、`prompt`、`model`。设置 TTL 过期（通常 1-24 小时）。

**Q: token 缓存会不会内存爆炸？**

A: 取决于 LLM 输出长度。生产环境可以：
1. 设置最大缓存 token 数（如 4096），超限则拒绝续传要求重头
2. 使用 Redis Stream 代替数组，只记录 offset 而不存全部内容
3. 对话轮次多时，只缓存最后一轮或关键上下文

**Q: SSE 和 WebSocket 可以同时用于同一个 AI 对话吗？**

A: 技术上可以，但会增加复杂度。常见做法是**根据场景选一个**：
- 纯打字效果 → SSE
- 需要客户端实时交互（如发送指令、切换模型） → WebSocket
