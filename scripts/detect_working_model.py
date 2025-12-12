import os
import sys
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

base_url = os.getenv("PHONE_AGENT_BASE_URL")
api_key = os.getenv("PHONE_AGENT_API_KEY")

candidates = [
    "gpt-4o",
    "gpt-4o-mini",
    "claude-3-5-sonnet-20241022",
    "claude-3-5-sonnet-latest",
    "claude-3-5-sonnet-20240620",
    "claude-opus-4-5-20251101", 
    "gpt-5-codex",
    "gemini-2.5-pro",
    "claude-3-opus-20240229"
]

print(f"Testing Base URL: {base_url}")
client = OpenAI(base_url=base_url, api_key=api_key, timeout=5.0)

working_model = None

for model in candidates:
    print(f"Testing '{model}'...", end=" ", flush=True)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5
        )
        print("✅ SUCCESS!")
        working_model = model
        break
    except Exception as e:
        err = str(e)
        if "404" in err:
            print("❌ Not Found (404)")
        elif "401" in err:
            print("❌ Auth Error (401)")
            break
        else:
            print(f"❌ Error: {err[:50]}...")

if working_model:
    print(f"\n💪 FOUND WORKING MODEL: {working_model}")
    # Write to a file so we can read it reliably
    with open("working_model.txt", "w") as f:
        f.write(working_model)
else:
    print("\n😭 NO WORKING MODELS FOUND.")
