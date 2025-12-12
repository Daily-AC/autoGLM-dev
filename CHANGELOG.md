# Changelog

本文件记录项目的所有重要变更。

## [Unreleased]

### ✨ 新增

- **异步架构**: 完整的异步支持

  - `AsyncPhoneAgent` - 异步 Agent
  - `AsyncModelClient` - 异步模型客户端
  - `AsyncActionHandler` - 异步动作处理器
  - 异步 ADB 函数: `async_tap`, `async_swipe`, `async_get_screenshot` 等

- **错误恢复机制**

  - `retry_async` / `retry_sync` - 重试装饰器，支持指数退避
  - `with_retry` - 单次调用重试工具
  - `ADBConnectionManager` - ADB 自动重连管理
  - `CircuitBreaker` - API 熔断保护
  - `AsyncCancellationToken` - 异步取消令牌

- **配置管理系统**

  - 统一 `Settings` 配置类
  - 环境变量支持 (`AUTOGLM_*`)
  - YAML 配置文件支持
  - 程序化配置覆盖

- **UX 增强**

  - 详细错误信息显示
  - 任务成功/失败状态区分
  - 失败后"继续任务"按钮
  - `/api/chat/continue` API 端点

- **测试覆盖**

  - 80+ 单元测试
  - 覆盖所有核心模块

- **文档**
  - API 参考文档 (`docs/API.md`)
  - 开发者指南 (`docs/DEVELOPMENT.md`)
  - 配置示例 (`config.example.yaml`)

### 🔧 改进

- Web 应用改用 `asyncio.create_task` 替代 `BackgroundTasks`
- 模型响应解析错误信息更详细
- 日志系统添加 `failed()` 方法

### 📁 新增文件

- `phone_agent/retry.py` - 重试机制
- `phone_agent/config/settings.py` - 配置管理
- `tests/` - 测试目录
- `pytest.ini` - Pytest 配置
- `config.example.yaml` - 配置示例
- `docs/API.md` - API 文档
- `docs/DEVELOPMENT.md` - 开发者指南

---

## [0.1.0] - Initial Release

- 基础 PhoneAgent 功能
- ADB 设备控制
- 模型集成
- Web 控制台
