from __future__ import annotations

import argparse
import sys

from ..config import Config, load_config
from ..main import _force_utf8_stdout, collect_all
from . import embed, graph, store


def _cmd_check(cfg: Config) -> int:
    """임베딩·Qdrant·Neo4j 연결을 각각 점검."""
    ok = True
    try:
        v = embed.embed_texts(["연결 테스트"], cfg.embed_provider, cfg.llm_api_key, cfg.embed_model)
        print(f"[embed]  OK  ({cfg.embed_provider}, dim {len(v[0])})")
    except Exception as e:  # noqa: BLE001
        print(f"[embed]  실패: {e}", file=sys.stderr)
        ok = False
    try:
        store.get_client(cfg.qdrant_url, cfg.qdrant_api_key).get_collections()
        print("[qdrant] OK")
    except Exception as e:  # noqa: BLE001
        print(f"[qdrant] 실패: {e}", file=sys.stderr)
        ok = False
    try:
        drv = graph.get_driver(cfg.neo4j_uri, cfg.neo4j_user, cfg.neo4j_password)
        drv.verify_connectivity()
        drv.close()
        print("[neo4j]  OK")
    except Exception as e:  # noqa: BLE001
        print(f"[neo4j]  실패: {e}", file=sys.stderr)
        ok = False
    print("모두 정상 ✅" if ok else "일부 실패 — 위 로그 확인")
    return 0 if ok else 1


def _cmd_index(cfg: Config, limit: int) -> int:
    """수집한 항목을 임베딩해 Qdrant + Neo4j에 색인(멱등)."""
    items, _ = collect_all(cfg)
    if limit > 0:
        items = items[:limit]
    if not items:
        print("수집 항목 없음")
        return 0
    texts = [f"{it.title}\n{it.abstract}".strip() for it in items]
    vecs = embed.embed_texts(texts, cfg.embed_provider, cfg.llm_api_key, cfg.embed_model)

    qc = store.get_client(cfg.qdrant_url, cfg.qdrant_api_key)
    store.ensure_collection(qc, len(vecs[0]))
    print(f"[qdrant] {store.index(qc, items, vecs)}건 색인")

    drv = graph.get_driver(cfg.neo4j_uri, cfg.neo4j_user, cfg.neo4j_password)
    graph.ensure_constraints(drv)
    print(f"[neo4j]  {graph.index(drv, items)}건 색인")
    drv.close()
    return 0


def _cmd_search(cfg: Config, query: str, limit: int) -> int:
    """벡터 유사도 검색."""
    qv = embed.embed_texts([query], cfg.embed_provider, cfg.llm_api_key, cfg.embed_model)[0]
    qc = store.get_client(cfg.qdrant_url, cfg.qdrant_api_key)
    print(f"질의: {query}")
    for h in store.search(qc, qv, limit=limit):
        p = h.payload or {}
        title = p.get("title_ko") or p.get("title", "")
        print(f"  {h.score:.3f}  {title}")
        print(f"         {p.get('url', '')}")
    return 0


def _cmd_related(cfg: Config, query: str, limit: int) -> int:
    """쿼리로 기준 문서를 벡터 검색한 뒤, 그래프상 관련 문서를 보여준다(GraphRAG)."""
    qv = embed.embed_texts([query], cfg.embed_provider, cfg.llm_api_key, cfg.embed_model)[0]
    qc = store.get_client(cfg.qdrant_url, cfg.qdrant_api_key)
    hits = store.search(qc, qv, limit=1)
    if not hits:
        print("검색 결과 없음")
        return 0
    p = hits[0].payload or {}
    print(f"기준 문서: {p.get('title_ko') or p.get('title', '')}")
    print(f"           {p.get('url', '')}  [{p.get('category', '')}]")

    drv = graph.get_driver(cfg.neo4j_uri, cfg.neo4j_user, cfg.neo4j_password)
    rel = graph.related_docs(drv, p.get("doc_id", ""), limit=limit)
    drv.close()
    print(f"\n── 그래프상 관련 문서 {len(rel)}건 (카테고리·저자 공유) ──")
    for r in rel:
        print(f"  (공유 {r['shared']})  {r['title']}")
        print(f"             {r['url']}")
    return 0


def _cmd_trends(cfg: Config, days: int) -> int:
    """발행일 기준 카테고리 급증 + 상위 키워드."""
    from . import trends as kb_trends

    drv = graph.get_driver(cfg.neo4j_uri, cfg.neo4j_user, cfg.neo4j_password)
    docs = kb_trends.fetch_docs(drv)
    drv.close()
    print(f"분석 문서 {len(docs)}건 (최근 {days}일 vs 이전 {days}일)")
    print("── 📈 카테고리 트렌드 ──")
    for r in kb_trends.category_trends(docs, days)[:10]:
        s = "∞" if r["surge"] == float("inf") else f"{r['surge']:.1f}x"
        arrow = "🔺" if r["surge"] > 1.2 else ("🔻" if r["surge"] < 0.8 and r["prior"] else "  ")
        print(f"  {arrow} {r['category']:18} 최근 {r['recent']:3} / 이전 {r['prior']:3}  (급증 {s})")
    terms = kb_trends.top_terms(docs, days)
    print("── 🔑 상위 키워드(최근) ──")
    print("  " + ", ".join(f"{w}({n})" for w, n in terms))
    return 0


def _cmd_ask(cfg: Config, question: str) -> int:
    """LangGraph 에이전트: 질문→검색→그래프→답변(인용)."""
    from . import agent as kb_agent

    print(f"❓ {question}\n")
    r = kb_agent.ask(cfg, question)
    print("💡 답변\n" + r["answer"] + "\n")
    print("── 근거 문서 ──")
    for i, d in enumerate(r["docs"], 1):
        print(f"  [{i}] {d['title']}")
        print(f"       {d['url']}")
    if r.get("related"):
        print("── 관련(그래프) ──")
        for x in r["related"]:
            print(f"  · {x['title']}")
    return 0


def main() -> int:
    _force_utf8_stdout()
    parser = argparse.ArgumentParser(prog="arip-kb", description="ARIP Stage 2 — 지식 계층(벡터/그래프)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check", help="임베딩·Qdrant·Neo4j 연결 점검")
    pi = sub.add_parser("index", help="수집 항목을 벡터/그래프에 색인")
    pi.add_argument("--limit", type=int, default=0, help="색인할 최대 건수(0=전체)")
    ps = sub.add_parser("search", help="벡터 유사도 검색")
    ps.add_argument("query")
    ps.add_argument("--limit", type=int, default=5)
    pr = sub.add_parser("related", help="벡터 검색 + 그래프 관련 문서(GraphRAG)")
    pr.add_argument("query")
    pr.add_argument("--limit", type=int, default=6)
    pt = sub.add_parser("trends", help="카테고리 급증 + 상위 키워드")
    pt.add_argument("--days", type=int, default=7)
    pa = sub.add_parser("ask", help="LangGraph 에이전트: 질문에 근거·인용 답변")
    pa.add_argument("question")
    args = parser.parse_args()

    cfg = load_config()
    if args.cmd == "check":
        return _cmd_check(cfg)
    if args.cmd == "index":
        return _cmd_index(cfg, args.limit)
    if args.cmd == "search":
        return _cmd_search(cfg, args.query, args.limit)
    if args.cmd == "related":
        return _cmd_related(cfg, args.query, args.limit)
    if args.cmd == "trends":
        return _cmd_trends(cfg, args.days)
    if args.cmd == "ask":
        return _cmd_ask(cfg, args.question)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
