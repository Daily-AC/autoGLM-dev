
import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
import torch
from transformers import AutoModelForCausalLM, AutoModel, AutoTokenizer

model_id = "zai-org/AutoGLM-Phone-9B"

print("Debugging model loading...")

try:
    print("\n--- Attempting AutoModelForCausalLM ---")
    model = AutoModelForCausalLM.from_pretrained(
        model_id, 
        trust_remote_code=True, 
        device_map="auto",
        torch_dtype=torch.float16
    )
    print(f"Success! Class: {type(model).__name__}")
    print(f"Has generate? {hasattr(model, 'generate')}")
except Exception as e:
    print(f"Failed: {e}")

try:
    print("\n--- Attempting AutoModel (Base) ---")
    model = AutoModel.from_pretrained(
        model_id, 
        trust_remote_code=True, 
        device_map="auto", 
        torch_dtype=torch.float16
    )
    print(f"Success! Class: {type(model).__name__}")
    print(f"Has generate? {hasattr(model, 'generate')}")
except Exception as e:
    print(f"Failed: {e}")
