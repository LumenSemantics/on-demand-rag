from __future__ import annotations

import httpx
import feedparser

from .base import Item

# 일부 피드는 기본 urllib User-Agent를 차단하므로 브라우저 형태 UA로 요청.
_UA = "Mozilla/5.0 (compatible; ARIP/0.1; +https://github.com/LumenSemantics/on-demand-rag)"


def collect(name: str, url: str, limit: int = 15) -> list[Item]:
    """범용 RSS/Atom 피드를 가져온다.

    httpx로 직접 받아 상태 코드를 확인하므로, 죽은 피드(404 등)는
    조용히 0건이 되지 않고 예외로 드러나 상위에서 로그된다.
    """
    resp = httpx.get(url, headers={"User-Agent": _UA}, timeout=30.0, follow_redirects=True)
    resp.raise_for_status()

    feed = feedparser.parse(resp.content)
    items: list[Item] = []
    for e in feed.entries[:limit]:
        uid = e.get("id") or e.get("link") or e.get("title", "")
        items.append(
            Item(
                id=f"rss:{name}:{uid}",
                source=f"rss:{name}",
                title=" ".join(e.get("title", "").split()),
                url=e.get("link", ""),
                abstract=" ".join((e.get("summary", "") or "").split())[:500],
                published=e.get("published", e.get("updated", "")),
            )
        )
    return items
