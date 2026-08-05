from __future__ import annotations

import httpx

PROMPT = (
    "다음은 AI 연구 논문 또는 기술 글의 내용이다. "
    "핵심을 한국어 한 문장으로만 요약해라. "
    "제목·고유명사·기술 용어는 원문 그대로 두고, 설명만 한국어로. "
    "군더더기 없이 한 줄로:\n\n"
)


def summarize(text: str, provider: str, api_key: str, model: str) -> str:
    """초록을 한 줄로 요약한다. 실패하거나 미설정이면 빈 문자열(=요약 생략)."""
    text = (text or "").strip()
    if not text or not provider or not api_key:
        return ""

    prompt = PROMPT + text[:4000]
    try:
        if provider == "openai":
            return _openai(prompt, api_key, model)
        if provider == "anthropic":
            return _anthropic(prompt, api_key, model)
        if provider == "gemini":
            return _gemini(prompt, api_key, model)
    except Exception:
        return ""
    return ""


def _openai(prompt: str, api_key: str, model: str) -> str:
    r = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model or "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 150,
        },
        timeout=40.0,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def _anthropic(prompt: str, api_key: str, model: str) -> str:
    r = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
        json={
            "model": model or "claude-3-5-haiku-latest",
            "max_tokens": 150,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=40.0,
    )
    r.raise_for_status()
    return r.json()["content"][0]["text"].strip()


def _gemini(prompt: str, api_key: str, model: str) -> str:
    m = model or "gemini-2.0-flash"
    r = httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent",
        params={"key": api_key},
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=40.0,
    )
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
