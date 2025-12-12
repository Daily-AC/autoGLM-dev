"""Model client for AI inference using OpenAI-compatible or Anthropic API."""

import json
import os
from dataclasses import dataclass, field
from typing import Any

from openai import OpenAI
try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from phone_agent.logging import get_logger

# Module logger
logger = get_logger("model")


@dataclass
class ModelConfig:
    """Configuration for the AI model."""

    base_url: str = field(default_factory=lambda: os.environ.get("AUTOGLM_BASE_URL", "http://localhost:8000/v1"))
    api_key: str = field(default_factory=lambda: os.environ.get("AUTOGLM_API_KEY", "EMPTY"))
    model_name: str = field(default_factory=lambda: os.environ.get("AUTOGLM_MODEL", "autoglm-phone-9b"))
    max_tokens: int = field(default_factory=lambda: int(os.environ.get("AUTOGLM_MAX_TOKENS", "3000")))
    temperature: float = field(default_factory=lambda: float(os.environ.get("AUTOGLM_TEMPERATURE", "0.0")))
    top_p: float = 0.85
    frequency_penalty: float = 0.2
    extra_body: dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelResponse:
    """Response from the AI model."""

    thinking: str
    action: str
    raw_content: str


class ModelClient:
    """
    Client for interacting with OpenAI-compatible or Anthropic models.

    Args:
        config: Model configuration.
    """

    def __init__(self, config: ModelConfig | None = None):
        self.config = config or ModelConfig()
        self.is_anthropic = "claude" in self.config.model_name.lower()
        
        if self.is_anthropic:
            if not ANTHROPIC_AVAILABLE:
                raise ImportError("Anthropic library not installed. Run: pip install anthropic")
            
            # Adjust Base URL for Anthropic if needed
            # User provided: https://anyrouter.top -> Anthropic expects https://anyrouter.top (SDK adds /v1/messages)
            # Or if user provided https://anyrouter.top/v1, we need to handle it.
            # The Anthropic SDK 'base_url' usually expects the root, but let's be careful.
            # If standard OpenAI URL is provided (endswith /v1), we strip it for Anthropic usually,
            # BUT AnyRouter might just proxy /v1/messages.
            # Let's try to use the base_url as is, but Anthropic requests don't use the same endpoints.
            
            # Simple heuristic: If it ends in /v1, remove it for Anthropic SDK if the SDK adds it?
            # actually Anthropic SDK default is https://api.anthropic.com
            
            self.anthropic_client = Anthropic(
                base_url=self.config.base_url.replace("/v1", ""), # Attempt to strip /v1 for SDK
                api_key=self.config.api_key
            )
        else:
            self.client = OpenAI(base_url=self.config.base_url, api_key=self.config.api_key)

    def request(self, messages: list[dict[str, Any]]) -> ModelResponse:
        """
        Send a request to the model.

        Args:
            messages: List of message dictionaries.

        Returns:
            ModelResponse containing thinking and action.

        Raises:
            ValueError: If the response cannot be parsed.
        """
        max_retries = 3
        raw_content = ""

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    messages=messages,
                    model=self.config.model_name,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                    top_p=self.config.top_p,
                    frequency_penalty=self.config.frequency_penalty,
                    extra_body=self.config.extra_body,
                    stream=False,
                )

                raw_content = response.choices[0].message.content
                
                if raw_content and raw_content.strip():
                    break # Success
                
                logger.warn("Model returned empty content", attempt=attempt+1, max_retries=max_retries, finish_reason=response.choices[0].finish_reason)
                if attempt < max_retries - 1:
                    import time
                    time.sleep(1.0) # Wait a bit before retry
                    
            except Exception as e:
                logger.error("API call failed", attempt=attempt+1, max_retries=max_retries, error=str(e))
                if attempt == max_retries - 1:
                    raw_content = "" # Ensure it's empty string if failed
                else:
                    import time
                    time.sleep(1.0)
        
        if not raw_content:
             raw_content = ""
        
        # print(f"[DEBUG] Raw Model Content: {raw_content[:200]}...") # Uncomment to debug
        thinking, action = self._parse_response(raw_content)
        return ModelResponse(thinking=thinking, action=action, raw_content=raw_content)

    def _request_anthropic(self, messages: list[dict[str, Any]]) -> ModelResponse:
        # Extract system message if present (Anthropic handles it separately)
        system_prompt = ""
        filtered_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                # Convert OpenAI image format to Anthropic image format if necessary
                # OpenAI: {type: image_url, image_url: {url: data:image/...}}
                # Anthropic: {type: image, source: {type: base64, media_type: ..., data: ...}}
                content = msg["content"]
                if isinstance(content, list):
                    new_content = []
                    for item in content:
                        if item["type"] == "text":
                            new_content.append({"type": "text", "text": item["text"]})
                        elif item["type"] == "image_url":
                            # Parse data url
                            data_url = item["image_url"]["url"]
                            if data_url.startswith("data:"):
                                header, data = data_url.split(",", 1)
                                media_type = header.split(";")[0].split(":")[1]
                                new_content.append({
                                    "type": "image", 
                                    "source": {
                                        "type": "base64",
                                        "media_type": media_type,
                                        "data": data
                                    }
                                })
                    msg["content"] = new_content
                filtered_messages.append(msg)

        response = self.anthropic_client.messages.create(
            model=self.config.model_name,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            system=system_prompt,
            messages=filtered_messages
        )

        raw_content = response.content[0].text
        thinking, action = self._parse_response(raw_content)
        return ModelResponse(thinking=thinking, action=action, raw_content=raw_content)

    def _parse_response(self, content: str) -> tuple[str, str]:
        """
        Parse the model response into thinking and action parts.

        Parsing rules:
        1. If content contains 'finish(message=', everything before is thinking,
           everything from 'finish(message=' onwards is action.
        2. If rule 1 doesn't apply but content contains 'do(action=',
           everything before is thinking, everything from 'do(action=' onwards is action.
        3. Fallback: If content contains '<answer>', use legacy parsing with XML tags.
        4. Otherwise, return empty thinking and full content as action.

        Args:
            content: Raw response content.

        Returns:
            Tuple of (thinking, action).
        """
        # Rule 1: Check for finish(message=
        if "finish(message=" in content:
            parts = content.split("finish(message=", 1)
            thinking = parts[0].strip()
            action = "finish(message=" + parts[1]
            return thinking, action

        # Rule 2: Check for do(action=
        if "do(action=" in content:
            parts = content.split("do(action=", 1)
            thinking = parts[0].strip()
            action = "do(action=" + parts[1]
            return thinking, action

        # Rule 3: Fallback to legacy XML tag parsing
        if "<answer>" in content:
            parts = content.split("<answer>", 1)
            thinking = parts[0].replace("<think>", "").replace("</think>", "").strip()
            action = parts[1].replace("</answer>", "").strip()
            return thinking, action

        # Rule 4: No markers found, return content as action
        return "", content


