from __future__ import annotations

import httpx

SLACK_TEXT_LIMIT = 39000


def split_message(text: str, limit: int = SLACK_TEXT_LIMIT) -> list[str]:
    """긴 메시지를 한도 이하 여러 조각으로 나눈다(줄 경계에서만 분할)."""
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    cur: list[str] = []
    cur_len = 0
    for line in text.split("\n"):
        add = len(line) + 1
        if cur and cur_len + add > limit:
            chunks.append("\n".join(cur))
            cur, cur_len = [], 0
        cur.append(line)
        cur_len += add
    if cur:
        chunks.append("\n".join(cur))
    return chunks


def send(webhook_url: str, text: str) -> None:
    """Slack Incoming Webhook으로 메시지를 보낸다. 한도 초과 시 나눠 발송."""
    chunks = split_message(text)
    for i, chunk in enumerate(chunks):
        if len(chunks) > 1:
            chunk = f"({i + 1}/{len(chunks)})\n{chunk}"
        r = httpx.post(webhook_url, json={"text": chunk}, timeout=30.0)
        r.raise_for_status()
