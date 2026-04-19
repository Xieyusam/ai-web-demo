/**
 * Node.js AI Agent - MCP Client 实现
 *
 * 功能：
 * 1. 接收用户对话
 * 2. 调用 LLM 判断是否需要使用工具
 * 3. 通过 MCP Client 调用 MCP Server 的工具
 * 4. 返回结果给用户
 *
 * MCP 调用流程：
 * ┌─────────────────────────────────────────────────────────────────┐
 * │                      AI Agent Service                            │
 * │   ┌─────────────────────┐    ┌─────────────────────────────┐   │
 * │   │   AI Agent          │───►│   MCP Server (端口 8101)     │   │
 * │   │   (MCP Client)      │    │   提供 calculate_bmi 工具    │   │
 * │   └─────────────────────┘    └─────────────────────────────┘   │
 * │           │                                                 │
 * │   ┌───────┴───────┐                                        │
 * │   │  LLM API     │  ◄── OPENAI_API_KEY / ANTHROPIC_API_KEY │
 * │   └───────────────┘                                        │
 * └─────────────────────────────────────────────────────────────────┘
 *
 * 启动：
 * npm run agent
 *
 * 测试：
 * curl -X POST http://localhost:8201/chat -H "Content-Type: application/json" -d '{"message":"计算身高170体重65的BMI"}'
 */

import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';

// 加载环境变量
dotenv.config();

const app = express();
const AGENT_PORT = 8201;
const MCP_SERVER_URL = 'http://localhost:8101';

// 读取 API Keys
const OPENAI_API_KEY = process.env.OPENAI_API_KEY || '';
const ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY || '';
const MINIMAX_API_KEY = process.env.MINIMAX_API_KEY || '';
const DEFAULT_PROVIDER = process.env.DEFAULT_PROVIDER || 'openai';

app.use(cors());
app.use(express.json());

// =============================================================================
// MCP Client 实现
// =============================================================================
class MCPClient {
  constructor(serverUrl) {
    this.serverUrl = serverUrl;
    this.tools = [];
  }

  async listTools() {
    try {
      const response = await fetch(`${this.serverUrl}/mcp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          jsonrpc: '2.0',
          method: 'tools/list',
          id: 1
        })
      });
      const data = await response.json();
      if (data.result && data.result.tools) {
        this.tools = data.result.tools;
      }
      return this.tools;
    } catch (error) {
      console.error('listTools error:', error);
      return [];
    }
  }

  async callTool(toolName, arguments_) {
    try {
      const response = await fetch(`${this.serverUrl}/mcp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          jsonrpc: '2.0',
          method: 'tools/call',
          params: {
            name: toolName,
            arguments: arguments_
          },
          id: 2
        })
      });
      const data = await response.json();
      if (data.result && data.result.content) {
        return JSON.parse(data.result.content[0].text);
      }
      return data;
    } catch (error) {
      console.error('callTool error:', error);
      return { error: error.message };
    }
  }
}

// =============================================================================
// LLM 调用
// =============================================================================
async function callLLM(provider, messages, tools = null) {
  if (provider === 'openai' && OPENAI_API_KEY) {
    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${OPENAI_API_KEY}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: 'gpt-4o',
        messages,
        temperature: 0.7,
        tools: tools || undefined
      })
    });
    const result = await response.json();

    if (result.choices && result.choices[0]) {
      const choice = result.choices[0];
      if (choice.finish_reason === 'tool_calls') {
        return JSON.stringify(choice.message.tool_calls);
      }
      return choice.message.content;
    }
    return '';

  } else if (provider === 'anthropic' && ANTHROPIC_API_KEY) {
    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'x-api-key': ANTHROPIC_API_KEY,
        'Content-Type': 'application/json',
        'anthropic-version': '2023-06-01'
      },
      body: JSON.stringify({
        model: 'claude-sonnet-4-20250514',
        messages,
        max_tokens: 1024,
        tools: tools || undefined
      })
    });
    const result = await response.json();

    if (result.content && result.content.length > 0) {
      for (const content of result.content) {
        if (content.type === 'text') return content.text;
        if (content.type === 'tool_use') {
          return JSON.stringify([{ function: content.name, arguments: content.input }]);
        }
      }
    }
    return '';

  } else if (provider === 'minimax' && MINIMAX_API_KEY) {
    const response = await fetch('https://api.minimaxi.com/v1/text/chatcompletion_v2', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${MINIMAX_API_KEY}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: 'MiniMax-M2.7',
        messages,
        max_tokens: 1024,
        tools: tools || undefined
      })
    });
    const result = await response.json();
    console.log('[MiniMax Debug]', result);

    if (result.error) {
      return `MiniMax API Error: ${result.error.message || result.error}`;
    }

    if (result.choices && result.choices[0]) {
      const choice = result.choices[0];
      const message = choice.message || {};

      // Check for tool_calls first
      if (message.tool_calls && message.tool_calls.length > 0) {
        return JSON.stringify(message.tool_calls);
      }

      if (choice.delta && choice.delta.content) {
        return choice.delta.content;
      }
      if (message.content) {
        return message.content;
      }
    }
    return 'MiniMax returned empty response';

  }

  return '未配置 API Key，请设置 OPENAI_API_KEY 或 MINIMAX_API_KEY 环境变量';
}

