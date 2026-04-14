import express from 'express';
import cors from 'cors';
import { WebSocketServer } from 'ws';
import { createServer } from 'http';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const app = express();
const PORT = 8089;

// Serve demo.html from the demo root
const demoRoot = join(__dirname, '../../');
app.use(cors());
app.use(express.json());
app.use(express.static(demoRoot));

app.get('/', (req, res) => {
  res.sendFile(join(demoRoot, 'demo.html'));
});

// =====================
// SSE 端点（Step 1 & 2）
// 流式传输文本内容，支持通过 Last-Event-ID 续传
// =====================
const SSE_CONTENT = [
  "【第一段】流式接口（Streaming API）是一种数据传输技术，允许服务器分批次将数据发送给客户端，而无需等待所有数据准备完毕。",
  "【第二段】与传统的请求-响应模式不同，流式接口在建立连接后，服务器可以持续不断地推送数据，直到所有内容传输完成。",
  "【第三段】SSE（Server-Sent Events）是实现流式接口的一种浏览器原生技术。它基于 HTTP 协议，服务器通过特定的 Content-Type（text/event-stream）向浏览器持续写入数据。",
  "【第四段】EventSource 是浏览器提供的 JavaScript API，用于接收 SSE 流。它会自动处理重连，并支持通过 Last-Event-ID 头部实现断点续传。",
  "【第五段】当网络中断或用户主动关闭连接时，SSE 流会终止。重新连接后，浏览器会自动带上 Last-Event-ID，服务器据此从断点继续发送剩余内容。",
  "【第六段】这就好比在听有声书时突然暂停，再次播放时会从暂停处继续，而不是从头开始朗读。这就是「续传」的核心原理。",
  "【第七段】WebSocket 是另一种双向通信协议，与 SSE 不同，它不基于 HTTP，而是建立了独立的 TCP 连接。WebSocket 一旦断开，没有自动续传机制，需要在应用层自行实现。",
  "【第八段】实际应用中，流式接口广泛用于：实时日志推送、AI 对话打字效果、股票行情更新、进度条通知等需要「服务器持续推送」的场景。",
];

app.get('/sse/stream', (req, res) => {
  // 优先从 query 参数读取（前端手动续传时通过 URL 传递）
  // 次选 Last-Event-ID 头（浏览器自动重连时携带）
  const lastEventId = req.query.lastEventId || req.headers['last-event-id'] || '';
  let startIndex = 0;
  if (lastEventId !== '') {
    const parsed = parseInt(lastEventId);
    if (!isNaN(parsed)) startIndex = parsed + 1;
  }

  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders();

  let idx = startIndex;

  const interval = setInterval(() => {
    if (idx >= SSE_CONTENT.length) {
      clearInterval(interval);
      res.write(`event: done\ndata: [DONE]\n\n`);
      res.end();
      return;
    }
    res.write(`id: ${idx}\nevent: message\ndata: ${SSE_CONTENT[idx]}\n\n`);
    idx++;
  }, 1200); // 每段1.2秒，足够看清每个段落的切换

  req.on('close', () => {
    clearInterval(interval);
    console.log(`SSE client disconnected at paragraph ${idx}`);
  });
});

// =====================
// WebSocket 端点（Step 3 & 4）
// =====================
const server = createServer(app);
const wss = new WebSocketServer({ server });

wss.on('connection', (ws, req) => {
  const clientIp = req.socket.remoteAddress;
  console.log(`WebSocket client connected from ${clientIp}`);

  ws.send(JSON.stringify({ type: 'connected', data: 'welcome' }));

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
});

server.listen(PORT, () => {
  console.log(`Node server running on http://localhost:${PORT}`);
  console.log(`SSE:  http://localhost:${PORT}/sse/stream`);
  console.log(`WebSocket: ws://localhost:${PORT}/ws`);
});
