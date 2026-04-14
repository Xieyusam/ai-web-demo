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

const demoRoot = join(__dirname, '../../');
app.use(cors());
app.use(express.json());
app.use(express.static(demoRoot));

app.get('/', (req, res) => {
  res.sendFile(join(demoRoot, 'demo.html'));
});

// =====================
// SSE 端点（Step 1 & 2）
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
  }, 1200);

  req.on('close', () => {
    clearInterval(interval);
  });
});

// =====================
// HTTP Server + WebSocket
// =====================
const server = createServer(app);
const wss = new WebSocketServer({ server });

// =====================
// WebSocket 端点路由分发
// =====================
wss.on('connection', (ws, req) => {
  const url = new URL(req.url, `http://${req.headers.host}`);
  const pathname = url.pathname;

  if (pathname === '/ws/chat') {
    handleAIChat(ws, url);
  } else {
    handleDemoWS(ws, url);
  }
});

// =====================
// Demo WS 路由（Step 3 & 4）
// =====================
const sessions = new Map();

function genSessionId() {
  return Math.random().toString(36).substring(2, 10);
}

function startStream(ws, sessionId, startIndex) {
  const existing = sessions.get(sessionId);
  if (existing && existing.interval) clearInterval(existing.interval);

  let idx = startIndex;
  const interval = setInterval(() => {
    if (idx >= SSE_CONTENT.length) {
      clearInterval(interval);
      sessions.delete(sessionId);
      if (ws.readyState === ws.OPEN) ws.send(JSON.stringify({ type: 'done', sessionId }));
      return;
    }
    if (ws.readyState !== ws.OPEN) {
      clearInterval(interval);
      sessions.set(sessionId, { lastParagraphId: idx, interval: null });
      return;
    }
    ws.send(JSON.stringify({ type: 'paragraph', id: idx, text: SSE_CONTENT[idx], sessionId, done: false }));
    sessions.set(sessionId, { lastParagraphId: idx, interval });
    idx++;
  }, 1200);

  sessions.set(sessionId, { lastParagraphId: idx - 1, interval });
}

function handleDemoWS(ws, url) {
  const sessionIdParam = url.searchParams.get('sessionId');
  const lastIdParam = url.searchParams.get('lastId');

  if (sessionIdParam && lastIdParam) {
    const startIndex = parseInt(lastIdParam) + 1;
    ws.send(JSON.stringify({ type: 'resume', sessionId: sessionIdParam, resumeFrom: startIndex, message: `继续从第 ${startIndex + 1} 段推送` }));
    startStream(ws, sessionIdParam, startIndex);
  } else {
    const sessionId = genSessionId();
    ws.send(JSON.stringify({ type: 'connected', sessionId, message: `sessionId=${sessionId}，开始推送` }));
    startStream(ws, sessionId, 0);
  }

  ws.on('message', (msg) => {
    try { const data = JSON.parse(msg); if (data.type === 'ping') ws.send(JSON.stringify({ type: 'pong' })); } catch (e) {}
  });
  ws.on('close', () => {});
}

// =====================
// AI Chat — SSE 方案（Step 5a）
// 优势：续传由浏览器自动处理，EventSource 自动带 Last-Event-ID 重连
// =====================

// 模拟 LLM 返回的 token 列表（与 WS 方案共用）
const AI_CHUNKS = [
  "我", "来", "为", "你", "详细", "解释", "一下", "这个", "概念", "。",
  "首", "先", "，", "流", "式", "接", "口", "是", "一", "种", "非", "常",
  "实", "用", "的", "技", "术", "，", "它", "允", "许", "服", "务", "器",
  "边", "处", "理", "边", "返", "回", "结", "果", "，", "而", "不", "必",
  "等", "待", "全", "部", "完", "成", "后", "再", "一", "次", "性", "发", "送", "。",
  "这", "就", "像", "我", "们", "在", "使", "用", "C", "hat", "G", "PT",
  "时", "看", "到", "的", "打", "字", "效", "果", "，", "一", "个", "字",
  "一", "个", "字", "地", "出", "现", "，", "这", "就", "是", "流", "式",
  "响", "应", "的", "典", "型", "应", "用", "。", "对", "于", "企", "业", "级",
  "应", "用", "，", "我", "们", "通", "常", "会", "使", "用", "R", "ed", "is",
  "来", "存", "储", "流", "式", "会", "话", "状", "态", "，", "这", "样",
  "即", "使", "服", "务", "器", "重", "启", "，", "客", "户", "端", "也",
  "能", "从", "断", "点", "恢", "复", "，", "保", "证", "用", "户", "体", "验", "。"
];

// AI session 存储（与 WS 方案共用）
const aiSessions = new Map();

function genAISessionId() {
  return 'ai-' + Math.random().toString(36).substring(2, 10);
}
// AI_CHUNKS 和 aiSessions 在下面统一声明

// =====================
// AI Chat — SSE 端点
// POST /api/ai/sse/start → 创建 session，返回 sessionId
// GET  /api/ai/sse/stream → SSE 流，续传时 URL 带 ?sessionId=xxx&lastEventId=N
// =====================

