# Streaming Interrupt & Retry — 进阶教程

## SSE vs WebSocket 选型指南

| 场景 | 推荐 | 原因 |
|------|------|------|
| 服务器单向推送（日志、进度、通知） | SSE | 实现简单，无需额外协议支持 |
| 需要双向通信（聊天、协作、游戏） | WebSocket | 全双工，性能更好 |
| 需要穿透企业防火墙 | SSE | 基于 HTTP，防火墙友好 |
| 需要在已有 HTTP 服务上扩展 | SSE | 复用 HTTP 端口 |
| 需要高频率双向消息 | WebSocket | 无 HTTP 头部开销 |

## 生产环境注意事项

### 中断处理

- 客户端断开时服务器必须清理资源（定时器、文件句柄等）
- 使用 `req.on('close')`（Node）或检测 `websocket.client_state`（Python）判断断开
- 设置合理的超时机制，防止僵尸连接

### 重试策略

- **指数退避**：重试间隔按 1s、2s、4s、8s 增长，避免频繁重试
- **最大重试次数**：防止无限重试消耗资源
- **幂等性**：SSE 续传时服务器必须保证从断点返回的数据与首次一致
- **Last-Event-ID 持久化**：在 Redis 或数据库中存储，支持服务重启后续传

### SSE 特定

```js
// 浏览器端 EventSource 自动重连，但不会带 Last-Event-ID
// 需要手动维护
const es = new EventSource(url);
es.onopen = () => { lastEventId = null; };
es.onmessage = (e) => {
  lastEventId = e.lastEventId;
  // 处理消息...
};
```

### WebSocket 特定

- 使用心跳（ping/pong）检测连接存活
- 建议在应用层实现 session 机制，支持重连后状态恢复
- 使用 wss（WebSocket Secure）加密传输

## 高级用法

### 1. 带权限验证的 SSE

```js
app.get('/sse/stream', (req, res) => {
  const token = req.headers.authorization;
  if (!verifyToken(token)) {
    res.status(401).end();
    return;
  }
  // ...正常逻辑
});
```

### 2. 多用户隔离的 WebSocket

```js
const clients = new Map(); // sessionId -> ws

wss.on('connection', (ws, req) => {
  const sessionId = req.url.split('?session=')[1];
  clients.set(sessionId, ws);

  ws.on('close', () => clients.delete(sessionId));
});
```

### 3. SSE 广播（服务器推送多人）

```js
const clients = new Set();

app.get('/sse/broadcast', (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  clients.add(res);
  req.on('close', () => clients.delete(res));
});

// 广播消息给所有客户端
function broadcast(data) {
  clients.forEach(client => {
    client.write(`data: ${JSON.stringify(data)}\n\n`);
  });
}
```

## 扩展阅读

- [MDN: Using SSE](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- [MDN: WebSocket](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [Stream Handbook](https://github.com/substack/stream-handbook)
