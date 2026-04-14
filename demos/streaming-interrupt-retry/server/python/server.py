from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import StreamingResponse, JSONResponse
from datetime import datetime
import asyncio
import json

app = FastAPI()


@app.get("/")
def root():
    return JSONResponse({"status": "ok", "server": "python"})


# =====================
# SSE 端点（Step 1 & 2）
# =====================
async def sse_generate(start_index: int = 0):
    total = 20
    for i in range(start_index, total):
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
