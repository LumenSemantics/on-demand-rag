from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import datetime

from ..collectors.base import Item

# 문장 경계(마침표/물음표/느낌표 뒤 공백)로 분리
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
_HTML_TAG = re.compile(r"<[^>]+>")
_SPACE_BEFORE_PUNCT = re.compile(r"\s+([.,;:!?])")


def _excerpt(text: str, max_sentences: int = 2, max_chars: int = 280) -> str:
    """LLM 요약이 없을 때 쓰는 무료 대체: 초록/본문의 앞 몇 문장 발췌.

    HTML 태그 제거 → 공백 정리 → 앞 max_sentences 문장 → 길이 상한.
    """
    text = _HTML_TAG.sub(" ", text or "")
    text = " ".join(text.split()).strip()
    text = _SPACE_BEFORE_PUNCT.sub(r"\1", text)  # 태그 제거로 생긴 "world ." → "world."
    if not text:
        return ""
    snippet = " ".join(_SENT_SPLIT.split(text)[:max_sentences]).strip()
    if len(snippet) > max_chars:
        snippet = snippet[:max_chars].rstrip() + "…"
    return snippet

# 소스 식별자 → 사람이 읽는 한국어 섹션 라벨
_SOURCE_LABELS = {
    "arxiv": "📄 arXiv 신규 논문",
    "huggingface": "🚀 HuggingFace 인기 논문",
}
# 섹션 노출 순서 (작을수록 위)
_SOURCE_ORDER = {"arxiv": 0, "huggingface": 1}


def _label(source: str) -> str:
    if source in _SOURCE_LABELS:
        return _SOURCE_LABELS[source]
    if source.startswith("rss:"):
        return f"📰 {source[4:]}"  # "rss:OpenAI" → "📰 OpenAI"
    return source


def _order(source: str) -> tuple[int, str]:
    return (_SOURCE_ORDER.get(source, 2), source)


def _source_tag(source: str) -> str:
    if source == "arxiv":
        return "arXiv"
    if source == "huggingface":
        return "HF"
    if source.startswith("rss:"):
        return source[4:]
    return source


def _render_item(it: Item, with_source_tag: bool = False) -> list[str]:
    out: list[str] = []
    tag = f" · {_source_tag(it.source)}" if with_source_tag else ""
    title = it.title_ko or it.title  # 번역이 있으면 한국어 제목 우선
    line = f"- [{title}]({it.url}){tag}"
    if it.extra:
        line += f"  {it.extra}"
    out.append(line)
    # LLM 요약(한국어)이 있으면 우선, 없으면 초록 발췌(무료)로 대체
    detail = it.summary or _excerpt(it.abstract)
    if detail:
        out.append(f"    - {detail}")
    return out


def _source_sections(items: Sequence[Item]) -> list[str]:
    by_source: dict[str, list[Item]] = {}
    for it in items:
        by_source.setdefault(it.source, []).append(it)
    lines: list[str] = []
    for source in sorted(by_source, key=_order):
        group = by_source[source]
        lines.append(f"## {_label(source)} ({len(group)})")
        for it in group:
            lines += _render_item(it)
        lines.append("")
    return lines


def _catalog_sections(items: Sequence[Item]) -> list[str]:
    """AI 주제 카탈로그로 묶는다(카테고리별). 소스 태그를 함께 표기."""
    from ..catalog import CATEGORY_ORDER, classify

    by_cat: dict[str, list[Item]] = {}
    for it in items:
        label = it.category or classify(it)
        by_cat.setdefault(label, []).append(it)

    lines: list[str] = []
    for label in CATEGORY_ORDER:
        group = by_cat.get(label)
        if not group:
            continue
        lines.append(f"## {label} ({len(group)})")
        for it in group:
            lines += _render_item(it, with_source_tag=True)
        lines.append("")
    return lines


def build_report(items: Sequence[Item], group_by: str = "category") -> str:
    """신규 항목을 Markdown 리포트로 만든다.

    group_by="category": AI 주제 카탈로그로 묶음(기본)
    group_by="source":   소스별(arXiv/HF/RSS)로 묶음
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines: list[str] = [
        f"# 🤖 AI 연구 브리핑 — {now}",
        "",
        f"**신규 {len(items)}건**",
        "",
    ]
    if group_by == "source":
        lines += _source_sections(items)
    else:
        lines += _catalog_sections(items)
    return "\n".join(lines).rstrip() + "\n"


def build_digest(items: Sequence[Item], group_by: str = "category") -> str:
    """짧은 요약(카테고리/소스별 건수). 카카오 등 길이 제한 채널용."""
    now = datetime.now().strftime("%m/%d")
    lines = [f"🤖 AI 연구 브리핑 {now}", f"신규 {len(items)}건", ""]
    if group_by == "source":
        by: dict[str, int] = {}
        for it in items:
            by[it.source] = by.get(it.source, 0) + 1
        for src in sorted(by, key=_order):
            lines.append(f"{_label(src)} {by[src]}")
    else:
        from ..catalog import counts

        for label, n in counts(items).items():
            lines.append(f"{label} {n}")
    return "\n".join(lines)
