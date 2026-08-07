from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

# reports/YYYY-MM-DD.md (같은 날 여러 번이면 _N 접미사 허용)
_REPORT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:_\d+)?\.md$")


def write_report(report_md: str, archive_dir: str = "reports", now: datetime | None = None) -> Path:
    """리포트를 reports/YYYY-MM-DD.md 로 저장한다(같은 날은 덮어씀)."""
    now = now or datetime.now()
    d = Path(archive_dir)
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{now:%Y-%m-%d}.md"
    path.write_text(report_md, encoding="utf-8")
    return path


def rebuild_index(archive_dir: str = "reports") -> Path:
    """reports 폴더의 모든 리포트를 최신순으로 나열한 index.md 를 재생성한다.

    GitHub이 .md를 그대로 렌더링하므로 별도 Pages 설정 없이 웹에서 열람 가능.
    """
    d = Path(archive_dir)
    d.mkdir(parents=True, exist_ok=True)
    names = sorted(
        (p.name for p in d.glob("*.md") if p.name != "index.md" and _REPORT_RE.match(p.name)),
        reverse=True,
    )
    lines = ["# 🗂️ AI 연구 브리핑 아카이브", "", f"총 {len(names)}일치", ""]
    for name in names:
        lines.append(f"- [{name[:-3]}]({name})")  # ".md" 제거해 날짜만 표시
    idx = d / "index.md"
    idx.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return idx
