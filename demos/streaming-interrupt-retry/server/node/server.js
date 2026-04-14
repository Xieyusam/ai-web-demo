import express from 'express';
import cors from 'cors';
import { WebSocketServer } from 'ws';
import { createServer } from 'http';

const app = express();
const PORT = 8089;

app.use(cors());
app.use(express.json());

app.get('/', (req, res) => {
  res.json({ status: 'ok', server: 'node' });
});

// =====================
// SSE 端点（Step 1 & 2）
// =====================
app.get('/sse/stream', (req, res) => {
  const lastEventId = req.headers['last-event-id'] || '0';
  const startIndex = parseInt(lastEventId) || 0;

  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders();

  let count = startIndex;
  const total = 20;

  const interval = setInterval(() => {
    if (count >= total) {
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
