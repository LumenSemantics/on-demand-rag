import os
import tempfile
from datetime import datetime

from arip.archive import rebuild_index, write_report
from arip.collectors.base import Item
from arip.curate import keyword_filter, sort_and_cap
from arip.report.builder import build_report
from arip.store.dedup import SeenStore


def _mk(id, source="arxiv", title="T", abstract="", score=0):
    return Item(id=id, source=source, title=title, url="http://x", abstract=abstract, score=score)


def test_keyword_include_and_exclude():
    items = [
        _mk("1", title="A survey of RAG systems"),
        _mk("2", title="Robotics manipulation"),
        _mk("3", title="LLM agent planning"),
    ]
    # include: rag/agent 중 하나 있어야 통과
    inc = keyword_filter(items, ["rag", "agent"], [])
    assert {i.id for i in inc} == {"1", "3"}
    # exclude: robotics 제외
    exc = keyword_filter(items, [], ["robotics"])
    assert {i.id for i in exc} == {"1", "3"}
    # 둘 다 비면 전체 통과
    assert len(keyword_filter(items, [], [])) == 3


def test_archive_write_and_index_newest_first():
    with tempfile.TemporaryDirectory() as d:
        p1 = write_report("# A\n", d, now=datetime(2026, 8, 1, 7, 0))
        p2 = write_report("# B\n", d, now=datetime(2026, 8, 3, 7, 0))
        assert p1.name == "2026-08-01.md"
        assert p2.name == "2026-08-03.md"

        idx = rebuild_index(d)
        text = idx.read_text(encoding="utf-8")
        assert "총 2일치" in text
        # 최신(08-03)이 위, index.md 자신은 목록에서 제외
        assert text.index("2026-08-03") < text.index("2026-08-01")
        assert "index.md)" not in text


def test_sort_and_cap_by_score_per_source():
    items = [
        _mk("a1", source="huggingface", score=5),
        _mk("a2", source="huggingface", score=50),
        _mk("a3", source="huggingface", score=1),
        _mk("b1", source="arxiv", score=0),
        _mk("b2", source="arxiv", score=0),
    ]
    out = sort_and_cap(items, max_per_source=2)
    hf = [i.id for i in out if i.source == "huggingface"]
    ax = [i.id for i in out if i.source == "arxiv"]
    # HF는 upvotes 높은 순 상위 2개
    assert hf == ["a2", "a1"]
    # arXiv는 score 동일 → 원래 순서 유지, 상한 2
    assert ax == ["b1", "b2"]


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
