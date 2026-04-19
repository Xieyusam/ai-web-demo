"""
Python MCP Server with fastmcp SDK

MCP 核心概念：
┌─────────────────────────────────────────────────────────────────┐
│                      AI Application (Host)                        │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                    MCP Client                             │   │
│   │   1. 发现工具 → tools/list                               │   │
│   │   2. 调用工具 → tools/call                               │   │
│   └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                               │
                               │ stdio (本地) / SSE (远程)
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      MCP Server (本服务)                         │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │  @mcp.tool() 装饰器定义工具                             │   │
│   │  - calculate_bmi(height_cm, weight_kg)                  │   │
│   └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘

传输层选择：
- stdio: Claude Desktop 插件，本地进程通信
- SSE:  Web 服务，远程 HTTP 通信 ◄── 本 Demo 选择

MCP 协议消息格式 (JSON-RPC 2.0):
- tools/list: 列出所有可用工具
- tools/call: 调用指定工具

安装依赖：
pip install -r requirements.txt

启动服务：
python main.py

测试：
curl http://localhost:8100/health
"""

import uvicorn
from fastmcp import FastMCP
import json

# =============================================================================
# 创建 MCP Server
# =============================================================================
# FastMCP 是 MCP Python SDK 的高级封装，简化了工具定义
mcp = FastMCP("bmi-server")

# =============================================================================
# MCP 工具定义
# =============================================================================
@mcp.tool()
def calculate_bmi(height_cm: float, weight_kg: float) -> dict:
    """
    计算 BMI (Body Mass Index) 并返回健康建议

    BMI 是国际上常用的衡量人体胖瘦程度以及是否健康的指标。

    Args:
        height_cm: 身高（厘米），例如 170
        weight_kg: 体重（公斤），例如 65

    Returns:
        dict: 包含 BMI 值、分类和健康建议

    BMI 分类标准（中国参考）：
    - < 18.5: 偏瘦
    - 18.5 ~ 24: 正常
    - 24 ~ 28: 偏胖
    - >= 28: 肥胖
    """
    # 计算 BMI
    height_m = height_cm / 100
    bmi = weight_kg / (height_m ** 2)

    # 根据 BMI 值判断分类（中国标准）
    if bmi < 18.5:
        category = "偏瘦"
        suggestion = "建议适当增加营养摄入，保持均衡饮食。"
    elif bmi < 24:
        category = "正常"
        suggestion = "继续保持健康的饮食和运动习惯。"
    elif bmi < 28:
        category = "偏胖"
        suggestion = "建议适当控制饮食，增加运动量。"
    else:
        category = "肥胖"
        suggestion = "建议咨询医生，制定科学的减重计划。"

    return {
        "bmi": round(bmi, 2),
        "category": category,
        "suggestion": suggestion,
        "height_cm": height_cm,
        "weight_kg": weight_kg
    }


# =============================================================================
# FastAPI 应用 + MCP 端点
# =============================================================================
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI(title="MCP BMI Server")
PORT = 8100

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    """返回演示页面"""
    return FileResponse("static/index.html")

@app.get("/health")
async def health():
    """健康检查端点"""
    return {
        "status": "healthy",
        "service": "MCP BMI Server (Python)",
        "version": "1.0.0",
        "port": PORT,
        "mcp_server": "bmi-server"
    }

@app.post("/mcp")
async def mcp_endpoint(request: dict):
    """MCP JSON-RPC 2.0 端点"""
    method = request.get("method", "")
    params = request.get("params", {})
    id = request.get("id")

    try:
        if method == "tools/list":
            # 返回工具列表
            return {
                "jsonrpc": "2.0",
                "id": id,
                "result": {
                    "tools": [
                        {
                            "name": "calculate_bmi",
                            "description": "计算 BMI (Body Mass Index) 并返回健康建议",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "height_cm": {"type": "number", "description": "身高（厘米）"},
                                    "weight_kg": {"type": "number", "description": "体重（公斤）"}
                                },
                                "required": ["height_cm", "weight_kg"]
                            }
                        }
                    ]
                }
            }
        elif method == "tools/call":
            # 调用工具
            name = params.get("name")
            args = params.get("arguments", {})

            if name == "calculate_bmi":
                height_cm = args.get("height_cm")
                weight_kg = args.get("weight_kg")

                # 复用 calculate_bmi 函数
                result = calculate_bmi(height_cm, weight_kg)

                return {
                    "jsonrpc": "2.0",
                    "id": id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]
                    }
                }
            else:
                return {"jsonrpc": "2.0", "id": id, "error": f"Unknown tool: {name}"}
        else:
            return {"jsonrpc": "2.0", "id": id, "error": "Method not found"}
    except Exception as e:
        return {"jsonrpc": "2.0", "id": id, "error": str(e)}


if __name__ == "__main__":
    print(f"""
============================================================
Python MCP BMI Server
============================================================
MCP Server: bmi-server
Port: {PORT}

MCP 工具:
  - calculate_bmi(height_cm: float, weight_kg: float)

使用说明:
  1. 启动服务: python main.py
  2. 打开页面: http://localhost:{PORT}
  3. 健康检查: http://localhost:{PORT}/health

API 端点:
  GET  /           - 演示页面
  GET  /health     - 健康检查
  POST /mcp        - MCP JSON-RPC 端点 (tools/list, tools/call)

============================================================
    """)

    uvicorn.run(app, host="0.0.0.0", port=PORT)