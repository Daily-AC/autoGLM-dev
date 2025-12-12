# Open-AutoGLM 架构设计笔记

> 记录项目重构过程中的设计模式和最佳实践

---

## 1. 结构化日志系统

### 设计动机

传统 `print()` 调试的问题：

- ❌ 无级别区分（不知道是调试还是错误）
- ❌ 无时间戳（无法追踪时序）
- ❌ 无模块来源（不知道哪个组件输出的）
- ❌ 字符串格式（无法程序化解析）

### 解决方案：JSON 结构化日志

```python
# 日志条目结构
{
    "ts": 1702371600.123,        # Unix 时间戳
    "module": "agent",           # 模块名
    "level": "INFO",             # 级别: DEBUG/INFO/WARN/ERROR/AGENT
    "msg": "执行点击操作",        # 消息
    "tag": "ACTION",             # 可选：语义标签
    "details": {...}             # 可选：额外数据
}
```

### 核心类设计

```python
class StructuredLogger:
    """
    结构化日志器

    特点：
    1. 多级别支持 (DEBUG → ERROR)
    2. JSON 格式输出
    3. 双通道：终端 + Web 队列
    4. Agent 专用标签 (THOUGHT/ACTION/RESULT)
    """

    def __init__(self, module: str, queue=None):
        self.module = module  # 模块标识
        self.queue = queue    # Web 前端队列
```

### 使用模式

```python
# 创建模块级日志器
logger = StructuredLogger("agent")

# 普通日志
logger.info("任务开始", task="打开微信")
logger.debug("截图完成", width=1080, height=2400)
logger.error("模型调用失败", error=str(e))

# Agent 专用（带语义标签）
logger.thought("分析屏幕，发现搜索框在右上角")
logger.action("Tap", {"element": [800, 100]})
logger.result("任务完成")
```

---

## 2. 异常层级系统

### 设计动机

异常处理的问题：

- ❌ 所有错误都用 `Exception`，无法区分类型
- ❌ 不知道哪些错误可以重试
- ❌ 错误信息缺乏上下文
- ❌ 难以实现针对性的恢复策略

### 解决方案：分层异常

```
AutoGLMError (基类)
├── DeviceError (设备相关)
│   ├── DeviceNotFoundError     # 不可恢复
│   └── DeviceDisconnectedError # 可重连
│
├── ModelError (模型相关)
│   ├── ModelRateLimitError     # 可指数退避
│   ├── ModelInvalidResponseError # 可重试
│   └── ModelAuthenticationError # 不可恢复
│
├── ActionError (动作相关)
│   ├── ActionParseError        # 解析失败
│   └── ActionExecutionError    # 执行失败
│
└── TaskCancelledError          # 用户取消
```

### 异常设计原则

```python
class AutoGLMError(Exception):
    """
    异常基类设计原则：

    1. retryable 属性：标识是否可重试
    2. 上下文信息：携带调试所需数据
    3. 用户友好消息：可直接展示给用户
    """
    retryable: bool = False
    user_message: str = "操作失败"

    def __init__(self, message: str, **context):
        super().__init__(message)
        self.context = context  # 携带上下文
```

### 使用模式

```python
# 抛出异常时携带上下文
raise ModelRateLimitError(
    "API 限流",
    retry_after=30,
    model="gpt-4o"
)

# 捕获并处理
try:
    response = model_client.request(context)
except ModelRateLimitError as e:
    # 指数退避
    await asyncio.sleep(e.context.get("retry_after", 1))
    return await self.retry()
except ModelError as e:
    # 其他模型错误
    logger.error("模型错误", error=str(e))
    raise
```

---

## 3. 前端日志解析

### 旧方式（字符串匹配）

```javascript
// 脆弱，依赖特定格式
if (line.includes("[THOUGHT]")) {
  const text = line.split("[THOUGHT]")[1].trim();
  addBubble("thought", text);
}
```

### 新方式（JSON 解析）

