from __future__ import annotations

import httpx

SLACK_TEXT_LIMIT = 39000


def send(webhook_url: str, text: str) -> None:
    """Slack Incoming Webhook으로 메시지를 보낸다."""
    if len(text) > SLACK_TEXT_LIMIT:
        text = text[:SLACK_TEXT_LIMIT] + "\n… (생략)"
    r = httpx.post(webhook_url, json={"text": text}, timeout=30.0)
    r.raise_for_status()
