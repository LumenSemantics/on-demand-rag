from __future__ import annotations

import httpx

# 텔레그램 sendMessage는 메시지당 4096자 제한 → 여유를 두고 자른다.
TELEGRAM_TEXT_LIMIT = 4000


def split_message(text: str, limit: int = TELEGRAM_TEXT_LIMIT) -> list[str]:
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


def send(bot_token: str, chat_id: str, text: str) -> None:
    """텔레그램 봇으로 메시지를 보낸다. 한도 초과 시 나눠 발송.

    마크다운 파싱 오류(400)를 피하려고 parse_mode 없이 평문으로 보낸다.
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    chunks = split_message(text)
    for i, chunk in enumerate(chunks):
        if len(chunks) > 1:
            chunk = f"({i + 1}/{len(chunks)})\n{chunk}"
        r = httpx.post(
            url,
            json={"chat_id": chat_id, "text": chunk, "disable_web_page_preview": True},
            timeout=30.0,
        )
        r.raise_for_status()
