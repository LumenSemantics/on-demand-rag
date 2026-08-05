import os
import tempfile

from arip.collectors.base import Item
from arip.report.builder import build_report
from arip.store.dedup import SeenStore


def test_filter_new_and_mark():
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "t.db")
        store = SeenStore(db)
        items = [Item(id="a", source="s", title="A", url="u")]

        # 처음엔 신규
        assert store.filter_new(items) == items

        # 기록 후엔 신규 아님
        store.mark_seen(items)
        assert store.filter_new(items) == []
        store.close()


def test_filter_new_dedups_within_batch():
    with tempfile.TemporaryDirectory() as d:
        store = SeenStore(os.path.join(d, "t.db"))
        items = [
            Item(id="x", source="s", title="X", url="u1"),
            Item(id="x", source="s", title="X dup", url="u2"),
        ]
        # 같은 id는 배치 내에서도 1건만
        assert len(store.filter_new(items)) == 1
        store.close()


def test_build_report_contains_title_and_summary():
    items = [Item(id="a", source="arxiv", title="Hello", url="http://x", summary="한 줄 요약")]
    report = build_report(items)
    assert "Hello" in report
    assert "한 줄 요약" in report
    assert "신규 1건" in report
