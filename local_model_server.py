
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

@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def create_chat_completion(request: ChatCompletionRequest):
    global model, processor
    if model is None:
        raise HTTPException(status_code=500, detail="Model not initialized")

    try:
        # Convert request.messages to pure list of dicts for processor
        # AND convert OpenAI image_url format to Hugging Face "image" format (PIL Image)
        messages_list = []
        for m in request.messages:
            # Handle list of content (text + image)
            content = m.content
            if hasattr(content, "model_dump"):
                 content = content.model_dump()
            elif isinstance(content, list):
                 # re-verify items in list are dicts
                 content = [c.model_dump() if hasattr(c, "model_dump") else c for c in content]
            
            # Convert string content (e.g. system prompt) to list of dicts
            if isinstance(content, str):
                content = [{"type": "text", "text": content}]
            
            # Process content list for images
            new_content = []
            for item in content:
                if item.get("type") == "image_url":
                    # Extract base64
                    data_url = item["image_url"]["url"]
                    if "base64," in data_url:
                        base64_str = data_url.split("base64,")[1]
                        image_data = base64.b64decode(base64_str)
                        image = Image.open(io.BytesIO(image_data)).convert("RGB")
                        
                        # Resize if too large (e.g. > 1024px) to save VRAM and tokens
                        # 1080x2400 -> 5200 tokens. Resize to max 1024 -> ~1000 tokens.
                        max_dim = 1024
                        if max(image.size) > max_dim:
                            image.thumbnail((max_dim, max_dim))
                            print(f" [INFO] Resized image to: {image.size}")
                        
                        # Transform to HuggingFace format: {"type": "image", "image": <PIL.Image>}
                        new_content.append({"type": "image", "image": image})
                        print(f" [INFO] Successfully decoded image: {image.size}")
                    else:
                        # Handle plain URLs if supported or ignore
                        print("Warning: Non-base64 image URL found, ignoring.")
                elif item.get("type") == "image":
                     # Already in correct format (unlikely from this client but possible)
                     new_content.append(item)
                else:
                     # Text or other
                     new_content.append(item)

            messages_list.append({"role": m.role, "content": new_content})

        print(f"Processing request with {len(messages_list)} messages...")
        
        # Use processor to handle text + images
        inputs = processor.apply_chat_template(
            messages_list, 
            add_generation_prompt=True, 
            return_dict=True, 
            tokenize=True, 
            return_tensors="pt"
        ).to(model.device)

        # DEBUG: Print input stats
        seq_len = inputs["input_ids"].shape[1]
        print(f" [DEBUG] Input Sequence Length: {seq_len} tokens")
        if "pixel_values" in inputs:
            print(f" [DEBUG] Image Features Shape: {inputs['pixel_values'].shape}")

        # Define comprehensive stop tokens to prevent hallucination
        terminators = [
            processor.tokenizer.eos_token_id,
            processor.tokenizer.convert_tokens_to_ids("<|endoftext|>"),
            processor.tokenizer.convert_tokens_to_ids("<|user|>"), 
            processor.tokenizer.convert_tokens_to_ids("<|observation|>")
        ]
        # Remove any None values in case tokens don't exist
        terminators = [t for t in terminators if t is not None]

        # Generate parameters - optimize for chat
        gen_kwargs = {
            "max_new_tokens": min(request.max_tokens or 1024, 2048),
            "do_sample": True,
            "temperature": max(request.temperature if request.temperature is not None else 0.1, 0.01),
            "top_p": request.top_p if request.top_p else 0.8,
            "eos_token_id": terminators,
        }
        
        # Add streamer specifically for console output
        from transformers import TextStreamer
        streamer = TextStreamer(processor.tokenizer, skip_prompt=True, skip_special_tokens=True)
        gen_kwargs["streamer"] = streamer
        
        print("Generating response (tokens will appear below)...")
        # Generate
        with torch.no_grad():
            outputs = model.generate(**inputs, **gen_kwargs)
        print("\nGeneration complete.")

        # Decode response (skip input tokens)
        input_len = inputs["input_ids"].shape[1]
        response_text = processor.decode(outputs[0][input_len:], skip_special_tokens=True)
        
        # Post-processing truncation (Safety Net)
        # If model generates "finish(...)" then continues talking, cut it off.
        # This prevents the "run-on" hallucination where it imagines executing the action.
        
        first_action_idx = -1
        # Find the EARLIEST occurrence of an action
        idx_do = response_text.find("do(")
        idx_finish = response_text.find("finish(")
        
        if idx_do != -1 and idx_finish != -1:
            first_action_idx = min(idx_do, idx_finish)
        elif idx_do != -1:
            first_action_idx = idx_do
        elif idx_finish != -1:
            first_action_idx = idx_finish
            
        if first_action_idx != -1:
            # We found an action start. Now find the matching closing parenthesis.
            # We need to be careful about nested parens or strings containing parens.
            # Simple bracket counting approach.
            balance = 0
            end_idx = -1
            
            # Start scanning from the opening parenthesis of "do(" or "finish("
            # "do(" is at first_action_idx. The '(' is at first_action_idx + 2 ("do") or + 6 ("finish")
            # Let's just scan from first_action_idx looking for the first '('
            
            start_paren = response_text.find("(", first_action_idx)
            if start_paren != -1:
                balance = 1
                for i in range(start_paren + 1, len(response_text)):
                    char = response_text[i]
                    if char == "(":
                        balance += 1
                    elif char == ")":
                        balance -= 1
                    
                    if balance == 0:
                        end_idx = i + 1 # Include the closing ')'
                        break
            
            if end_idx != -1:
                # Truncate everything after the action
                print(f" [INFO] Action detected. Truncating hallucinations after char {end_idx}.")
                response_text = response_text[:end_idx]
        
        # print(f" [DEBUG] Final Response: {response_text[:200]}...")

        # Construct response
        choice = ChatCompletionResponseChoice(
            index=0,
            message=ChatMessage(role="assistant", content=response_text),
            finish_reason="stop"
        )
        
        return ChatCompletionResponse(
            model=request.model,
            choices=[choice]
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Generation error details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}\n\n{traceback.format_exc()}")

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
    parser.add_argument("--port", type=int, default=8000, help="Port to bind")
    parser.add_argument("--quantize", type=str, choices=["4bit", "8bit", "none"], default="none", help="Quantization mode to save VRAM")
    args = parser.parse_args()

    # Load model before starting server
    load_model(args.model, quantize=args.quantize)

    uvicorn.run(app, host=args.host, port=args.port)
