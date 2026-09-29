"""Real configurable LangChain chat and embedding providers."""
from __future__ import annotations

import json
import os
import re
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.embeddings import Embeddings
from langchain_ollama import ChatOllama

from finance_rag.config import Settings


class JSONResponseError(ValueError):
    def __init__(self, message: str, raw_response: str) -> None:
        super().__init__(message)
        self.raw_response = raw_response


def chat_model(settings: Settings, model_name: str | None = None) -> BaseChatModel:
    selected_model = model_name or settings.llm.model
    if settings.llm.provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(model=selected_model, base_url=settings.llm.base_url,
                          temperature=settings.llm.temperature,
                          reasoning=settings.llm.reasoning,
                          num_ctx=settings.llm.num_ctx,
                          client_kwargs={"timeout": settings.llm.timeout_seconds})
    if settings.llm.provider == "groq":
        from langchain_groq import ChatGroq
        if not os.getenv("GROQ_API_KEY"):
            raise ValueError("GROQ_API_KEY is required for Groq")
        return ChatGroq(model=selected_model, temperature=settings.llm.temperature,
                        timeout=settings.llm.timeout_seconds)
    raise ValueError(f"Unsupported LLM provider: {settings.llm.provider}")


def embedding_model(settings: Settings) -> Embeddings:
    if settings.embeddings.provider == "ollama":
        from langchain_ollama import OllamaEmbeddings
        return OllamaEmbeddings(model=settings.embeddings.model,
                                base_url=settings.embeddings.base_url,
                                client_kwargs={"timeout": settings.embeddings.timeout_seconds})
    if settings.embeddings.provider == "sentence_transformers":
        from sentence_transformers import SentenceTransformer

        class LocalEmbeddings(Embeddings):
            def __init__(self) -> None:
                self.model = SentenceTransformer(settings.embeddings.model)

            def embed_documents(self, texts: list[str]) -> list[list[float]]:
                return self.model.encode(texts).tolist()

            def embed_query(self, text: str) -> list[float]:
                return self.model.encode(text).tolist()

        return LocalEmbeddings()
    raise ValueError(f"Unsupported embedding provider: {settings.embeddings.provider}")


def invoke_text(model: BaseChatModel, prompt: str) -> tuple[str, dict]:
    message = model.invoke(prompt)
    content = message.content
    text = content if isinstance(content, str) else "".join(
        str(block.get("text", "")) for block in content if isinstance(block, dict))
    return text.strip(), dict(getattr(message, "usage_metadata", None) or {})


def invoke_json_response(model: BaseChatModel, prompt: str,
                         schema: dict[str, Any] | None = None
                         ) -> tuple[dict[str, Any], dict, str]:
    if isinstance(model, ChatOllama):
        # Ollama can constrain JSON to the requested response shape. The model
        # still supplies every field value; the schema supplies no decision.
        response, usage = invoke_text(model.bind(format=schema or "json"), prompt)
    else:
        response, usage = invoke_text(model, prompt)
    match = re.search(r"\{.*\}", response, re.S)
    if not match:
        raise JSONResponseError(f"Model did not return JSON: {response[:300]}", response)
    try:
        parsed = json.loads(match.group())
    except json.JSONDecodeError as exc:
        raise JSONResponseError(f"Model returned invalid JSON: {response[:300]}", response) from exc
    if not isinstance(parsed, dict):
        raise JSONResponseError("Expected a JSON object from model", response)
    return parsed, usage, response


def invoke_json(model: BaseChatModel, prompt: str,
                schema: dict[str, Any] | None = None) -> tuple[dict[str, Any], dict]:
    parsed, usage, _ = invoke_json_response(model, prompt, schema)
    return parsed, usage
