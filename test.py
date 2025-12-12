from phone_agent import PhoneAgent
from phone_agent.model import ModelConfig

# 配置模型
model_config = ModelConfig(
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    api_key="sk-2aa187bb5fc44808b76f0971c8c51684",
    model_name="qwen-vl-plus",
)

# 创建 Agent
agent = PhoneAgent(model_config=model_config)

# 执行任务
result = agent.run("打开淘宝搜索无线耳机")
print(result)