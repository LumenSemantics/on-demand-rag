from __future__ import annotations

from collections.abc import Sequence

import httpx


def embed_texts(texts: Sequence[str], provider: str, api_key: str, model: str) -> list[list[float]]:
    """텍스트들을 임베딩 벡터로 변환한다.

    provider="gemini"  → Gemini gemini-embedding-001 (3072차원), LLM 키 재사용
    provider="openai"  → OpenAI text-embedding-3-small (1536차원)
    """
    texts = list(texts)
    if not texts:
        return []
    if provider == "gemini":
        return [_gemini(t, api_key, model) for t in texts]
    if provider == "openai":
        return _openai(texts, api_key, model)
    raise ValueError(f"지원하지 않는 EMBED_PROVIDER: {provider!r}")


def _gemini(text: str, api_key: str, model: str) -> list[float]:
    m = model or "gemini-embedding-001"
    r = httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{m}:embedContent",
        params={"key": api_key},
        json={"content": {"parts": [{"text": text[:8000]}]}},
        timeout=30.0,
    )
    r.raise_for_status()
    return r.json()["embedding"]["values"]


def _openai(texts: list[str], api_key: str, model: str) -> list[list[float]]:
    r = httpx.post(
        "https://api.openai.com/v1/embeddings",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": model or "text-embedding-3-small", "input": [t[:8000] for t in texts]},
        timeout=60.0,
    )
    r.raise_for_status()
    return [d["embedding"] for d in r.json()["data"]]
