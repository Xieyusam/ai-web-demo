from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import asyncio
import json
import os

app = FastAPI()

# 获取 server.py 所在目录的父目录（即 demo 根目录）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEMO_ROOT = os.path.join(BASE_DIR, '../..')

# 挂载静态文件
app.mount("/static", StaticFiles(directory=DEMO_ROOT), name="static")


@app.get("/")
def root():
    demo_path = os.path.join(DEMO_ROOT, 'demo.html')
    return FileResponse(demo_path)


# =====================
# SSE 端点（Step 1 & 2）
# 流式传输文本内容，支持通过 Last-Event-ID 续传
# =====================
SSE_CONTENT = [
    "【第一段】流式接口（Streaming API）是一种数据传输技术，允许服务器分批次将数据发送给客户端，而无需等待所有数据准备完毕。",
    "【第二段】与传统的请求-响应模式不同，流式接口在建立连接后，服务器可以持续不断地推送数据，直到所有内容传输完成。",
    "【第三段】SSE（Server-Sent Events）是实现流式接口的一种浏览器原生技术。它基于 HTTP 协议，服务器通过特定的 Content-Type（text/event-stream）向浏览器持续写入数据。",
    "【第四段】EventSource 是浏览器提供的 JavaScript API，用于接收 SSE 流。它会自动处理重连，并支持通过 Last-Event-ID 头部实现断点续传。",
    "【第五段】当网络中断或用户主动关闭连接时，SSE 流会终止。重新连接后，浏览器会自动带上 Last-Event-ID，服务器据此从断点继续发送剩余内容。",
    "【第六段】这就好比在听有声书时突然暂停，再次播放时会从暂停处继续，而不是从头开始朗读。这就是「续传」的核心原理。",
    "【第七段】WebSocket 是另一种双向通信协议，与 SSE 不同，它不基于 HTTP，而是建立了独立的 TCP 连接。WebSocket 一旦断开，没有自动续传机制，需要在应用层自行实现。",
    "【第八段】实际应用中，流式接口广泛用于：实时日志推送、AI 对话打字效果、股票行情更新、进度条通知等需要「服务器持续推送」的场景。",
]

async def sse_generate(start_index: int = 0):
    for idx in range(start_index, len(SSE_CONTENT)):
        await asyncio.sleep(1.2)
        yield f"id: {idx}\nevent: message\ndata: {SSE_CONTENT[idx]}\n\n"
    yield f"event: done\ndata: [DONE]\n\n"


@app.get("/sse/stream")
async def sse_stream(request: Request):
    # 优先从 query 参数读取（前端手动续传时通过 URL 传递）
    # 次选 Last-Event-ID 头（浏览器自动重连时携带）
    last_event_id = request.query_params.get("lastEventId") or request.headers.get("Last-Event-ID", "")
    start_index = 0
    if last_event_id != "":
        try:
            start_index = int(last_event_id) + 1
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


# =====================
# WebSocket 端点（Step 3 & 4）
# 服务器主动推送流式文本内容，支持 session 续传
# =====================
import random
import string

# session 池：sessionId -> { last_paragraph_id, task }
sessions = {}

def gen_session_id():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

