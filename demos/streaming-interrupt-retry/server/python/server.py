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
    last_event_id = request.headers.get("Last-Event-ID", "")
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
# =====================
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json({"type": "connected", "data": "welcome"})
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                msg_type = msg.get("type")
                if msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
                elif msg_type == "message":
                    await websocket.send_json({
                        "type": "message",
                        "data": f"echo: {msg.get('data')}",
                        "timestamp": datetime.now().isoformat()
                    })
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "data": "invalid json"})
    except Exception:
        pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8088)
