"""Pydantic models for API requests/responses."""

from pydantic import BaseModel


class Profile(BaseModel):
    """Model configuration profile."""
    name: str
    provider: str = "OpenAI"  # OpenAI | Anthropic
    base_url: str
    api_key: str
    model: str
    is_active: bool = False


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""
    task: str
