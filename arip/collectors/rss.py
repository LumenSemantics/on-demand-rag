from __future__ import annotations

import html
import re

import httpx
import feedparser

from .base import Item

# 일부 피드는 기본 urllib User-Agent를 차단하므로 브라우저 형태 UA로 요청.
_UA = "Mozilla/5.0 (compatible; ARIP/0.1; +https://github.com/LumenSemantics/on-demand-rag)"

_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_BEFORE_PUNCT = re.compile(r"\s+([.,;:!?])")
# 국내 매체가 초록 앞에 붙이는 이미지 크레딧 주석
# (예: "/챗GPT의 도움을 받아 제작한 이미지입니다.")은 기사 내용이 아니라
# 편집 주석이라 키워드 매칭(gpt 오탐)·요약을 오염시키므로 걷어낸다.
# "받아"와 "제작" 사이에 문구가 끼는 변형도 포괄한다.
_CREDIT_RE = re.compile(r"/?\s*[^.]{0,40}?도움을 받아[^.]{0,60}?제작[^.]{0,20}?입니다\.\s*")


def _clean(text: str) -> str:
    """초록에 섞인 원본 HTML과 이미지 크레딧 주석을 걷어낸다.

    일부 피드는 summary에 <img> 마크업을 그대로 담고, 국내 매체는 본문 앞에
    "…도움을 받아 제작한 이미지입니다." 같은 크레딧을 붙여 키워드 매칭·요약·
    카탈로그 분류를 오염시킨다. 태그·엔티티·크레딧을 제거해 순수 텍스트만 남긴다.
    """
    no_tags = _TAG_RE.sub(" ", text or "")
    unescaped = html.unescape(no_tags)
    no_credit = _CREDIT_RE.sub(" ", unescaped)
    collapsed = " ".join(no_credit.split())
    return _SPACE_BEFORE_PUNCT.sub(r"\1", collapsed)  # 태그 제거로 생긴 "world ." → "world."


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
                title=_clean(e.get("title", "")),
                url=e.get("link", ""),
                abstract=_clean(e.get("summary", "") or "")[:500],
                published=e.get("published", e.get("updated", "")),
            )
        )
    return items
