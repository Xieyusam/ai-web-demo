/**
 * Node.js MCP Server with @modelcontextprotocol/sdk
 *
 * MCP 核心概念：
 * ┌─────────────────────────────────────────────────────────────────┐
 * │                      AI Application (Host)                      │
 * │   ┌─────────────────────────────────────────────────────────┐   │
 * │   │                    MCP Client                           │   │
 * │   │   1. 发现工具 → tools/list                               │   │
 * │   │   2. 调用工具 → tools/call                               │   │
 * │   └─────────────────────────────────────────────────────────┘   │
 * └─────────────────────────────────────────────────────────────────┘
 *                                │
 *                                │ stdio (本地) / SSE (远程)
 *                                ▼
 * ┌─────────────────────────────────────────────────────────────────┐
 * │  MCP Server (Node.js) · 端口 8101                               │
 * │   server.tool()                                                │
 * │   - calculate_bmi(height_cm, weight_kg)                        │
 * └─────────────────────────────────────────────────────────────────┘
 *
 * 传输层选择：
 * - stdio: Claude Desktop 插件，本地进程通信
 * - SSE:  Web 服务，远程 HTTP 通信 ◄── 本 Demo 选择
 *
 * MCP 协议消息格式 (JSON-RPC 2.0):
 * - tools/list: 列出所有可用工具
 * - tools/call: 调用指定工具
 *
 * 安装依赖：
 * npm install
 *
 * 启动服务：
 * npm start
 *
 * 测试：
 * curl http://localhost:8101/health
 */

import express from 'express';
import cors from 'cors';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';

const app = express();
const PORT = 8101;

app.use(cors());
app.use(express.json());

// =============================================================================
// 创建 MCP Server
// =============================================================================
const mcpServer = new McpServer({
  name: 'bmi-server',
  version: '1.0.0'
});

// =============================================================================
// MCP 工具定义
// =============================================================================
mcpServer.tool(
  'calculate_bmi',
  '计算 BMI (Body Mass Index) 并返回健康建议',
  {
    height_cm: z.number().describe('身高（厘米）'),
    weight_kg: z.number().describe('体重（公斤）')
  },
  async ({ height_cm, weight_kg }) => {
    const height_m = height_cm / 100;
    const bmi = weight_kg / (height_m * height_m);

    let category, suggestion;
    if (bmi < 18.5) {
      category = '偏瘦';
      suggestion = '建议适当增加营养摄入，保持均衡饮食。';
    } else if (bmi < 24) {
      category = '正常';
      suggestion = '继续保持健康的饮食和运动习惯。';
    } else if (bmi < 28) {
      category = '偏胖';
      suggestion = '建议适当控制饮食，增加运动量。';
    } else {
      category = '肥胖';
      suggestion = '建议咨询医生，制定科学的减重计划。';
    }

    const result = {
      bmi: Math.round(bmi * 100) / 100,
      category,
      suggestion,
      height_cm,
      weight_kg
    };

    return {
      content: [{ type: 'text', text: JSON.stringify(result) }]
    };
  }
);

// =============================================================================
// MCP JSON-RPC 端点
// =============================================================================
const mcpTools = [
  {
    name: 'calculate_bmi',
    description: '计算 BMI (Body Mass Index) 并返回健康建议',
    inputSchema: {
      type: 'object',
      properties: {
        height_cm: { type: 'number', description: '身高（厘米）' },
        weight_kg: { type: 'number', description: '体重（公斤）' }
      },
      required: ['height_cm', 'weight_kg']
    }
  }
];

// 辅助函数：BMI 计算
async function calculateBmiHandler(height_cm, weight_kg) {
  const height_m = height_cm / 100;
  const bmi = weight_kg / (height_m * height_m);

  let category, suggestion;
  if (bmi < 18.5) {
    category = '偏瘦';
    suggestion = '建议适当增加营养摄入，保持均衡饮食。';
  } else if (bmi < 24) {
    category = '正常';
    suggestion = '继续保持健康的饮食和运动习惯。';
  } else if (bmi < 28) {
    category = '偏胖';
    suggestion = '建议适当控制饮食，增加运动量。';
  } else {
    category = '肥胖';
    suggestion = '建议咨询医生，制定科学的减重计划。';
  }

  return {
    bmi: Math.round(bmi * 100) / 100,
    category,
    suggestion,
    height_cm,
    weight_kg
  };
}

// MCP 端点
app.post('/mcp', async (req, res) => {
  const { method, params, id } = req.body;

  try {
    if (method === 'tools/list') {
      res.json({
        jsonrpc: '2.0',
        id,
        result: { tools: mcpTools }
      });
    } else if (method === 'tools/call') {
      const { name, arguments: args } = params;
      if (name === 'calculate_bmi') {
        const result = await calculateBmiHandler(args.height_cm, args.weight_kg);
        res.json({
          jsonrpc: '2.0',
          id,
          result: {
            content: [{ type: 'text', text: JSON.stringify(result) }]
          }
        });
      } else {
        res.status(400).json({ jsonrpc: '2.0', id, error: `Unknown tool: ${name}` });
      }
    } else {
      res.status(400).json({ jsonrpc: '2.0', id, error: 'Method not found' });
    }
  } catch (error) {
    res.status(500).json({ jsonrpc: '2.0', id, error: error.message });
  }
});

// 健康检查
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'MCP BMI Server (Node.js)',
    version: '1.0.0',
    port: PORT,
    mcp_server: 'bmi-server'
  });
});

// 演示页面
app.get('/', (req, res) => {
  res.sendFile('static/index.html', { root: './' });
});

app.listen(PORT, () => {
  console.log(`
============================================================
Node.js MCP BMI Server
============================================================
MCP Server: bmi-server
Port: ${PORT}

MCP 工具:
  - calculate_bmi(height_cm: number, weight_kg: number)

使用说明:
  1. 启动服务: npm start
  2. 打开页面: http://localhost:${PORT}
  3. 健康检查: http://localhost:${PORT}/health

API 端点:
  GET  /           - 演示页面
  GET  /health     - 健康检查
  POST /mcp        - MCP JSON-RPC 端点

============================================================
  `);
});