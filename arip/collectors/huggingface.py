from __future__ import annotations

import httpx

from .base import Item

HF_API = "https://huggingface.co/api/daily_papers"


def collect(limit: int = 30) -> list[Item]:
    """HuggingFace Daily Papers(오늘의 인기 논문)를 가져온다."""
    resp = httpx.get(HF_API, timeout=30.0, follow_redirects=True)
    resp.raise_for_status()
    data = resp.json()

    items: list[Item] = []
    for entry in data[:limit]:
        paper = entry.get("paper", {}) or {}
        pid = paper.get("id", "")
        title = paper.get("title") or entry.get("title", "")
        try:
            upvotes = int(paper.get("upvotes", 0) or 0)
        except (TypeError, ValueError):
            upvotes = 0
        items.append(
            Item(
                id=f"hf:{pid}" if pid else f"hf:{title}",
                source="huggingface",
                title=" ".join(title.split()),
                url=(f"https://huggingface.co/papers/{pid}" if pid else "https://huggingface.co/papers"),
                abstract=" ".join((paper.get("summary", "") or "").split()),
                authors=[a.get("name", "") for a in paper.get("authors", []) or []],
                published=paper.get("publishedAt", "") or entry.get("publishedAt", ""),
                extra=f"👍 {upvotes}",
                score=upvotes,  # 인기순 정렬에 사용
            )
        )
    return items
