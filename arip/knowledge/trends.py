from __future__ import annotations

import re
from collections import Counter
from datetime import date, datetime, timedelta
from email.utils import parsedate_to_datetime

from neo4j import Driver

_FETCH = """
MATCH (d:Document)
OPTIONAL MATCH (d)-[:HAS_CATEGORY]->(c:Category)
RETURN c.label AS category, d.published AS published, d.title AS title
"""

_WORD = re.compile(r"[A-Za-z][A-Za-z0-9\-]{2,}")
_STOP = set(
    "the a an of for and or to in on with via using their our we is are be new toward towards "
    "from at into over under can does do this that these those model models language large learning "
    "based approach method framework via can more via not but its it as by".split()
)


def _parse_date(s: str) -> date | None:
    s = (s or "").strip()
    if not s:
        return None
    try:  # ISO (arXiv 등)
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except ValueError:
        pass
    try:  # RFC822 (RSS)
        return parsedate_to_datetime(s).date()
    except (TypeError, ValueError):
        return None


def fetch_docs(driver: Driver) -> list[tuple[str, date | None, str]]:
    with driver.session() as s:
        return [(r["category"], _parse_date(r["published"]), r["title"] or "") for r in s.run(_FETCH)]


def category_trends(docs, days: int = 7) -> list[dict]:
    """최근 days일 vs 그 이전 days일의 카테고리별 문서 수와 급증 배율."""
    dates = [d for _, d, _ in docs if d]
    if not dates:
        return []
    today = max(dates)
    recent_start = today - timedelta(days=days - 1)
    prior_start = recent_start - timedelta(days=days)
    recent: Counter = Counter()
    prior: Counter = Counter()
    for cat, dt, _ in docs:
        if not cat or not dt:
            continue
        if recent_start <= dt <= today:
            recent[cat] += 1
        elif prior_start <= dt < recent_start:
            prior[cat] += 1
    rows = []
    for cat in set(recent) | set(prior):
        r, p = recent[cat], prior[cat]
        surge = (r / p) if p else (float("inf") if r else 0.0)
        rows.append({"category": cat, "recent": r, "prior": p, "surge": surge})
    rows.sort(key=lambda x: (x["recent"], x["surge"]), reverse=True)
    return rows


def top_terms(docs, days: int = 7, n: int = 15) -> list[tuple[str, int]]:
    """최근 days일 문서 제목의 상위 키워드."""
    dates = [d for _, d, _ in docs if d]
    if not dates:
        return []
    recent_start = max(dates) - timedelta(days=days - 1)
    c: Counter = Counter()
    for _, dt, title in docs:
        if not dt or dt < recent_start:
            continue
        for w in _WORD.findall(title.lower()):
            if w not in _STOP:
                c[w] += 1
    return c.most_common(n)
