
import os
# Set mirror BEFORE importing transformers/huggingface_hub
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

import argparse
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Union, Dict, Any
from transformers import AutoModelForCausalLM, AutoTokenizer, TextStreamer
import torch
import base64
import io
from PIL import Image

# Define Pydantic models for request/response validation
class ChatMessage(BaseModel):
    role: str
    content: Union[str, List[Dict[str, Any]]]

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    max_tokens: Optional[int] = 2560
    temperature: Optional[float] = 0.1
    top_p: Optional[float] = 0.9
    stream: Optional[bool] = False

class ChatCompletionResponseChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: Optional[str] = "stop"

class ChatCompletionResponse(BaseModel):
    id: str = "chatcmpl-default"
    object: str = "chat.completion"
    created: int = 0
    model: str
    choices: List[ChatCompletionResponseChoice]
    usage: Dict[str, int] = {}

app = FastAPI()
model = None
processor = None

def load_model(model_name: str, cache_dir: Optional[str] = None, quantize: str = "none"):
    global model, processor
    max_retries = 10
    import time
    
    # Configure quantization if requested
    quantization_config = None
    if quantize == "4bit":
        from transformers import BitsAndBytesConfig
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True
        )
        print("⚡ Enabling 4-bit Quantization (Low VRAM Mode)")
    elif quantize == "8bit":
        from transformers import BitsAndBytesConfig
        quantization_config = BitsAndBytesConfig(load_in_8bit=True)
        print("⚡ Enabling 8-bit Quantization")

    for attempt in range(max_retries):
        print(f"Loading model: {model_name} (Attempt {attempt+1}/{max_retries})...")
        try:
            from transformers import AutoProcessor, AutoModelForMultimodalLM
            
            # Load processor (handles images + text)
            print("Loading AutoProcessor...")
            processor = AutoProcessor.from_pretrained(model_name, trust_remote_code=True, cache_dir=cache_dir)
            
            print("Trying AutoModelForMultimodalLM...")
            # Use eager attention to avoid Kernel Deadlocks on new architectures (RTX 5090/sm_120)
            model = AutoModelForMultimodalLM.from_pretrained(
                model_name,
                torch_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
                device_map="auto",
                trust_remote_code=True,
                cache_dir=cache_dir,
                quantization_config=quantization_config, # Apply quantization
                attn_implementation="eager" # Force standard attention implementation
            )

            # Validate generation capability
            if not hasattr(model, "generate"):
                raise ValueError(f"Loaded model type '{type(model).__name__}' does not have a 'generate' method!")

            print(f"Model loaded successfully! ({type(model).__name__})")
            return # Success
            
        except Exception as e:
            print(f"Error loading model: {e}")
            is_network_error = "peer closed connection" in str(e) or "HTTPSConnectionPool" in str(e) or "ReadTimeout" in str(e)
            if is_network_error:
                print("Network error detected. Retrying in 5 seconds...")
                time.sleep(5)
            else:
                print("Retrying in 5 seconds...")
                time.sleep(5)
    
    raise Exception("Failed to load model after multiple retries")

