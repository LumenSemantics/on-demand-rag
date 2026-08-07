from __future__ import annotations

from collections.abc import Sequence

from .collectors.base import Item


def keyword_filter(
    items: Sequence[Item],
    include: Sequence[str] | None,
    exclude: Sequence[str] | None,
) -> list[Item]:
    """제목+초록 기준 키워드 필터.

    - exclude: 하나라도 걸리면 제외
    - include: 지정되면 하나라도 있어야 통과 (비어 있으면 전체 통과)
    대소문자 무시.
    """
    inc = [w.lower() for w in (include or []) if w]
    exc = [w.lower() for w in (exclude or []) if w]
    if not inc and not exc:
        return list(items)

    out: list[Item] = []
    for it in items:
        hay = f"{it.title} {it.abstract}".lower()
        if exc and any(w in hay for w in exc):
            continue
        if inc and not any(w in hay for w in inc):
            continue
        out.append(it)
    return out


def sort_and_cap(items: Sequence[Item], max_per_source: int = 0) -> list[Item]:
    """소스별로 score 내림차순 정렬 후, 소스마다 max_per_source개로 제한.

    Python 정렬은 안정적이라 score가 같은 항목(예: arXiv, RSS는 전부 0)은
    원래 순서(최신순/피드순)를 유지한다. max_per_source<=0이면 제한 없음.
    """
    groups: dict[str, list[Item]] = {}
    order: list[str] = []
    for it in items:
        if it.source not in groups:
            groups[it.source] = []
            order.append(it.source)
        groups[it.source].append(it)

    result: list[Item] = []
    for src in order:
        g = sorted(groups[src], key=lambda x: x.score, reverse=True)
        if max_per_source and max_per_source > 0:
            g = g[:max_per_source]
        result.extend(g)
    return result