async def send_paragraph(websocket, session_id, paragraph_id):
    if paragraph_id >= len(SSE_CONTENT):
        return False
    try:
        await websocket.send_json({
            "type": "paragraph",
            "id": paragraph_id,
            "text": SSE_CONTENT[paragraph_id],
            "session_id": session_id,
            "done": False
        })
        return True
    except Exception:
        return False

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    url = websocket.url
    session_id_param = url.query_params.get("sessionId")
    last_id_param = url.query_params.get("lastId")

    if session_id_param and last_id_param:
        # 续传模式
        session_id = session_id_param
        start_index = int(last_id_param) + 1
        await websocket.send_json({
            "type": "resume",
            "session_id": session_id,
            "resume_from": start_index,
            "message": f"服务器已恢复，继续从第 {start_index + 1} 段推送"
        })
    else:
        # 新连接
        session_id = gen_session_id()
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "message": f"连接成功，sessionId={session_id}，开始推送"
        })
        start_index = 0

    idx = start_index
    session_task = None

    async def stream_task():
        nonlocal idx, session_task
        while idx < len(SSE_CONTENT):
            ok = await send_paragraph(websocket, session_id, idx)
            if not ok:
                sessions[session_id] = {"last_paragraph_id": idx}
                break
            sessions[session_id] = {"last_paragraph_id": idx}
            idx += 1
            await asyncio.sleep(1.2)
        else:
            try:
                await websocket.send_json({"type": "done", "session_id": session_id})
            except Exception:
                pass
            if session_id in sessions:
                del sessions[session_id]

    async def background_stream():
        await stream_task()

    # 启动后台推送任务
    task = asyncio.create_task(background_stream())
    session_task = task

    # 监听客户端关闭
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except Exception:
        # 客户端断开，取消后台任务
        task.cancel()
        sessions[session_id] = {"last_paragraph_id": idx}
        print(f"WS session {session_id} paused at paragraph {idx}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8088)


# =====================
# AI Chat — SSE 方案（Step 5a）
# POST /api/ai/sse/start → 创建 session
# GET  /api/ai/sse/stream → SSE 流，支持 Last-Event-ID 续传
# =====================

AI_CHUNKS = [
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
]

ai_sessions = {}

def gen_ai_session_id():
    return 'ai-' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

@app.post("/api/ai/sse/start")
async def ai_sse_start(request: Request):
    body = await request.json()
    session_id = gen_ai_session_id()
    ai_sessions[session_id] = {
        "prompt": body.get("prompt", "请解释什么是流式接口"),
        "model": body.get("model", "gpt-4"),
        "chunks": [],
        "last_sent_index": -1,
    }
    return JSONResponse({"sessionId": session_id, "status": "started", "protocol": "sse"})

async def ai_sse_generate(session_id: str, start_index: int = 0):
    session = ai_sessions.get(session_id)
    if not session:
        return

    if start_index > 0:
        yield f"event: system\ndata: [RESUME] 续传成功，已跳过前 {start_index} 个 token，从第 {start_index + 1} 个继续\n\n"
    else:
        yield f"event: system\ndata: [START] 开始生成，共 {len(AI_CHUNKS)} 个 token\n\n"

    for idx in range(start_index, len(AI_CHUNKS)):
        delay = 0.06 + random.random() * 0.14
        await asyncio.sleep(delay)
        yield f"id: {idx}\nevent: chunk\ndata: {AI_CHUNKS[idx]}\n\n"
        session["chunks"].append(AI_CHUNKS[idx])
        session["last_sent_index"] = idx

    yield f"id: {len(AI_CHUNKS) - 1}\nevent: done\ndata: [DONE]\n\n"

@app.get("/api/ai/sse/stream")
async def ai_sse_stream(request: Request):
    session_id = request.query_params.get("sessionId", "")
    session = ai_sessions.get(session_id)
    if not session:
        return JSONResponse({"error": "Session not found"}, status_code=404)

    last_event_id = request.query_params.get("lastEventId") or request.headers.get("Last-Event-ID", "")
    start_index = 0
    if last_event_id:
        try:
            start_index = int(last_event_id) + 1
        except ValueError:
            start_index = 0

    return StreamingResponse(
        ai_sse_generate(session_id, start_index),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


# =====================
# AI Chat — WebSocket 方案（Step 5b）
# =====================
@app.post("/api/ai/ws/start")
async def ai_ws_start(request: Request):
    body = await request.json()
    session_id = gen_ai_session_id()
    ai_sessions[session_id] = {
        "prompt": body.get("prompt", "请解释什么是流式接口"),
        "model": body.get("model", "gpt-4"),
        "chunks": [],
        "last_sent_index": -1,
    }
    return JSONResponse({"sessionId": session_id, "status": "started", "protocol": "ws"})

@app.websocket("/ws/chat")
async def ai_websocket(websocket: WebSocket):
    await websocket.accept()
    url = websocket.url
    session_id = url.query_params.get("sessionId")
    last_chunk_id = url.query_params.get("lastChunkId")
    session = ai_sessions.get(session_id)

    if not session:
        await websocket.send_json({"type": "error", "message": "Session not found"})
        await websocket.close()
        return

    start_index = 0
    if last_chunk_id is not None and last_chunk_id != "":
        start_index = int(last_chunk_id) + 1
        await websocket.send_json({
            "type": "resume", "sessionId": session_id, "resumeFrom": start_index,
            "message": f"续传成功！已跳过前 {start_index} 个 token"
        })
    else:
        await websocket.send_json({
            "type": "start", "sessionId": session_id, "model": session["model"],
            "prompt": session["prompt"], "totalTokens": len(AI_CHUNKS)
        })

    # replay buffered tokens
    for i in range(start_index, session["last_sent_index"] + 1):
        if session["chunks"][i]:
            await websocket.send_json({
                "type": "chunk", "id": i, "text": session["chunks"][i],
                "sessionId": session_id, "buffered": True
            })

    idx = session["last_sent_index"] + 1

    async def stream_task():
        nonlocal idx
        while idx < len(AI_CHUNKS):
            delay = 0.06 + random.random() * 0.14
            await asyncio.sleep(delay)
            try:
                await websocket.send_json({
                    "type": "chunk", "id": idx, "text": AI_CHUNKS[idx],
                    "sessionId": session_id, "buffered": False
                })
                session["chunks"].append(AI_CHUNKS[idx])
                session["last_sent_index"] = idx
                idx += 1
            except Exception:
                session["last_sent_index"] = idx - 1
                break
        else:
            try:
                await websocket.send_json({"type": "done", "id": len(AI_CHUNKS) - 1, "sessionId": session_id})
            except Exception:
                pass
            if session_id in ai_sessions:
                del ai_sessions[session_id]

    task = asyncio.create_task(stream_task())

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except Exception:
        task.cancel()
        session["last_sent_index"] = idx - 1
        print(f"AI WS session {session_id} paused at token {idx - 1}")
