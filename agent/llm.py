"""Thin wrapper around the OpenAI-compatible client (AI Proxy).

Centralises client creation, chat completions, and embeddings so the rest of
the codebase never constructs the client directly.
"""
from __future__ import annotations

import threading
from functools import lru_cache

from core.config import settings
from core.logging import get_logger
from openai import OpenAI

logger = get_logger(__name__)

_lock = threading.Lock()
_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                _client = OpenAI(
                    api_key=settings.aiproxy_token,
                    base_url=settings.aiproxy_base_url,
                )
    return _client


def chat(messages: list[dict], **kwargs) -> str:
    """Return the text content of the first choice for a chat completion."""
    resp = get_client().chat.completions.create(messages=messages, **kwargs)
    return resp.choices[0].message.content or ""


@lru_cache(maxsize=4096)
def get_embedding(text: str) -> list[float]:
    """Fetch an embedding vector. Cached per text to avoid duplicate calls."""
    resp = get_client().embeddings.create(
        input=text, model=settings.embedding_model
    )
    return resp.data[0].embedding
