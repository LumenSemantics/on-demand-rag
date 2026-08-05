from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from ..collectors.base import Item

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
            if it.summary:
                lines.append(f"    - {it.summary}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