// 优先从 query 读 sessionId（续传时 EventSource 重连不带 query，需要 query param）
// 但 EventSource 重连时浏览器会自动带 Last-Event-ID 头，服务器读取即可续传
app.post('/api/ai/sse/start', (req, res) => {
  const { prompt, model } = req.body;
  const sessionId = genAISessionId();
  aiSessions.set(sessionId, {
    prompt: prompt || '请解释什么是流式接口',
    model: model || 'gpt-4',
    chunks: [],
    lastSentIndex: -1,
    _currentTimer: null,
  });
  res.json({ sessionId, status: 'started', protocol: 'sse' });
});

app.get('/api/ai/sse/stream', (req, res) => {
  const sessionId = req.query.sessionId || '';
  const session = aiSessions.get(sessionId);
  if (!session) {
    res.status(404).json({ error: 'Session not found，请先调用 POST /api/ai/sse/start 创建 session' });
    return;
  }

  // EventSource 自动重连时会带 Last-Event-ID，续传全自动化
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

  // 如果是续传（startIndex > 0），先发一个系统消息
  if (startIndex > 0) {
    res.write(`event: system\ndata: [RESUME] 续传成功，已跳过前 ${startIndex} 个 token，从第 ${startIndex + 1} 个继续\n\n`);
  } else {
    res.write(`event: system\ndata: [START] 开始生成，共 ${AI_CHUNKS.length} 个 token\n\n`);
  }

  let idx = startIndex;
  let stopped = false;

  function scheduleNext() {
    if (stopped || idx >= AI_CHUNKS.length) {
      if (!stopped) {
        res.write(`id: ${idx - 1}\nevent: done\ndata: [DONE]\n\n`);
        res.end();
      }
      return;
    }
    const delay = 60 + Math.floor(Math.random() * 140);
    const timer = setTimeout(() => {
      if (stopped) return;
      res.write(`id: ${idx}\nevent: chunk\ndata: ${AI_CHUNKS[idx]}\n\n`);
      session.chunks[idx] = AI_CHUNKS[idx];
      session.lastSentIndex = idx;
      idx++;
      scheduleNext();
    }, delay);
    session._currentTimer = timer;
  }

  scheduleNext();

  req.on('close', () => {
    stopped = true;
    if (session._currentTimer) clearTimeout(session._currentTimer);
    console.log(`SSE AI session ${sessionId} paused at token ${session.lastSentIndex}`);
  });
});

// =====================
// AI Chat — WebSocket 方案（Step 5b）
// =====================
app.post('/api/ai/ws/start', (req, res) => {
  const { prompt, model } = req.body;
  const sessionId = genAISessionId();
  aiSessions.set(sessionId, {
    prompt: prompt || '请解释什么是流式接口',
    model: model || 'gpt-4',
    chunks: [],
    lastSentIndex: -1,
    _currentTimer: null,
  });
  res.json({ sessionId, status: 'started', protocol: 'ws' });
});

function handleAIChat(ws, url) {
  const sessionId = url.searchParams.get('sessionId');
  const lastChunkId = url.searchParams.get('lastChunkId');
  const session = aiSessions.get(sessionId);

  if (!session) {
    ws.send(JSON.stringify({ type: 'error', message: 'Session not found' }));
    ws.close();
    return;
  }

  let startIndex = 0;
  if (lastChunkId !== null && lastChunkId !== '') {
    startIndex = parseInt(lastChunkId) + 1;
    ws.send(JSON.stringify({
      type: 'resume', sessionId, resumeFrom: startIndex,
      message: `续传成功！已跳过前 ${startIndex} 个 token`
    }));
  } else {
    ws.send(JSON.stringify({
      type: 'start', sessionId, model: session.model,
      prompt: session.prompt, totalTokens: AI_CHUNKS.length
    }));
  }

  for (let i = startIndex; i <= session.lastSentIndex; i++) {
    if (session.chunks[i]) {
      ws.send(JSON.stringify({ type: 'chunk', id: i, text: session.chunks[i], sessionId, buffered: true }));
    }
  }

  let idx = session.lastSentIndex + 1;
  let stopped = false;

  function scheduleNext() {
    if (stopped || idx >= AI_CHUNKS.length) {
      if (!stopped) ws.send(JSON.stringify({ type: 'done', id: AI_CHUNKS.length - 1, sessionId }));
      return;
    }
    const delay = 60 + Math.floor(Math.random() * 140);
    const timer = setTimeout(() => {
      if (ws.readyState !== ws.OPEN) { stopped = true; if (session._currentTimer) clearTimeout(session._currentTimer); return; }
      ws.send(JSON.stringify({ type: 'chunk', id: idx, text: AI_CHUNKS[idx], sessionId, buffered: false }));
      session.chunks[idx] = AI_CHUNKS[idx];
      session.lastSentIndex = idx;
      idx++;
      scheduleNext();
    }, delay);
    session._currentTimer = timer;
  }

  scheduleNext();

  ws.on('close', () => { stopped = true; if (session._currentTimer) clearTimeout(session._currentTimer); });
  ws.on('error', () => { stopped = true; });
}

server.listen(PORT, () => {
  console.log(`Node server running on http://localhost:${PORT}`);
  console.log(`AI Chat: POST http://localhost:${PORT}/api/chat`);
  console.log(`AI WS:   ws://localhost:${PORT}/ws/chat?sessionId=xxx`);
});
