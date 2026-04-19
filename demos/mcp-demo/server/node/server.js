/**
 * Node.js MCP Server with SSE Transport
 *
 * MCP Client-Server Architecture:
 * ┌─────────────────────────────────────────────────────────────┐
 * │                        Host (Browser/AI)                    │
 * │   ┌─────────────┐                                           │
 * │   │ MCP Client  │ ◄──── SSE (HTTP)                         │
 * │   │   (JS)      │                                           │
 * │   └─────────────┘                                           │
 * └─────────────────────────────────────────────────────────────┘
 *                           │
 *                           ▼
 * ┌──────────────────────────────────────────────────────────────┐
 * │   Node.js MCP Server (port 8101)                           │
 * │   ┌─────────────────────────────────────────┐               │
 * │   │ Tool: get_current_weather(city: str)    │               │
 * │   │ - Express 模拟 MCP 协议                 │               │
 * │   │ - Returns fixed weather data            │               │
 * │   └─────────────────────────────────────────┘               │
 * └──────────────────────────────────────────────────────────────┘
 *
 * Transport Layer:
 * - stdio: 本地进程通信 Claude Desktop 插件
 * - SSE:  远程HTTP通信 浏览器/Web服务 ◄── 本Demo
 */

import express from 'express';
import cors from 'cors';
import crypto from 'crypto';

const app = express();
const PORT = 8101;

// Middleware
app.use(cors());
app.use(express.json());

// In-memory storage for connected SSE clients
// In production, you'd use a proper message queue or pub/sub system
const connectedClients = new Map();

/**
 * MCP Tool Definition
 */
const mcpTools = [
  {
    name: "get_current_weather",
    description: "获取指定城市的当前天气信息，返回城市名、天气状况、温度和湿度",
    inputSchema: {
      type: "object",
      properties: {
        city: {
          type: "string",
          description: "城市名称，例如：北京、上海、东京"
        }
      },
      required: ["city"]
    }
  }
];

/**
 * Tool Handler: get_current_weather
 * @param {string} city - 城市名称
 * @returns {Object} 包含城市、天气、温度和湿度的字典
 */
function getCurrentWeather(city) {
  return {
    city: city,
    weather: "晴天",
    temperature: "25°C",
    humidity: "50%"
  };
}

// =============================================================================
// MCP Protocol Handlers
// =============================================================================

/**
 * Handle tools/list request
 *
 * MCP Protocol:
 * Request:  {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
 * Response: {"jsonrpc": "2.0", "id": 1, "result": {"tools": [...]}}
 */
function handleToolsList() {
  return mcpTools;
}

/**
 * Handle tools/call request
 *
 * MCP Protocol:
 * Request:  {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
 *            "params": {"name": "get_current_weather", "arguments": {"city": "北京"}}}
 * Response: {"jsonrpc": "2.0", "id": 2, "result": {"content": [{"type": "text", "text": "..."}]}}
 */
function handleToolsCall(toolName, arguments_) {
  if (toolName === "get_current_weather") {
    const result = getCurrentWeather(arguments_.city);
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(result, null, 2)
        }
      ]
    };
  } else {
    throw new Error(`Unknown tool: ${toolName}`);
  }
}

// =============================================================================
// SSE Endpoint - Server-Sent Events for client notifications
// =============================================================================

/**
 * GET /sse - SSE endpoint for browser/Web clients
 *
 * Server-Sent Events (SSE) 是一种基于HTTP的单向通信协议，
 * 服务器通过这个端点向浏览器客户端推送事件。
 *
 * MCP SSE 流程:
 * 1. 客户端连接 /sse 端点，建立长连接
 * 2. 服务器可随时通过此连接向客户端发送事件
 * 3. 客户端通过 POST /mcp 发送请求
 */
