# Open-AutoGLM-Dev-System

<div align="center">
<img src="resources/logo.svg" width="20%"/>
</div>

<p align="center">
  <a href="README.md">中文</a> | 
  <a href="README_en.md">English</a> |
  <a href="docs/API.md">API 文档</a> |
  <a href="docs/DEVELOPMENT.md">开发指南</a>
</p>

> 🤖 **Phone Agent** - 基于 AutoGLM 的手机端智能助理框架
>
> 本项目基于 [Open-AutoGLM](https://github.com/zai-org/Open-AutoGLM) 进行二次开发。

Phone Agent 能够以多模态方式理解手机屏幕内容，并通过自动化操作帮助用户完成任务。只需用自然语言描述需求，如"打开小红书搜索美食"，即可自动完成整个流程。

## ✨ 特性

- 🧠 **多模态理解** - 视觉语言模型理解屏幕内容
- 🎯 **自然语言控制** - 用自然语言描述任务
- ⚡ **异步架构** - 完整的 async/await 支持
- 🔄 **自动恢复** - API 重试、ADB 自动重连
- 🛡️ **安全机制** - 敏感操作确认、人工接管
- 🌐 **Web 控制台** - 实时查看执行状态
- 📱 **远程调试** - WiFi 连接设备

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
pip install -e .
```

### 2. 配置

```bash
cp config.example.yaml config.yaml
# 编辑 config.yaml 设置 API key
```

或使用环境变量：

```bash
export AUTOGLM_API_KEY="your-api-key"
export AUTOGLM_MODEL="gpt-4o"
```

### 3. 连接设备

```bash
adb devices  # 确认设备已连接
```

### 4. 启动

**Web 控制台**（推荐）：

```bash
python web_app.py
# 访问 http://localhost:8000
```

**命令行**：

```bash
python main.py
```

## 📁 项目结构

```
Open-AutoGLM/
├── phone_agent/          # 核心库
│   ├── agent.py         # PhoneAgent, AsyncPhoneAgent
│   ├── actions/         # 动作处理
│   ├── adb/             # ADB 操作
│   ├── config/          # 配置管理
│   └── model/           # 模型客户端
├── web/                  # Web 控制台
├── tests/                # 单元测试 (80+ tests)
├── scripts/              # 工具脚本
├── docs/                 # 文档
│   ├── API.md           # API 参考
│   └── DEVELOPMENT.md   # 开发指南
├── examples/             # 示例代码
├── web_app.py           # FastAPI 应用
├── main.py              # CLI 入口
└── config.example.yaml  # 配置示例
```

## 📖 使用示例

### Python API

```python
from phone_agent import AsyncPhoneAgent
from phone_agent.model import ModelConfig
import asyncio

async def main():
    agent = AsyncPhoneAgent(ModelConfig(
        api_key="your-key",
        model_name="gpt-4o"
    ))

    result = await agent.run("打开微信发送消息")
    print(result)

asyncio.run(main())
```

### 配置管理

```python
from phone_agent.config import settings

# 访问配置
print(settings.model.api_key)
print(settings.web.port)

# 修改配置
settings.agent.verbose = True
```

## 🧪 运行测试

```bash
pytest tests/ -v
```

## 📚 文档

- [API 参考](docs/API.md) - 完整的 API 文档
- [开发指南](docs/DEVELOPMENT.md) - 贡献代码指南
- [更新日志](CHANGELOG.md) - 版本更新记录

## 🔧 环境变量

| 变量               | 说明     | 默认值                    |
| ------------------ | -------- | ------------------------- |
| `AUTOGLM_API_KEY`  | API 密钥 | -                         |
| `AUTOGLM_BASE_URL` | API 地址 | https://api.openai.com/v1 |
| `AUTOGLM_MODEL`    | 模型名称 | gpt-4o                    |
| `AUTOGLM_PORT`     | Web 端口 | 8000                      |
| `AUTOGLM_DEBUG`    | 调试模式 | false                     |

## 📋 环境要求

- Python 3.10+
- Android 7.0+ 设备
- ADB (Android Debug Bridge)
- [ADB Keyboard](https://github.com/senzhk/ADBKeyBoard) (文本输入)

## ⚠️ 免责声明

本项目仅供研究和学习使用。严禁用于非法获取信息、干扰系统或任何违法活动。

## 📄 License

Apache License 2.0
