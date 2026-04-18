"""
FastAPI 高并发对比教学 Demo - Python 端

演示 async def + await asyncio.sleep vs def + time.sleep 的并发性能差异
"""

import time
import asyncio
import os
import json
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="FastAPI 高并发对比 Demo")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))


@app.get("/async-llm")
async def async_llm():
    start = time.time()
    await asyncio.sleep(2)
    elapsed = (time.time() - start) * 1000
    return JSONResponse({
        "endpoint": "async-llm",
        "type": "async def + await asyncio.sleep",
        "elapsed_ms": round(elapsed, 2),
        "timestamp": start
    })


@app.get("/sync-llm")
def sync_llm():
    start = time.time()
    time.sleep(2)
    elapsed = (time.time() - start) * 1000
    return JSONResponse({
        "endpoint": "sync-llm",
        "type": "def + time.sleep (同步阻塞)",
        "elapsed_ms": round(elapsed, 2),
        "timestamp": start
    })


async def call_async_llm(client, index):
    """内部调用 async-llm"""
    start = time.time()
    await asyncio.sleep(2)
    elapsed = (time.time() - start) * 1000
    return {"index": index, "elapsed_ms": round(elapsed, 2), "start": start}


def call_sync_llm(index):
    """内部调用 sync-llm（同步）"""
    start = time.time()
    time.sleep(2)
    elapsed = (time.time() - start) * 1000
    return {"index": index, "elapsed_ms": round(elapsed, 2), "start": start}


async def sse_async_generator(llm_type: str, count: int):
    """
    SSE 流式推送：服务器内部并发调用，展示真实并行效果

    原理：服务器使用 httpx 异步并发发起多个请求，
    由于 asyncio.sleep 不阻塞事件循环，所有请求真正并行执行
    """
    overall_start = time.time()

    if llm_type == "async":
        # 使用 asyncio 并发调用
        tasks = [call_async_llm(None, i) for i in range(count)]
        results = await asyncio.gather(*tasks)
    else:
        # 同步调用（模拟串行）
        results = [call_sync_llm(i) for i in range(count)]

    # 按完成顺序流式发送
    for i, result in enumerate(results, 1):
        elapsed = (time.time() - overall_start) * 1000
        data = {
            "index": result["index"] + 1,
            "elapsed_ms": result["elapsed_ms"],
            "total_elapsed_ms": round(elapsed, 2),
            "type": llm_type
        }
        yield f"data: {json.dumps(data)}\n\n"
        await asyncio.sleep(0)  # 让出控制权，允许其他协程执行

    # 发送完成信号
    total_time = (time.time() - overall_start) * 1000
    yield f"data: {{\"done\": true, \"total_time_ms\": {round(total_time, 2)}}}\n\n"


@app.get("/sse-test")
async def sse_test(
    type: str = Query(..., description="async 或 sync"),
    count: int = Query(10, description="并发数量")
):
    """
    SSE 端点：服务器内部并发调用，绕过浏览器连接数限制

    使用方式：GET /sse-test?type=async&count=10
    """
    return StreamingResponse(
        sse_async_generator(type, count),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/")
def index():
    return FileResponse(os.path.join(CURRENT_DIR, "static", "index.html"))


static_dir = os.path.join(CURRENT_DIR, "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8091)
