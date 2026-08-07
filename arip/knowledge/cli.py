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
    if r.get("queries"):
        print("🧭 하위 질의: " + " · ".join(r["queries"]) + "\n")
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


def _cmd_eval(cfg: Config, n: int) -> int:
    """검색 품질: 색인 문서 제목으로 자기 검색 → recall@1/@5·MRR."""
    qc = store.get_client(cfg.qdrant_url, cfg.qdrant_api_key)
    samples = [p for p in store.sample(qc, n) if p.get("title") and p.get("doc_id")]
    if not samples:
        print("샘플 없음")
        return 0
    vecs = embed.embed_texts([p["title"] for p in samples], cfg.embed_provider, cfg.llm_api_key, cfg.embed_model)
    ranks: list[int | None] = []
    for p, v in zip(samples, vecs):
        hits = store.search(qc, v, limit=5)
        rank = next((i for i, h in enumerate(hits, 1) if (h.payload or {}).get("doc_id") == p["doc_id"]), None)
        ranks.append(rank)
    total = len(ranks)
    r1 = sum(1 for r in ranks if r == 1) / total
    r5 = sum(1 for r in ranks if r is not None) / total
    mrr = sum(1 / r for r in ranks if r) / total
    print(f"검색 품질 평가 ({total}건, 제목→자기검색)")
    print(f"  recall@1 : {r1:.0%}")
    print(f"  recall@5 : {r5:.0%}")
    print(f"  MRR      : {mrr:.3f}")
    return 0


def _cmd_weekly(cfg: Config, days: int, send: bool) -> int:
    """최근 days일 롤업 다이제스트: 급상승·카테고리 분포·키워드. 저장 + 선택 발송."""
    import pathlib
    from collections import Counter
    from datetime import timedelta

    from ..notify import email as email_notify
    from ..notify import kakao, slack
    from . import trends as kb_trends

    drv = graph.get_driver(cfg.neo4j_uri, cfg.neo4j_user, cfg.neo4j_password)
    docs = kb_trends.fetch_docs(drv)
    drv.close()
    dates = [d for _, d, _ in docs if d]
    if not dates:
        print("주간 데이터 없음")
        return 0
    today = max(dates)
    start = today - timedelta(days=days - 1)
    recent = [(c, d, t) for c, d, t in docs if d and d >= start]
    dist = Counter(c for c, _, _ in recent if c)
    rows = kb_trends.category_trends(docs, days=days)
    terms = kb_trends.top_terms(docs, days=days)

    def fmt(s: float) -> str:
        return "∞" if s == float("inf") else f"{s:.1f}x"

    md = [f"# 📅 AI 주간 다이제스트 ({today}, 최근 {days}일)", "", f"**총 {len(recent)}건**", ""]
    surging = [r for r in rows if r["surge"] >= 3 and r["recent"] >= 3]
    if surging:
        md.append("## 🚨 급상승")
        md += [f"- {r['category']}: {r['recent']}건 ({fmt(r['surge'])})" for r in surging[:6]]
        md.append("")
    md.append("## 📊 카테고리 분포")
    md += [f"- {c}: {n}건" for c, n in dist.most_common()]
    md += ["", "## 🔑 키워드", ", ".join(f"{w}({n})" for w, n in terms)]
    report = "\n".join(md) + "\n"
    print(report)

    p = pathlib.Path(cfg.archive_dir) / f"weekly-{today}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(report, encoding="utf-8")
    print(f"[archive] {p}")

    if send:
        if cfg.slack_webhook:
            try:
                slack.send(cfg.slack_webhook, report)
                print("[slack] 발송")
            except Exception as e:  # noqa: BLE001
                print(f"[slack] 실패: {e}")
        if cfg.smtp_host and cfg.email_to:
            try:
                email_notify.send(cfg.smtp_host, cfg.smtp_port, cfg.smtp_user, cfg.smtp_password,
                                  cfg.email_to, "AI 주간 다이제스트", report)
                print("[email] 발송")
            except Exception as e:  # noqa: BLE001
                print(f"[email] 실패: {e}")
        if cfg.kakao_rest_api_key and cfg.kakao_refresh_token:
            short = f"📅 AI 주간 다이제스트\n총 {len(recent)}건\n" + "\n".join(
                f"{c} {n}" for c, n in dist.most_common()[:8]
            )
            try:
                kakao.send(cfg.kakao_rest_api_key, cfg.kakao_refresh_token, short,
                           cfg.report_base_url or "https://github.com/LumenSemantics/on-demand-rag")
                print("[kakao] 발송")
            except Exception as e:  # noqa: BLE001
                print(f"[kakao] 실패: {e}")
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
    pe = sub.add_parser("eval", help="검색 품질 평가(recall@k·MRR)")
    pe.add_argument("--n", type=int, default=20)
    pw = sub.add_parser("weekly", help="주간 다이제스트 생성·저장·발송")
    pw.add_argument("--days", type=int, default=7)
    pw.add_argument("--send", action="store_true", help="Slack/Email/카카오로 발송")
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
    if args.cmd == "eval":
        return _cmd_eval(cfg, args.n)
    if args.cmd == "weekly":
        return _cmd_weekly(cfg, args.days, args.send)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
