import os
import sys
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

base_url = os.getenv("PHONE_AGENT_BASE_URL")
api_key = os.getenv("PHONE_AGENT_API_KEY")
model = os.getenv("PHONE_AGENT_MODEL")

print(f"Testing Chat Completion:")
print(f"URL: {base_url}")
print(f"Model: {model}")
print("-" * 30)

client = OpenAI(base_url=base_url, api_key=api_key)

try:
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Hello, are you online?"}],
        max_tokens=50
    )
    print("\n✅ Success!")
    print(f"Response: {response.choices[0].message.content}")
except Exception as e:
    print(f"\n❌ Failed: {e}")

    # Fallback Test
    print("\nTrying fallback model 'gpt-4o'...")
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=50
        )
        print("✅ 'gpt-4o' works! The previous model might be invalid/restricted.")
    except Exception as e2:
        print(f"❌ 'gpt-4o' also failed: {e2}")
