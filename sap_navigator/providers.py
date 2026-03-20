from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx


class EmbeddingProvider(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        ...

    def embed_query(self, text: str) -> list[float]:
        ...


class ChatProvider(Protocol):
    def chat(self, messages: list[dict[str, str]], *, temperature: float = 0.1) -> str:
        ...


@dataclass(slots=True)
class OllamaEmbeddingProvider:
    model: str
    base_url: str
    timeout: float = 120.0

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        payload = {"model": self.model, "input": texts}
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(f"{self.base_url.rstrip('/')}/api/embed", json=payload)
            if response.status_code == 404:
                return [self._legacy_embed(client, text) for text in texts]
            response.raise_for_status()
            data = response.json()
            return data["embeddings"]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

    def _legacy_embed(self, client: httpx.Client, text: str) -> list[float]:
        response = client.post(
            f"{self.base_url.rstrip('/')}/api/embeddings",
            json={"model": self.model, "prompt": text},
        )
        response.raise_for_status()
        data = response.json()
        return data["embedding"]


@dataclass(slots=True)
class OpenAIEmbeddingProvider:
    model: str
    base_url: str | None = None
    api_key: str | None = None

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        from openai import OpenAI

        client = OpenAI(**_openai_client_args(self.base_url, self.api_key))
        response = client.embeddings.create(model=self.model, input=texts)
        return [item.embedding for item in response.data]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


@dataclass(slots=True)
class OllamaChatProvider:
    model: str
    base_url: str
    timeout: float = 180.0

    def chat(self, messages: list[dict[str, str]], *, temperature: float = 0.1) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(f"{self.base_url.rstrip('/')}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
        return data["message"]["content"].strip()


@dataclass(slots=True)
class OpenAIChatProvider:
    model: str
    base_url: str | None = None
    api_key: str | None = None

    def chat(self, messages: list[dict[str, str]], *, temperature: float = 0.1) -> str:
        from openai import OpenAI

        client = OpenAI(**_openai_client_args(self.base_url, self.api_key))
        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )
        return response.choices[0].message.content.strip()


def build_embedding_provider(provider: str, *, model: str, base_url: str, api_key: str = "") -> EmbeddingProvider:
    provider = provider.lower().strip()
    if provider == "ollama":
        return OllamaEmbeddingProvider(model=model, base_url=base_url)
    if provider in {"openai", "lmstudio"}:
        return OpenAIEmbeddingProvider(model=model, base_url=base_url or None, api_key=api_key or None)
    raise ValueError(f"Unsupported embedding provider: {provider}")


def build_chat_provider(provider: str, *, model: str, base_url: str, api_key: str = "") -> ChatProvider:
    provider = provider.lower().strip()
    if provider == "ollama":
        return OllamaChatProvider(model=model, base_url=base_url)
    if provider in {"openai", "lmstudio"}:
        return OpenAIChatProvider(model=model, base_url=base_url or None, api_key=api_key or None)
    raise ValueError(f"Unsupported chat provider: {provider}")


def _openai_client_args(base_url: str | None, api_key: str | None) -> dict[str, str]:
    client_args: dict[str, str] = {}
    if base_url:
        client_args["base_url"] = base_url.rstrip("/")
    if api_key:
        client_args["api_key"] = api_key
    elif base_url:
        client_args["api_key"] = "lm-studio"
    return client_args