```javascript
function processLogEntry(line) {
  // 尝试 JSON 解析
  let entry;
  try {
    entry = JSON.parse(line);
  } catch {
    // 降级：普通文本日志
    appendLogToTerminal(line);
    return;
  }

  // 根据标签处理
  switch (entry.tag) {
    case "THOUGHT":
      addBubble("thought", entry.msg);
      break;
    case "ACTION":
      addBubble("tool", `${entry.msg}: ${JSON.stringify(entry.details)}`);
      break;
    case "RESULT":
      addBubble("ai", entry.msg);
      setLoading(false);
      break;
  }

  // 根据级别处理
  if (entry.level === "ERROR") {
    setLoading(false);
    setNodeFailed(lastActiveNodeId);
  }
}
```

---

## 4. CancellationToken 模式

### 设计动机

同步阻塞任务无法真正取消的问题：

- 线程无法从外部强制终止
- `time.sleep()` 等阻塞调用无法中断
- 需要主动检查取消请求

### 解决方案：取消令牌

```python
class CancellationToken:
    """
    线程安全的取消令牌

    核心思想：
    1. 使用 threading.Event 实现线程安全
    2. 在关键检查点主动检查取消状态
    3. 抛出异常终止执行流
    """

    def __init__(self):
        self._cancelled = threading.Event()

    def cancel(self):
        """请求取消（主线程调用）"""
        self._cancelled.set()

    @property
    def is_cancelled(self) -> bool:
        """检查是否已取消（工作线程调用）"""
        return self._cancelled.is_set()

    def raise_if_cancelled(self):
        """如果已取消则抛出异常"""
        if self.is_cancelled:
            raise TaskCancelledException()
```

### 检查点位置

```python
def _execute_step(self):
    # 检查点 1：步骤开始前
    self._token.raise_if_cancelled()

    screenshot = get_screenshot()  # 可能耗时

    # 检查点 2：模型调用前（避免浪费 Token）
    self._token.raise_if_cancelled()

    response = model.request(context)  # 耗时且花钱

    # 检查点 3：动作执行前
    self._token.raise_if_cancelled()

    action_handler.execute(action)  # 可能影响设备
```

---

## 5. 代码模块化最佳实践

### 单文件过大的问题

`web_app.py` 645 行的问题：

- 职责混杂（路由、状态、流处理、Agent 管理）
- 难以测试单个功能
- 修改一处可能影响其他

### 拆分原则

| 原则         | 说明                         |
| ------------ | ---------------------------- |
| **单一职责** | 每个模块只做一件事           |
| **依赖注入** | 通过参数传递依赖，不要硬编码 |
| **接口分离** | 暴露最小必要接口             |

### 模块结构示例

```
web/
├── __init__.py      # 包导出
├── state.py         # 状态管理（AppState, QueueLogger）
├── models.py        # 数据模型（Pydantic）
├── profiles.py      # Profile 管理
├── screen.py        # 屏幕流处理
├── agent_runner.py  # Agent 任务执行
└── services.py      # 后台服务

web_app.py           # 纯路由定义，极简
```

---

## 6. 上下文裁剪 (Context Trimming)

### 设计动机

Agent 对话上下文无限增长的问题：

- 每步添加 user message + assistant message
- 图片 (base64) 约 100-500KB 每张
- 10 步任务可能累积数 MB 上下文
- 导致 Token 消耗大、API 成本高、可能超限

### 解决方案：两层裁剪

```python
@dataclass
class AgentConfig:
    max_context_messages: int = 10  # 保留最近 N 条
    remove_old_images: bool = True  # 移除旧消息中的图片
```

**策略 1**: 移除旧图片（保留最新截图）

```python
for msg in self._context[1:-2]:  # 跳过 system 和最新消息
    MessageBuilder.remove_images_from_message(msg)
```

**策略 2**: 限制消息数量

```python
if len(self._context) > max_msgs + 1:
    self._context = [self._context[0]] + self._context[-(max_msgs):]
```

### 效果估算

| 场景      | 无裁剪 | 有裁剪 | 节省 |
| --------- | ------ | ------ | ---- |
| 10 步任务 | ~2MB   | ~200KB | 90%  |
| 20 步任务 | ~4MB   | ~200KB | 95%  |

---

## 更新记录

| 日期       | 内容                                     |
| ---------- | ---------------------------------------- |
| 2024-12-12 | 初始版本：结构化日志、异常层级、取消令牌 |