@app.post("/v1/chat/completions")
async def create_chat_completion(request: ChatCompletionRequest):
    global model, processor
    if model is None:
        raise HTTPException(status_code=500, detail="Model not initialized")

    try:
        # Convert request.messages to pure list of dicts for processor
        messages_list = []
        for m in request.messages:
            # Handle list of content (text + image)
            content = m.content
            if hasattr(content, "model_dump"):
                 content = content.model_dump()
            elif isinstance(content, list):
                 content = [c.model_dump() if hasattr(c, "model_dump") else c for c in content]
            
            if isinstance(content, str):
                content = [{"type": "text", "text": content}]
            
            new_content = []
            for item in content:
                if item.get("type") == "image_url":
                    data_url = item["image_url"]["url"]
                    if "base64," in data_url:
                        base64_str = data_url.split("base64,")[1]
                        image_data = base64.b64decode(base64_str)
                        image = Image.open(io.BytesIO(image_data)).convert("RGB")
                        max_dim = 1024
                        if max(image.size) > max_dim:
                            image.thumbnail((max_dim, max_dim))
                        new_content.append({"type": "image", "image": image})
                    else:
                        print("Warning: Non-base64 image URL found, ignoring.")
                elif item.get("type") == "image":
                     new_content.append(item)
                else:
                     new_content.append(item)

            messages_list.append({"role": m.role, "content": new_content})

        print(f"Processing request with {len(messages_list)} messages...")
        
        inputs = processor.apply_chat_template(
            messages_list, 
            add_generation_prompt=True, 
            return_dict=True, 
            tokenize=True, 
            return_tensors="pt"
        ).to(model.device)

        terminators = [
            processor.tokenizer.eos_token_id,
            processor.tokenizer.convert_tokens_to_ids("<|endoftext|>"),
            processor.tokenizer.convert_tokens_to_ids("<|user|>"), 
            processor.tokenizer.convert_tokens_to_ids("<|observation|>")
        ]
        terminators = [t for t in terminators if t is not None]

        gen_kwargs = {
            "max_new_tokens": min(request.max_tokens or 1024, 2048),
            "do_sample": True,
            "temperature": max(request.temperature if request.temperature is not None else 0.1, 0.01),
            "top_p": request.top_p if request.top_p else 0.8,
            "eos_token_id": terminators,
        }
        
        # --- STREAMING LOGIC ---
        if request.stream:
            from transformers import TextIteratorStreamer
            from threading import Thread
            from fastapi.responses import StreamingResponse
            import json
            import time

            # Use TextIteratorStreamer
            streamer = TextIteratorStreamer(processor.tokenizer, skip_prompt=True, skip_special_tokens=True)
            gen_kwargs["streamer"] = streamer
            
            # Run generation in a separate thread
            thread = Thread(target=model.generate, kwargs={**inputs, **gen_kwargs})
            thread.start()

            async def stream_generator():
                chat_id = "chatcmpl-" + base64.b64encode(os.urandom(6)).decode('utf-8')
                created = int(time.time())
                
                # Yield role first
                chunk = {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": request.model,
                    "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}]
                }
                yield f"data: {json.dumps(chunk)}\n\n"
                
                generated_text = ""
                
                for new_text in streamer:
                    generated_text += new_text
                    
                    # Safety Net: Check for hallucination in stream
                    # Ideally we buffer a bit, but for now simple checking
                    if "finish(" in new_text or "do(" in new_text:
                        # If we see an action start, we let it pass, but if we see text AFTER action, 
                        # we might want to stop. But streaming is hard to retract.
                        pass

                    chunk = {
                        "id": chat_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": request.model,
                        "choices": [{"index": 0, "delta": {"content": new_text}, "finish_reason": None}]
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
                
                # Final chunk
                chunk = {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": request.model,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
                }
                yield f"data: {json.dumps(chunk)}\n\n"
                yield "data: [DONE]\n\n"

            return StreamingResponse(stream_generator(), media_type="text/event-stream")

        # --- NON-STREAMING LOGIC (Legacy) ---
        else:
            with torch.no_grad():
                outputs = model.generate(**inputs, **gen_kwargs)
            
            input_len = inputs["input_ids"].shape[1]
            response_text = processor.decode(outputs[0][input_len:], skip_special_tokens=True)
            
            # (Truncation logic omitted for brevity in non-streaming, but kept same as before if needed)
            
            choice = ChatCompletionResponseChoice(
                index=0,
                message=ChatMessage(role="assistant", content=response_text),
                finish_reason="stop"
            )
            return ChatCompletionResponse(model=request.model, choices=[choice])

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")

@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {"id": "autoglm-phone-9b", "object": "model", "created": 0, "owned_by": "zai-org"}
        ]
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Local AutoGLM Model Server")
    parser.add_argument("--model", type=str, default="zai-org/AutoGLM-Phone-9B", help="Model name or path")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=1428, help="Port to bind")
    parser.add_argument("--quantize", type=str, choices=["4bit", "8bit", "none"], default="4bit", help="Quantization mode to save VRAM")
    args = parser.parse_args()

    # Load model before starting server
    load_model(args.model, quantize=args.quantize)

    uvicorn.run(app, host=args.host, port=args.port)
