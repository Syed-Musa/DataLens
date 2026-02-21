"""Chat engine - orchestrate retrieval + AI for natural language queries."""

import json
import logging
from typing import Any

from services.ai_engine import get_ai_engine
from services.vector_store import get_vector_store

logger = logging.getLogger(__name__)


class ChatEngine:
    """Orchestrates embedding, FAISS retrieval, and AI response."""

    def __init__(self) -> None:
        self._vector_store = get_vector_store()
        self._ai = get_ai_engine()

    def chat(self, message: str, history: list[dict[str, str]] | None = None) -> dict[str, Any]:
        """Process chat: embed question, retrieve context, generate response."""
        docs = self._vector_store.search(message, top_k=5)
        return self._ai.chat_with_context(message, docs, history)


def get_chat_engine() -> ChatEngine:
    """Get chat engine instance."""
    return ChatEngine()