function buildToolsForLLM(mcpTools) {
  return mcpTools.map(tool => ({
    type: 'function',
    function: {
      name: tool.name,
      description: tool.description || '',
      parameters: tool.inputSchema || { type: 'object', properties: {} }
    }
  }));
}

// =============================================================================
// AI Agent 实现
// =============================================================================
class AIAgent {
  constructor(mcpClient, provider = 'openai') {
    this.mcpClient = mcpClient;
    this.provider = provider;
    this.conversationHistory = [];
  }

  async chat(userMessage) {
    // 添加用户消息到历史
    this.conversationHistory.push({
      role: 'user',
      content: userMessage
    });

    // 发现可用工具
    const tools = await this.mcpClient.listTools();
    const llmTools = buildToolsForLLM(tools);

    // 调用 LLM
    const response = await callLLM(this.provider, this.conversationHistory, llmTools);

    // 检查是否需要调用工具
    if (response.startsWith('[') || (response.startsWith('{') && response.includes('function'))) {
      try {
        const toolCalls = JSON.parse(response);
        if (Array.isArray(toolCalls) && toolCalls.length > 0) {
          const toolCall = toolCalls[0];
          if (toolCall.function) {
            const toolName = toolCall.function.name;
            const arguments_ = typeof toolCall.function.arguments === 'string'
              ? JSON.parse(toolCall.function.arguments)
              : toolCall.function.arguments;

            // 调用 MCP 工具
            const toolResult = await this.mcpClient.callTool(toolName, arguments_);

            // 对于 MiniMax，直接返回工具结果，不再进行第二轮 LLM 调用
            // 因为 MiniMax 对 tool_call_id 有严格要求
            const responseText = `${toolName} 执行结果：\n${JSON.stringify(toolResult, null, 2)}`;

            this.conversationHistory.push({
              role: 'assistant',
              content: responseText
            });

            return {
              response: responseText,
              tool_used: toolName,
              tool_result: toolResult
            };
          }
        }
      } catch (e) {
        console.error('Parse tool calls error:', e);
      }
    }

    // 普通回复
    this.conversationHistory.push({
      role: 'assistant',
      content: response
    });

    return {
      response,
      tool_used: null,
      tool_result: null
    };
  }

  reset() {
    this.conversationHistory = [];
  }
}

// =============================================================================
// 初始化
// =============================================================================
const mcpClient = new MCPClient(MCP_SERVER_URL);
const agent = new AIAgent(mcpClient, DEFAULT_PROVIDER);

// =============================================================================
// API 端点
// =============================================================================
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'Node.js AI Agent',
    version: '1.0.0',
    port: AGENT_PORT,
    mcp_server: MCP_SERVER_URL,
    llm_provider: DEFAULT_PROVIDER,
    has_openai_key: Boolean(OPENAI_API_KEY),
    has_anthropic_key: Boolean(ANTHROPIC_API_KEY)
  });
});

app.post('/chat', async (req, res) => {
  try {
    const { message, provider } = req.body;
    if (!message) {
      return res.status(400).json({ error: 'message is required' });
    }

    if (provider) {
      agent.provider = provider;
    }

    const result = await agent.chat(message);
    res.json(result);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/reset', (req, res) => {
  agent.reset();
  res.json({ status: 'reset' });
});

app.get('/tools', async (req, res) => {
  const tools = await mcpClient.listTools();
  res.json({ tools });
});

// 演示页面
app.get('/', (req, res) => {
  res.sendFile('static/index.html', { root: './' });
});

app.listen(AGENT_PORT, () => {
  console.log(`
============================================================
Node.js AI Agent (MCP Client)
============================================================
Agent Port: ${AGENT_PORT}
MCP Server: ${MCP_SERVER_URL}
LLM Provider: ${DEFAULT_PROVIDER}

API Keys:
  OpenAI:    ${OPENAI_API_KEY ? '✓ 已配置' : '✗ 未配置'}
  Anthropic: ${ANTHROPIC_API_KEY ? '✓ 已配置' : '✗ 未配置'}

使用说明:
  1. 启动服务: npm run agent
  2. 打开页面: http://localhost:${AGENT_PORT}
  3. 健康检查: http://localhost:${AGENT_PORT}/health
  4. 聊天: POST http://localhost:${AGENT_PORT}/chat

API 端点:
  GET  /           - 演示页面
  GET  /health     - 健康检查
  POST /chat       - 发送消息
  POST /reset      - 重置对话
  GET  /tools      - 列出可用工具

============================================================
  `);
});