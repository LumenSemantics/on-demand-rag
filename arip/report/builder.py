from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from ..collectors.base import Item


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
    for source in sorted(by_source):
        group = by_source[source]
        lines.append(f"## {source} ({len(group)})")
        for it in group:
            line = f"- [{it.title}]({it.url})"
            if it.extra:
                line += f"  {it.extra}"
            lines.append(line)
            if it.summary:
                lines.append(f"    - {it.summary}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
