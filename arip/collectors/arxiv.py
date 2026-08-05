from __future__ import annotations

import httpx
import feedparser

from .base import Item

ARXIV_API = "https://export.arxiv.org/api/query"


def collect(categories: list[str], max_results: int = 30) -> list[Item]:
    """arXiv 공식 API에서 최신 논문을 가져온다 (Atom 응답)."""
    query = " OR ".join(f"cat:{c}" for c in categories)
    params = {
        "search_query": query,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": str(max_results),
    }
    resp = httpx.get(ARXIV_API, params=params, timeout=60.0, follow_redirects=True)
    resp.raise_for_status()

    feed = feedparser.parse(resp.text)
    items: list[Item] = []
    for e in feed.entries:
        items.append(
            Item(
                id=e.get("id", e.get("link", "")),
                source="arxiv",
                title=" ".join(e.get("title", "").split()),
                url=e.get("link", ""),
                abstract=" ".join(e.get("summary", "").split()),
                authors=[a.get("name", "") for a in e.get("authors", [])],
                published=e.get("published", ""),
            )
        )
    return items
