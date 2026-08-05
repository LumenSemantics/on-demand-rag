from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Item:
    """수집된 항목 하나(논문/글)를 나타내는 공통 표현."""

    id: str  # 중복 제거 키 (arXiv id / URL / rss guid 등)
    source: str  # "arxiv", "huggingface", "rss:The Batch" ...
    title: str
    url: str
    abstract: str = ""
    authors: list[str] = field(default_factory=list)
    published: str = ""
    extra: str = ""  # 부가 표시 (예: "👍 42")
    score: int = 0  # 정렬용 중요도 (예: HF upvotes). 없으면 0
    category: str = ""  # AI 카탈로그 분류 라벨 (catalog.classify로 채움)
    summary: str = ""  # LLM 한 줄 요약 (나중에 채워짐)
