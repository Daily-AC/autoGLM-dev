import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("PHONE_AGENT_API_KEY")
# User mentioned ANTHROPIC_BASE_URL=https://anyrouter.top
# Standard Anthropic endpoint is /v1/messages
base_url = "https://anyrouter.top/v1/messages"

# Model user wants
model = "claude-opus-4-5-20251101"

headers = {
    "x-api-key": api_key,
    "anthropic-version": "2023-06-01",
    "content-type": "application/json"
}

data = {
    "model": model,
    "max_tokens": 1024,
    "messages": [
        {"role": "user", "content": "Hello, are you Claude Opus 4.5?"}
    ]
}

print(f"Testing Anthropic Native Protocol:")
print(f"URL: {base_url}")
print(f"Model: {model}")
print("-" * 30)

try:
    response = requests.post(base_url, headers=headers, json=data, timeout=10)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ Success!")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    else:
        print("❌ Failed")
        print(response.text)

except Exception as e:
    print(f"❌ Error: {e}")
