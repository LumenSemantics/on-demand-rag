from __future__ import annotations

import feedparser

from .base import Item


def collect(name: str, url: str, limit: int = 15) -> list[Item]:
    """범용 RSS/Atom 피드를 가져온다."""
    feed = feedparser.parse(url)
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
