import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

base_url = os.getenv("PHONE_AGENT_BASE_URL")
api_key = os.getenv("PHONE_AGENT_API_KEY")

print(f"Connecting to {base_url}...")
client = OpenAI(base_url=base_url, api_key=api_key)

try:
    models = client.models.list()
    print("\nAvailable Models:")
    found_claude = False
    for m in models:
        print(f" - {m.id}")
        if "claude" in m.id.lower():
            found_claude = True
            
    if not found_claude:
        print("\n(No models with 'claude' in name found)")
        
except Exception as e:
    print(f"\nError listing models: {e}")
