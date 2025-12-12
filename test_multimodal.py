
import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
import torch
import sys

print("Python executable:", sys.executable)
try:
    import transformers
    print("Transformers version:", transformers.__version__)
    from transformers import AutoModelForMultimodalLM
    print("AutoModelForMultimodalLM imported successfully.")
except ImportError as e:
    print("Import Failed:", e)
    sys.exit(1)

model_id = "zai-org/AutoGLM-Phone-9B"

try:
    print(f"Loading {model_id} with AutoModelForMultimodalLM...")
    model = AutoModelForMultimodalLM.from_pretrained(
        model_id,
        trust_remote_code=True,
        device_map="auto",
        torch_dtype=torch.float16
    )
    print(f"Success! Loaded class: {type(model).__name__}")
    print(f"Has generate method? {hasattr(model, 'generate')}")
except Exception as e:
    print("Loading Failed:", e)
    import traceback
    traceback.print_exc()
