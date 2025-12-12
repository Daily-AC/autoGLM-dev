import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(base_url=os.getenv("PHONE_AGENT_BASE_URL"), api_key=os.getenv("PHONE_AGENT_API_KEY"))

try:
    print("--- START MODEL LIST ---")
    for m in client.models.list():
        # Only print 'gpt' or 'claude' to filter noise and keep output short
        if 'gpt' in m.id or 'claude' in m.id:
            print(m.id)
    print("--- END MODEL LIST ---")
except Exception as e:
    print(e)
