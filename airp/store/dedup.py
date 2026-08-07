from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path

from ..collectors.base import Item


class SeenStore:
    """이미 알림으로 보낸 항목을 SQLite에 기록해 중복을 막는다."""

    def __init__(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS seen ("
            "  id TEXT PRIMARY KEY,"
            "  source TEXT,"
            "  title TEXT,"
            "  first_seen TEXT"
            ")"
        )
        self.conn.commit()

    def filter_new(self, items: Iterable[Item]) -> list[Item]:
        """아직 기록되지 않은(=신규) 항목만 돌려준다."""
        new: list[Item] = []
        seen_ids: set[str] = set()
        for it in items:
            if it.id in seen_ids:
                continue  # 이번 실행 내 중복
            cur = self.conn.execute("SELECT 1 FROM seen WHERE id = ?", (it.id,))
            if cur.fetchone() is None:
                new.append(it)
                seen_ids.add(it.id)
        return new

    def mark_seen(self, items: Iterable[Item]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.executemany(
            "INSERT OR IGNORE INTO seen (id, source, title, first_seen) VALUES (?, ?, ?, ?)",
            [(it.id, it.source, it.title, now) for it in items],
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
