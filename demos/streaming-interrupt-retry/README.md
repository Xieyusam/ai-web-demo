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

直接在浏览器打开 `demo.html`，选择语言后体验。

## 步骤说明

| Step | 内容 | 说明 |
|------|------|------|
| Step 1 | SSE 基础流 | 了解什么是 Server-Sent Events |
| Step 2 | SSE 中断与重试 | 学会用 EventSource 中断 + 续传 |
| Step 3 | WebSocket 基础流 | 了解双向通信，与 SSE 对比 |
| Step 4 | WebSocket 中断与重试 | 学会重连 + 状态恢复 |

## 技术栈

- 前端: Vue3 (CDN), Tailwind CSS (CDN)
- Node.js: Express, ws, cors
- Python: FastAPI, uvicorn

## 端口说明

- Node.js 服务: `http://localhost:8089`
- Python 服务: `http://localhost:8088`

demo.html 默认连接 Node.js 服务，切换语言后改为 Python 服务。
