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


def build_report(items: Sequence[Item]) -> str:
    """신규 항목들을 소스별로 묶어 Markdown 리포트로 만든다."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    by_source: dict[str, list[Item]] = {}
    for it in items:
        by_source.setdefault(it.source, []).append(it)

    lines: list[str] = [
        f"# 🤖 AI 연구 브리핑 — {now}",
        "",
        f"**신규 {len(items)}건**",
        "",
    ]
    for source in sorted(by_source, key=_order):
        group = by_source[source]
        lines.append(f"## {_label(source)} ({len(group)})")
        for it in group:
            line = f"- [{it.title}]({it.url})"
            if it.extra:
                line += f"  {it.extra}"
            lines.append(line)
            # LLM 요약(한국어)이 있으면 우선, 없으면 초록 발췌(무료)로 대체
            detail = it.summary or _excerpt(it.abstract)
            if detail:
                lines.append(f"    - {detail}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