app.get('/sse', (req, res) => {
  const clientId = crypto.randomUUID();
  const queue = [];

  // Store client connection
  connectedClients.set(clientId, queue);

  // Set SSE headers
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.setHeader('Access-Control-Allow-Origin', '*');

  // Send connection established event
  res.write(`event: connected\n`);
  res.write(`data: ${JSON.stringify({ client_id: clientId, status: 'connected' })}\n\n`);

  // Heartbeat interval to keep connection alive
  const heartbeatInterval = setInterval(() => {
    res.write(`event: heartbeat\n`);
    res.write(`data: ${JSON.stringify({ status: 'alive' })}\n\n`);
  }, 30000);

  // Clean up on client disconnect
  req.on('close', () => {
    clearInterval(heartbeatInterval);
    connectedClients.delete(clientId);
  });
});

// =============================================================================
// MCP Protocol Endpoint - JSON-RPC over HTTP
// =============================================================================

/**
 * POST /mcp - MCP Protocol Endpoint
 *
 * 处理 MCP JSON-RPC 2.0 请求:
 * - tools/list: 列出所有可用工具
 * - tools/call: 调用指定工具
 *
 * 请求格式:
 * {
 *     "jsonrpc": "2.0",
 *     "id": 1,
 *     "method": "tools/list",           // 或 "tools/call"
 *     "params": {}                       // tools/call 时需要 name 和 arguments
 * }
 *
 * 响应格式:
 * {
 *     "jsonrpc": "2.0",
 *     "id": 1,
 *     "result": {...}                    // 成功时
 * }
 * 或
 * {
 *     "jsonrpc": "2.0",
 *     "id": 1,
 *     "error": {...}                     // 失败时
 * }
 */
app.post('/mcp', (req, res) => {
  const request = req.body;

  // Validate JSON-RPC 2.0 format
  if (request.jsonrpc !== "2.0") {
    return res.status(400).json({
      jsonrpc: "2.0",
      id: request.id || null,
      error: {
        code: -32600,
        message: "Invalid JSON-RPC 2.0 request"
      }
    });
  }

  try {
    if (request.method === "tools/list") {
      const result = handleToolsList();
      return res.json({
        jsonrpc: "2.0",
        id: request.id,
        result: { tools: result }
      });

    } else if (request.method === "tools/call") {
      if (!request.params || !request.params.name) {
        throw new Error("Missing 'name' in params");
      }
      const toolName = request.params.name;
      const arguments_ = request.params.arguments || {};
      const result = handleToolsCall(toolName, arguments_);
      return res.json({
        jsonrpc: "2.0",
        id: request.id,
        result: result
      });

    } else {
      return res.status(404).json({
        jsonrpc: "2.0",
        id: request.id,
        error: {
          code: -32601,
          message: `Method not found: ${request.method}`
        }
      });
    }

  } catch (error) {
    return res.status(400).json({
      jsonrpc: "2.0",
      id: request.id,
      error: {
        code: -32602,
        message: error.message
      }
    });
  }
});

// =============================================================================
// Health Check Endpoint
// =============================================================================

/**
 * GET /health - Health check endpoint
 *
 * 用于验证服务器是否正常运行
 */
app.get('/health', (req, res) => {
  res.json({
    status: "healthy",
    service: "MCP Weather Server (Node.js)",
    version: "1.0.0",
    port: PORT
  });
});

// =============================================================================
// Server Startup
// =============================================================================

app.listen(PORT, '0.0.0.0', () => {
  console.log('='.repeat(60));
  console.log('MCP Weather Server with SSE Transport (Node.js)');
  console.log('='.repeat(60));
  console.log(`Server running on http://localhost:${PORT}`);
  console.log('');
  console.log('Endpoints:');
  console.log('  GET  /sse   - SSE endpoint for browser clients');
  console.log('  POST /mcp   - MCP protocol endpoint (JSON-RPC)');
  console.log('  GET  /health - Health check');
  console.log('');
  console.log('Available Tools:');
  mcpTools.forEach(tool => {
    console.log(`  - ${tool.name}: ${tool.description}`);
  });
  console.log('='.repeat(60));
});
