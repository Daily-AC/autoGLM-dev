# Phone Agent API 参考

本文档介绍 Phone Agent 的核心 API 和使用方法。

## 目录

- [快速开始](#快速开始)
- [核心类](#核心类)
- [配置管理](#配置管理)
- [ADB 操作](#adb-操作)
- [错误处理](#错误处理)
- [重试机制](#重试机制)

---

## 快速开始

### 安装

```bash
pip install -r requirements.txt
pip install -e .
```

### 基本使用

```python
from phone_agent import AsyncPhoneAgent
from phone_agent.model import ModelConfig
import asyncio

async def main():
    # 配置模型
    config = ModelConfig(
        base_url="https://api.openai.com/v1",
        api_key="your-api-key",
        model_name="gpt-4o"
    )

    # 创建 Agent
    agent = AsyncPhoneAgent(config)

    # 执行任务
    result = await agent.run("打开微信")
    print(result)

asyncio.run(main())
```

---

## 核心类

### AsyncPhoneAgent

异步手机自动化 Agent，用于 Web 应用。

```python
from phone_agent import AsyncPhoneAgent

agent = AsyncPhoneAgent(
    model_config=ModelConfig(...),  # 模型配置
    agent_config=AgentConfig(...),  # Agent 配置
)

# 单步执行
result = await agent.step("打开设置")

# 完整运行
await agent.run("搜索附近的餐厅")

# 取消任务
agent.cancel()

# 重置状态
agent.reset()
```

**属性：**

- `step_count` - 当前步数
- `context` - 对话上下文

### PhoneAgent

同步版本，用于 CLI 和脚本。

```python
from phone_agent import PhoneAgent

agent = PhoneAgent()
result = agent.run("打开微信")
```

### CancellationToken

任务取消令牌。

```python
from phone_agent import CancellationToken, AsyncCancellationToken

# 同步版本
token = CancellationToken()
token.cancel()
print(token.is_cancelled)  # True

# 异步版本
async_token = AsyncCancellationToken()
await async_token.check()  # 如果已取消，抛出 CancelledError
```

---

## 配置管理

### Settings

统一配置管理，支持多种配置源。

```python
from phone_agent.config import settings, configure

# 访问配置
print(settings.model.api_key)
print(settings.web.port)

# 修改配置
settings.model.max_tokens = 8192
settings.web.debug = True

# 使用 configure()
configure(model_max_tokens=8192, web_debug=True)

# 重新加载
settings.reload()

# 导出为字典
config_dict = settings.to_dict()
```

### 环境变量

配置可通过环境变量覆盖，前缀为 `AUTOGLM_`：

| 变量                | 说明     | 默认值                    |
| ------------------- | -------- | ------------------------- |
| `AUTOGLM_API_KEY`   | API 密钥 | -                         |
| `AUTOGLM_BASE_URL`  | API 地址 | https://api.openai.com/v1 |
| `AUTOGLM_MODEL`     | 模型名称 | gpt-4o                    |
| `AUTOGLM_DEVICE_ID` | 设备 ID  | 自动检测                  |
| `AUTOGLM_PORT`      | Web 端口 | 8000                      |
| `AUTOGLM_DEBUG`     | 调试模式 | false                     |

### YAML 配置

创建 `config.yaml`：

```yaml
model:
  model_name: "gpt-4o"
  max_tokens: 4096

device:
  id: "192.168.1.100:5555"

web:
  port: 8000
  debug: false
```

---

## ADB 操作

### 同步函数

```python
from phone_agent.adb import tap, swipe, back, home, type_text

# 点击
tap(540, 1200, device_id="xxx")

# 滑动
swipe(500, 1500, 500, 500)

# 返回/主页
back()
home()

# 输入文本
type_text("Hello World")
```

### 异步函数

```python
from phone_agent.adb import (
    async_tap,
    async_swipe,
    async_back,
    async_type_text,
    async_get_screenshot
)

await async_tap(540, 1200)
await async_swipe(500, 1500, 500, 500)
await async_type_text("Hello World")

# 截图
screenshot = await async_get_screenshot()
print(screenshot.width, screenshot.height)
```

---

## 错误处理

### 异常层次

```
AutoGLMError
├── DeviceError
│   ├── DeviceNotFoundError
│   ├── DeviceDisconnectedError (retryable)
│   └── ScreenshotError (retryable)
├── ModelError
│   ├── ModelConnectionError (retryable)
│   ├── ModelRateLimitError (retryable)
│   ├── ModelTimeoutError (retryable)
│   └── ModelInvalidResponseError (retryable)
├── ActionError
│   ├── ActionParseError
│   └── ActionExecutionError (retryable)
└── TaskCancelledError
```

### 使用示例

```python
from phone_agent import (
    AutoGLMError,
    DeviceDisconnectedError,
    ModelRateLimitError,
    is_retryable
)

try:
    await agent.step("打开微信")
except DeviceDisconnectedError as e:
    print(f"设备断开: {e.user_message}")
except ModelRateLimitError as e:
    print(f"限流，等待 {e.retry_after}s 后重试")
except AutoGLMError as e:
    if is_retryable(e):
        print("可重试的错误")
```

---

## 重试机制

### retry_async 装饰器

```python
from phone_agent import retry_async

@retry_async(max_attempts=3, base_delay=1.0)
async def api_call():
    return await client.request(...)
```

### with_retry 函数

```python
from phone_agent import with_retry

result = await with_retry(
    async_tap, 100, 200,
    max_attempts=3
)
```

### CircuitBreaker

```python
from phone_agent import CircuitBreaker

api_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=30.0
)

@api_breaker
async def protected_api():
    ...
```

### ADBConnectionManager

```python
from phone_agent import ADBConnectionManager

manager = ADBConnectionManager(device_id="xxx")

async with manager.ensure_connected():
    await async_tap(100, 200)
```

---

## ActionHandler

### AsyncActionHandler

```python
from phone_agent.actions import AsyncActionHandler

handler = AsyncActionHandler(device_id="xxx")

action = {
    "_metadata": "do",
    "action": "Tap",
    "element": [500, 300]
}

result = await handler.execute(action, screen_width=1080, screen_height=2400)
print(result.success, result.message)
```

### 支持的 Actions

| Action       | 参数            | 说明     |
| ------------ | --------------- | -------- |
| `Tap`        | element: [x, y] | 点击     |
| `Swipe`      | start, end      | 滑动     |
| `Type`       | text            | 输入文本 |
| `Back`       | -               | 返回     |
| `Home`       | -               | 主页     |
| `Wait`       | duration        | 等待     |
| `Launch`     | app             | 启动应用 |
| `Long Press` | element         | 长按     |
| `Double Tap` | element         | 双击     |

---

## 日志

```python
from phone_agent import get_logger

logger = get_logger("my_module")

logger.info("信息")
logger.warn("警告")
logger.error("错误")
logger.debug("调试")

# Agent 专用方法
logger.thought("思考中...")
logger.action("Tap", {"element": [100, 200]})
logger.result("完成")
logger.failed("失败原因")
```
