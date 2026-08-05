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


def test_build_report_falls_back_to_excerpt_when_no_summary():
    abstract = "First sentence here. Second sentence here. Third should be dropped."
    items = [Item(id="a", source="arxiv", title="T", url="http://x", abstract=abstract)]
    report = build_report(items)
    # LLM 요약이 없으면 앞 2문장 발췌가 들어가고 3번째 문장은 빠진다
    assert "First sentence here. Second sentence here." in report
    assert "Third should be dropped" not in report


def test_build_report_strips_html_in_excerpt():
    items = [Item(id="a", source="rss:X", title="T", url="http://x", abstract="<p>Hello <b>world</b>.</p>")]
    report = build_report(items)
    assert "Hello world." in report
    assert "<p>" not in report and "<b>" not in report
