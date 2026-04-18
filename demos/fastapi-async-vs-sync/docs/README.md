# FastAPI 高并发原理对比教学 Demo

通过可视化压测，直观感受 async vs sync 的性能差异，理解高并发核心概念。

---

## 目录

1. [快速开始](#快速开始)
2. [核心概念：QPS 是什么？](#核心概念qps-是什么)
3. [技术原理](#技术原理)
4. [面试 3 大要点](#面试-3-大要点)
5. [常见误区](#常见误区)

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

## 扩展学习

### 相关面试题

1. **"FastAPI 和 Flask 在并发模型上的区别？"**
   - Flask: 同步，每个请求独占线程
   - FastAPI: 异步，基于 Starlette/uvicorn

2. **"什么时候用 sync def，什么时候用 async def？"**
   - sync: CPU 密集型、无 IO 等待
   - async: I/O 密集型、网络请求、数据库查询

3. **"uvicorn 单 worker 和多 worker 区别？"**
   - 单 worker: 共享事件循环，适合 I/O 密集
   - 多 worker: 独立进程，适合 CPU 密集（但通信开销大）

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
