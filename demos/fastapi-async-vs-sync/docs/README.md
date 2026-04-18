# FastAPI 高并发原理对比教学 Demo

通过可视化压测，直观感受 async vs sync 的性能差异，理解高并发核心概念。

---

## 目录

1. [快速开始](#快速开始)
2. [核心概念：QPS 是什么？](#核心概念qps-是什么)
3. [技术原理](#技术原理)
4. [面试 3 大要点](#面试-3-大要点)
5. [常见误区](#常见误区)
6. [进阶：真实 AI Agent 高并发处理](#进阶真实-ai-agent-高并发处理)

---

## 快速开始

### 1. 启动服务

**Python FastAPI (端口 8091)**
```bash
cd demos/fastapi-async-vs-sync/server/python
python -m venv .venv
source .venv/bin/activate  # 或 .venv\Scripts\activate (Windows)
pip install -r requirements.txt
python main.py
```

**Node.js Express (端口 8090)**
```bash
cd demos/fastapi-async-vs-sync/server/node
npm install
node server.js
```

### 2. 打开 Demo 页面

- Python: http://localhost:8091
- Node.js: http://localhost:8090

### 3. 开始测试

1. 设置并发数量（默认 10，建议 10-50）
2. 点击 async-llm 和 sync-llm 测试按钮
3. 观察 QPS 对比和时间轴

---

## 核心概念：QPS 是什么？

### QPS = Queries Per Second（每秒查询率）

**公式：**
```
QPS = 总请求数 ÷ 总耗时（秒）
```

**示例：**
- 10 个请求，2 秒完成 → QPS = 10 ÷ 2 = **5 req/s**
- 10 个请求，20 秒完成 → QPS = 10 ÷ 20 = **0.5 req/s**

### 为什么 QPS 重要？

| QPS | 用户体验 |
|-----|----------|
| 高 | 10 个人同时访问，秒响应 |
| 低 | 10 个人同时访问，排队等待 |

**面试重点：** 高并发系统设计的核心目标之一就是提升 QPS。

### 本 Demo 的 QPS 对比

| 端点 | 10 并发耗时 | QPS |
|------|------------|-----|
| async-llm | ~2s | ~5 req/s |
| sync-llm | ~20s | ~0.5 req/s |

**差距：10 倍！**

---

## 技术原理

### 1. async def + await asyncio.sleep（推荐）

```python
async def query():
    await asyncio.sleep(2)  # 让出控制权
```

**原理：**
- `async def` 创建协程
- `await` 挂起函数，让出控制权给事件循环
- 事件循环调度其他任务

**10 并发效果：** 全部 ~2s 完成（并行执行）

```
请求1 ──▶ await ─┼──▶ 完成 (~2s)
请求2 ──▶ await ─┼──▶ 完成 (~2s)
请求3 ──▶ await ─┼──▶ 完成 (~2s)
```

### 2. def + time.sleep（灾难）

```python
def query():
    time.sleep(2)  # 阻塞线程
```

**原理：**
- 普通函数独占 worker
- 阻塞期间无法处理其他请求

**10 并发效果：** 10 × 2 = 20s（串行执行）

```
请求1 ──▶ sleep(2) ──▶ 完成 (2s)
请求2 ───────────▶ sleep(2) ──▶ 完成 (4s)
请求3 ───────────────────▶ sleep(2) ──▶ 完成 (6s)
...
请求10 ───────────────────────────────────▶ 完成 (20s)
```

### 3. async 中用 time.sleep（绝对禁止）

```python
async def bad_example():
    time.sleep(2)  # ❌ 灾难！
```

**后果：**
- `time.sleep` 是 C 级别阻塞
- 不释放 GIL，不让出事件循环
- **所有协程全部陪葬！**

**正确写法：**
```python
async def good_example():
    await asyncio.sleep(2)  # ✓ 挂起协程
```

### 4. Node.js 的 sync vs async

**同步（灾难）：**
```javascript
app.get('/sync', (req, res) => {
  while (Date.now() < start + 2000) {}  // 阻塞事件循环
});
```

**异步（推荐）：**
```javascript
app.get('/async', async (req, res) => {
  await new Promise(resolve => setTimeout(resolve, 2000));
});
```

---

## 面试 3 大要点（必背）

### 1. 事件循环 + 协程调度

**Python (asyncio)：**
- `async def` 创建协程
- `await` 让出控制权给事件循环
- 单线程即可高并发处理大量 IO 等待

**Node.js (事件循环)：**
- 单线程事件循环模型
- async/await 让出控制权
- 非阻塞 I/O 实现高并发

**核心结论：** 10 个并发请求同时打进来，`asyncio.sleep(2)` 并行执行，总耗时 ~2 秒。

### 2. sync def = 独占线程/进程

**问题：**
- 普通函数会独占 worker
- 10 个并发 = 串行等待
- uvicorn 默认单 worker，严重退化

**面试话术：**
> "同步函数在等待时会独占线程/进程，导致后续请求排队。在 FastAPI 中使用同步函数处理 IO 等待，会造成并发能力退化。"

### 3. 严禁在 async 中用 blocking I/O

**绝对禁止：**
- `time.sleep()` → 用 `await asyncio.sleep()`
- 同步文件 IO → 用 `aiofiles`
- 同步数据库驱动 → 用 `asyncpg`、`aiomysql`

**为什么？**
- 阻塞事件循环
- 所有协程陪葬
- 服务完全失去响应

---

## 常见误区

### ❌ 误区 1：async 函数会自动并行

**错误理解：**
```python
async def main():
    await func1()  # 等 func1 完成
    await func2()  # 再等 func2 完成
    # 这样是串行的！
```

**正确写法：**
```python
async def main():
    await asyncio.gather(
        func1(),  # 并行执行
        func2()   # 同时执行
    )
```

### ❌ 误区 2：async 一定比 sync 快

**错误：** 对于 CPU 密集型任务（计算、加密），async 无法加速。

**正确：** async 只对 I/O 密集型任务有效（网络请求、文件读写、数据库查询）。

### ❌ 误区 3：可以混用 sync 和 async

**错误：**
```python
async def bad():
    time.sleep(2)  # 阻塞事件循环

def also_bad():
    await something()  # 普通函数不能用 await
```

---

## 进阶：真实 AI Agent 高并发处理

### AI Agent 的特点

| 特点 | 说明 |
|------|------|
| I/O 密集 | 调用 LLM API（网络等待） |
| 长连接 | 流式响应（SSE/WebSocket） |
| 资源消耗大 | 每个请求占用内存高 |

---

### 方案一：多 Worker 模式

#### 什么是多 Worker？

```
单 Worker（单体）：
┌─────────────────────────┐
│      uvicorn 进程       │
│  ┌─────────────────┐   │
│  │   事件循环       │   │
│  │  请求1 请求2 ... │   │
│  └─────────────────┘   │
└─────────────────────────┘
问题：只有 1 个事件循环，CPU 只有一个核心被用
```

```
多 Worker（多进程）：
┌─────────────────────────────────────────────────┐
│                   操作系统                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ Worker 1 │  │ Worker 2 │  │ Worker 3 │      │
│  │ 事件循环  │  │ 事件循环  │  │ 事件循环  │      │
│  │ (CPU 核1) │  │ (CPU 核2) │  │ (CPU 核3) │      │
│  └──────────┘  └──────────┘  └──────────┘      │
│                                                 │
│         Nginx 负载均衡器（分配请求）              │
└─────────────────────────────────────────────────┘
优势：充分利用多核 CPU，并发能力翻倍
```

#### 代码示例

**Python (uvicorn)：**
```bash
# 单 worker（默认）
uvicorn main:app --host 0.0.0.0 --port 8000

# 多 worker（推荐 2-4 个，根据 CPU 核心数）
uvicorn main:app --workers 4 --limit-concurrency 100
```

**Node.js (Cluster)：**
```javascript
const cluster = require('cluster');
const numCPUs = require('os').cpus().length;

if (cluster.isMaster) {
  // 主进程不处理请求，只负责管理
  for (let i = 0; i < numCPUs; i++) {
    cluster.fork();  // 启动多个 Worker 进程
  }
} else {
  // 每个 Worker 都有自己的事件循环
  app.listen(3000);
}
```

#### 多 Worker 之间怎么通信？

**先记住：Worker 之间不直接通信！**

```
┌─────────────────────────────────────────────────┐
│  ❌ 错误理解                                      │
│  Worker 1 ←────→ Worker 2  ←────→ Worker 3     │
│  它们直接对话？不对！                              │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  ✅ 正确理解                                      │
│                                                 │
│  请求 ──▶ Nginx ──▶ Worker 1 (处理请求)          │
│                │                                 │
│                └──▶ 存/取 ◀──▶ Redis/数据库     │
│                         │                       │
│                ┌─────────┴─────────┐            │
│               Worker 1  Worker 2  Worker 3      │
│               (它们不互相通信，都和 Redis/DB 通信) │
└─────────────────────────────────────────────────┘
```

**类比：餐厅厨房**
- 前台接待员 = Nginx（接收订单、分配任务）
- 厨师 = Worker（各自做菜，互不干扰）
- 传菜员 = Redis/数据库（传递信息、共享数据）

**结论：多 Worker 不是"协作"，而是"独立处理 + 共享存储"**

---

### 方案二：限流 + 排队（保护后端）

#### 为什么需要限流？

```
没有限流：
1000 个请求 ──▶ 单机 ──▶ 崩溃（内存溢出）

有限流：
1000 个请求 ──▶ [限流 100/秒] ──▶ 100 ──▶ 单机（稳定）
                              └──▶ 900 排队中...
```

#### 代码示例

**Python（令牌桶限流）：**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/agent")
@limiter.limit("10/minute")  # 每用户每分钟 10 次
async def agent(request: Request):
    result = await call_llm(request)
    return result
```

**Node.js（并发限制）：**
```javascript
const pLimit = require('p-limit');
const limit = pLimit(10); // 最多 10 个并发处理

app.post('/agent', async (req, res) => {
  // 超过 10 个会排队，不会压垮服务
  const result = await limit(() => processAgent(req));
  res.json(result);
});
```

---

### 方案三：缓存（减少重复调用）

#### 缓存原理

```
请求 1: "什么是 AI？" ──▶ 检查缓存（未命中）──▶ 调用 LLM ──▶ 存入缓存 ──▶ 返回
请求 2: "什么是 AI？" ──▶ 检查缓存（命中!）──▶ 直接返回缓存结果 ──▶ 极速
```

#### AI Agent 缓存场景

| 缓存内容 | 效果 |
|----------|------|
| 相同问题的 LLM 回答 | 绕过 LLM 调用，直接返回 |
| 用户会话历史 | 多 Worker 共享对话上下文 |
| Token 用量计数 | 精确限流 |

#### 代码示例

```python
import hashlib, json, redis

cache = redis.from_url("redis://localhost")

@app.post("/agent")
async def agent(request: Request):
    # 用请求内容生成缓存 key
    key = "agent:" + hashlib.md5(json.dumps(request).encode()).hexdigest()

    # 命中缓存？直接返回
    if cached := await cache.get(key):
        return json.loads(cached)

    # 未命中，调用 LLM
    result = await llm.invoke(request)

    # 结果存入缓存（1 小时过期）
    await cache.setex(key, 3600, json.dumps(result))

    return result
```

---

### 方案四：水平扩展（分布式）

#### 从单机到多机

```
单机（遇到瓶颈）：
┌─────────────────┐
│   1 台服务器     │
│   uvicorn x 4   │
│   100 QPS       │
│   ❌ 再多就崩    │
└─────────────────┘

多机（水平扩展）：
┌──────────────┐
│    Nginx     │  负载均衡
│  (轮询分发)   │
└──────┬───────┘
       │
  ┌────┴────┬────────┐
  ▼         ▼        ▼
┌────┐   ┌────┐   ┌────┐
│ S1 │   │ S2 │   │ S3 │
│100 │   │100 │   │100 │
│QPS │   │QPS │   │QPS │
└────┘   └────┘   └────┘
  300 QPS 总容量 ✓
```

#### 分布式架构图

```
                          用户请求
                             │
                             ▼
                    ┌─────────────────┐
                    │   Nginx/Traefik │
                    │   (负载均衡)     │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
   ┌───────────┐       ┌───────────┐       ┌───────────┐
   │ Server 1  │       │ Server 2  │       │ Server 3  │
   │ :8001     │       │ :8002     │       │ :8003     │
   └─────┬─────┘       └─────┬─────┘       └─────┬─────┘
         │                   │                   │
         └───────────────────┼───────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  Redis / 数据库  │
                    │  (共享数据)      │
                    └─────────────────┘
```

---

### 方案五：异步任务队列（解耦）

#### 什么时候用队列？

| 场景 | 适用队列 |
|------|----------|
| LLM 生成很慢（10-30 秒）| ✓ 必须用（不能让用户干等）|
| 需要后处理（总结、翻译）| ✓ 队列解耦 |
| 简单查询（< 1 秒）| ✗ 不需要 |

#### 队列原理

```
同步（用户等待）：
请求 ──▶ FastAPI ──▶ 调用 LLM（等 10s）──▶ 返回
     用户在浏览器干等 10 秒 😫

异步（立即返回）：
请求 ──▶ FastAPI ──▶ 写入队列 ──▶ 立即返回 "task_123"
                              │
                              ▼
                    Celery Worker（后台）
                              │
                              ▼
                        调用 LLM（等 10s）
                              │
                              ▼
                        结果存入 Redis

用户轮询：
GET /task/task_123 ──▶ {"status": "done", "result": "..."}
```

#### 代码示例

```python
from celery import Celery

celery = Celery('tasks', broker='redis://localhost')

@celery.task
def agent_task(user_input: str):
    """后台执行的异步任务"""
    result = call_llm(user_input)
    return result

@app.post("/agent")
async def agent(user_input: str):
    # 立即返回，不阻塞
    task = agent_task.delay(user_input)
    return {"task_id": task.id, "status": "processing"}

@app.get("/task/{task_id}")
async def get_result(task_id: str):
    result = celery.AsyncResult(task_id)
    if result.ready():
        return {"status": "done", "result": result.get()}
    return {"status": "processing"}
```

---

### 分布式数据同步：核心挑战

#### 问题：多 Server 之间的数据共享

```
单体（无问题）：
请求 A ──▶ Server 1 ──▶ [内存: session_A]

多机（有问题）：
请求 A ──▶ Server 1 ──▶ [内存: session_A]  ✓ OK
请求 B ──▶ Server 2 ──▶ [内存: ____]      ❌ 没有 session_A
```

#### AI Agent 常见的数据同步问题

| 数据类型 | 问题 | 解决方案 |
|----------|------|----------|
| 用户对话历史 | 多 Server 不共享 | 存 Redis |
| API Key 限流计数 | 独立计数不准确 | Redis 集中计数 |
| LLM rate limit | 多 Server 各自计数超限 | Redis 分布式锁 |

#### 无状态设计：最佳实践

**原则：每个请求携带所有必要信息，不要依赖服务器内存**

```
❌ 有状态（出问题）：
请求 ──▶ Server 1（内存有 user_123 的 token）───▶ OK
请求 ──▶ Server 2（内存没有 user_123 的 token）───▶ ❌ 失败

✅ 无状态（推荐）：
请求 + token ──▶ 任何 Server 都能处理
              │
              └──▶ 从 Redis 读取用户信息
```

#### 会话历史怎么同步？

```python
# ❌ 错误：存在进程内存里
class Agent:
    def __init__(self):
        self.conversations = {}  # 每个 Worker 独立

# ✅ 正确：存在 Redis 里
class Agent:
    def __init__(self):
        self.redis = redis.from_url("redis://localhost")

    async def chat(self, user_id, message):
        # 从 Redis 读取历史
        history = await self.redis.lrange(f"chat:{user_id}", 0, -1)

        # 添加新消息
        history.append({"role": "user", "content": message})

        # 存回 Redis
        await self.redis.rpush(f"chat:{user_id}", history)

        # 调用 LLM
        result = await llm.invoke(history)

        return result
```

---

### 架构选型建议

| 规模 | QPS | 架构 | 说明 |
|------|-----|------|------|
| 小型 | < 100 | 单机 + 多 Worker + Redis 缓存 | 简单成本低 |
| 中型 | 100-1000 | 多机 + 限流 + 队列 | 水平扩展 |
| 大型 | > 1000 | K8s + 微服务 + 消息队列 | 完整分布式 |

### Demo 场景对应真实场景

| Demo 场景 | 真实 AI Agent | 瓶颈 |
|-----------|---------------|------|
| `async-llm` | async 调用 LLM API | 事件循环不阻塞，可高并发 |
| `sync-llm` | sync 调用 LLM（同步库）| **独占 worker，吞吐低** |

### 核心原则

> AI Agent 一定要用 `async/await`，配合 Redis 缓存 + 限流 + 多 Worker，基本能支撑到 500-1000 QPS。
>
> **初期不要过度设计**：先做单机无状态，把状态全放 Redis，等 QPS 真上去了再拆分。

---

## 面试相关问题

### Q1: "多 Worker 之间怎么通信？"

**答：** 多 Worker 之间不直接通信。每个 Worker 是独立进程，有独立内存空间。它们通过外部存储（Redis、数据库）共享数据。请求分发由 Nginx/负载均衡器负责。

### Q2: "分布式系统怎么保证数据一致性？"

**答：** 这是分布式系统最大的挑战。常见方案：
- **共享存储**：所有 Worker 连接同一个 Redis/数据库
- **无状态设计**：每个请求携带所有必要信息
- **分布式锁**：用 Redis/ZooKeeper 协调竞争资源

### Q3: "FastAPI 和 Flask 在并发模型上的区别？"

**答：**
- Flask: 同步，每个请求独占线程
- FastAPI: 异步，基于 Starlette/uvicorn，支持 async/await

### Q4: "什么时候用 sync def，什么时候用 async def？"

**答：**
- sync: CPU 密集型、无 I/O 等待
- async: I/O 密集型、网络请求、数据库查询

### Q5: "uvicorn 单 Worker 和多 Worker 区别？"

**答：**
- 单 Worker: 共享事件循环，适合 I/O 密集
- 多 Worker: 独立进程，充分利用多核 CPU，适合高并发

---

## 文件结构

```
demos/fastapi-async-vs-sync/
├── demo.html                 # 旧版（已废弃）
├── server/
│   ├── python/
│   │   ├── main.py          # FastAPI 服务（端口 8091）
│   │   ├── static/index.html # Python 版 Demo 页面
│   │   └── requirements.txt
│   └── node/
│       ├── server.js        # Express 服务（端口 8090）
│       ├── static/index.html # Node.js 版 Demo 页面
│       └── package.json
└── docs/
    └── README.md            # 本文档
```