class MessageBuilder:
    """Helper class for building conversation messages."""

    @staticmethod
    def create_system_message(content: str) -> dict[str, Any]:
        """Create a system message."""
        return {"role": "system", "content": content}

    @staticmethod
    def create_user_message(
        text: str, image_base64: str | None = None
    ) -> dict[str, Any]:
        """
        Create a user message with optional image.
        
        Args:
            text: Text content.
            image_base64: Optional base64-encoded image.
        
        Returns:
            Message dictionary.
        """
        content = []

        if image_base64:
            # Resize logic: Decode -> Resize -> Encode to save token/latency
            try:
                from PIL import Image
                import io
                import base64
                
                # Decode
                img_data = base64.b64decode(image_base64)
                img = Image.open(io.BytesIO(img_data))
                
                # Resize if needed (max 1024px on long side)
                max_dim = 1024
                if max(img.width, img.height) > max_dim:
                    scale = max_dim / max(img.width, img.height)
                    new_size = (int(img.width * scale), int(img.height * scale))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                    
                    # Re-encode
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=85) # Use JPEG for smaller size
                    image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
                    # print(f"[DEBUG] Resized image to {new_size}")
            except Exception as e:
                # If PIL missing or fail, fallback to original
                logger.warn("Failed to resize image", error=str(e))

            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}, # Default to jpeg
                }
            )

        content.append({"type": "text", "text": text})

        return {"role": "user", "content": content}

    @staticmethod
    def create_assistant_message(content: str) -> dict[str, Any]:
        """Create an assistant message."""
        return {"role": "assistant", "content": content}

    @staticmethod
    def remove_images_from_message(message: dict[str, Any]) -> dict[str, Any]:
        """
        Remove image content from a message to save context space.
        """
        if isinstance(message.get("content"), list):
            message["content"] = [
                item for item in message["content"] if item.get("type") == "text"
            ]
        return message

    @staticmethod
    def build_screen_info(current_app: str, **extra_info) -> str:
        """
        Build screen info string for the model.
        """
        info = {"current_app": current_app, **extra_info}
        return json.dumps(info, ensure_ascii=False)
