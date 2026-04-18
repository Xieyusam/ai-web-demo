/**
 * FastAPI 高并发对比教学 Demo - Node.js 端
 */

const express = require('express');
const cors = require('cors');
const path = require('path');

const app = express();
const PORT = 8090;

app.use(cors());
app.use(express.json());

const CURRENT_DIR = __dirname;

app.get('/async-llm', async (req, res) => {
  const start = Date.now();
  await new Promise(resolve => setTimeout(resolve, 2000));
  res.json({
    endpoint: 'async-llm',
    type: 'async handler + await setTimeout',
    elapsed_ms: Date.now() - start,
    timestamp: start / 1000
  });
});

app.get('/sync-llm', (req, res) => {
  const start = Date.now();
  while (Date.now() < start + 2000) {}
  res.json({
    endpoint: 'sync-llm',
    type: 'sync handler + while loop (同步阻塞)',
    elapsed_ms: Date.now() - start,
    timestamp: start / 1000
  });
});

app.get('/sse-test', (req, res) => {
  const type = req.query.type || 'async';
  const numCount = parseInt(req.query.count, 10) || 10;

  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.setHeader('X-Accel-Buffering', 'no');
  res.flushHeaders();

  const overallStart = Date.now();

  if (type === 'async') {
    const promises = [];
    for (let i = 0; i < numCount; i++) {
      promises.push((async (index) => {
        const start = Date.now();
        await new Promise(resolve => setTimeout(resolve, 2000));
        return { index, elapsed_ms: Date.now() - start };
      })(i));
    }

    Promise.all(promises).then(results => {
      results.forEach((result) => {
        res.write(`data: ${JSON.stringify({
          index: result.index + 1,
          elapsed_ms: result.elapsed_ms,
          total_elapsed_ms: Date.now() - overallStart,
          type
        })}\n\n`);
      });
      res.write(`data: ${JSON.stringify({ done: true, total_time_ms: Date.now() - overallStart })}\n\n`);
      res.end();
    });
  } else {
    for (let i = 0; i < numCount; i++) {
      const start = Date.now();
      while (Date.now() < start + 2000) {}
      res.write(`data: ${JSON.stringify({
        index: i + 1,
        elapsed_ms: Date.now() - start,
        total_elapsed_ms: Date.now() - overallStart,
        type
      })}\n\n`);
    }
    res.write(`data: ${JSON.stringify({ done: true, total_time_ms: Date.now() - overallStart })}\n\n`);
    res.end();
  }
});

app.get('/', (req, res) => {
  res.sendFile(path.join(CURRENT_DIR, 'static', 'index.html'));
});

app.use('/static', express.static(path.join(CURRENT_DIR, 'static')));

app.listen(PORT, () => {
  console.log(`Node.js Express server running on http://localhost:${PORT}`);
});
