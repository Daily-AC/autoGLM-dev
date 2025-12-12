# 开发者指南

本指南帮助开发者理解项目架构和贡献代码。

## 项目结构

```
Open-AutoGLM/
├── phone_agent/              # 核心库
│   ├── agent.py             # PhoneAgent, AsyncPhoneAgent
│   ├── exceptions.py        # 异常层次
│   ├── logging.py           # 结构化日志
│   ├── retry.py             # 重试和恢复机制
│   ├── actions/             # 动作处理
│   │   └── handler.py       # ActionHandler, AsyncActionHandler
│   ├── adb/                 # ADB 操作
│   │   ├── device.py        # 设备控制
│   │   ├── input.py         # 文本输入
│   │   └── screenshot.py    # 截图
│   ├── config/              # 配置管理
│   │   ├── settings.py      # 统一配置
│   │   └── prompts*.py      # 系统提示词
│   └── model/               # 模型客户端
│       └── client.py        # ModelClient, AsyncModelClient
├── web/                     # Web 控制台
│   ├── agent_runner.py      # Agent 运行器
│   └── templates/           # HTML 模板
├── tests/                   # 测试
│   ├── conftest.py          # Pytest 配置
│   └── unit/                # 单元测试
├── web_app.py               # FastAPI 应用
├── main.py                  # CLI 入口
├── config.example.yaml      # 配置示例
└── pytest.ini               # Pytest 配置
```

## 架构概览

```
┌─────────────────────────────────────────────────────────┐
│                     Web Console                          │
│                    (web_app.py)                          │
└───────────────────────┬─────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────┐
│                  AsyncPhoneAgent                         │
│                   (agent.py)                             │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌────────────────┐  ┌──────────────┐  │
│  │ AsyncModel  │  │ AsyncAction    │  │ Async ADB    │  │
│  │ Client      │  │ Handler        │  │ Functions    │  │
│  └─────────────┘  └────────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────┐
│                   Android Device                         │
│                   (via ADB)                              │
└─────────────────────────────────────────────────────────┘
```

## 开发环境设置

### 1. 克隆仓库

```bash
git clone https://github.com/xxx/Open-AutoGLM.git
cd Open-AutoGLM
```

### 2. 创建虚拟环境

```bash
python -m venv .venv
.\.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
pip install -e .
pip install pytest pytest-asyncio  # 测试依赖
```

### 4. 配置

```bash
cp config.example.yaml config.yaml
# 编辑 config.yaml 设置 API key 等
```

## 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试
pytest tests/unit/test_agent.py -v

# 查看覆盖率
pytest tests/ --cov=phone_agent
```

当前测试覆盖：

- ✅ 80 个单元测试
- ✅ Model Client
- ✅ Agent
- ✅ ActionHandler
- ✅ ADB Functions
- ✅ Retry / Recovery
- ✅ Settings

## 代码规范

### 异步 vs 同步

项目同时支持同步和异步 API：

```python
# 同步 (用于 CLI)
agent = PhoneAgent()
result = agent.run("...")

# 异步 (用于 Web)
agent = AsyncPhoneAgent()
result = await agent.run("...")
```

### 命名约定

- 异步函数前缀 `async_`：`async_tap()`, `async_get_screenshot()`
- 异步类前缀 `Async`：`AsyncPhoneAgent`, `AsyncActionHandler`

### 错误处理

使用项目定义的异常类：

```python
from phone_agent.exceptions import DeviceDisconnectedError

if not device_connected:
    raise DeviceDisconnectedError(
        "Device lost connection",
        device_id=device_id
    )
```

### 日志记录

使用结构化日志：

```python
from phone_agent.logging import get_logger

logger = get_logger("my_module")
logger.info("Operation completed", key="value", count=42)
```

## 贡献流程

1. **Fork** 仓库
2. **创建分支**: `git checkout -b feature/my-feature`
3. **编写代码**和**测试**
4. **运行测试**: `pytest tests/ -v`
5. **提交**: `git commit -m "feat: add my feature"`
6. **推送**: `git push origin feature/my-feature`
7. **创建 Pull Request**

### Commit 规范

使用 [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` 新功能
- `fix:` Bug 修复
- `docs:` 文档更新
- `test:` 测试
- `refactor:` 重构

## 常见问题

### Q: 如何添加新的 Action?

在 `phone_agent/actions/handler.py` 添加：

```python
# 在 ActionHandler 类中
def _handle_my_action(self, action: dict, w: int, h: int) -> ActionResult:
    # 实现逻辑
    return ActionResult(True, False)

# 在 _get_handler 中注册
handlers = {
    ...
    "MyAction": self._handle_my_action,
}
```

### Q: 如何添加新的配置项?

在 `phone_agent/config/settings.py` 修改对应的 Settings 类：

```python
@dataclass
class AgentSettings:
    my_new_option: str = "default"
```

然后在 `_load_from_env` 添加环境变量支持。

### Q: 如何调试 Agent?

```python
from phone_agent.config import settings

settings.agent.verbose = True
settings.log.level = "DEBUG"
```

或设置环境变量：

```bash
export AUTOGLM_VERBOSE=true
export AUTOGLM_LOG_LEVEL=DEBUG
```
