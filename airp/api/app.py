from __future__ import annotations

from functools import lru_cache

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from ..config import load_config
from ..knowledge import embed, graph, store

app = FastAPI(title="AIRP GraphRAG")
_cfg = load_config()


@lru_cache(maxsize=256)
def _embed_query(q: str) -> tuple[float, ...]:
    """질의 임베딩 캐시. 웹 UI는 같은 질의로 검색+그래프를 잇달아 호출하므로 중복 임베딩을 막는다."""
    return tuple(embed.embed_texts([q], _cfg.embed_provider, _cfg.llm_api_key, _cfg.embed_model)[0])


@app.on_event("shutdown")
def _shutdown() -> None:
    graph.close_shared()


@app.get("/healthz")
def healthz() -> dict:
    """가벼운 헬스체크(외부 호출 없음). Cloud Run 프로브용."""
    return {"status": "ok"}


@app.get("/api/search")
def api_search(q: str, limit: int = 8) -> dict:
    """벡터 유사도 검색 + 상위 문서의 그래프 관련 문서(GraphRAG)."""
    qv = list(_embed_query(q))
    qc = store.shared_client(_cfg.qdrant_url, _cfg.qdrant_api_key)
    hits = store.search(qc, qv, limit=limit)
    results = [
        {
            "score": round(float(h.score), 3),
            "title": (h.payload or {}).get("title_ko") or (h.payload or {}).get("title", ""),
            "url": (h.payload or {}).get("url", ""),
            "category": (h.payload or {}).get("category", ""),
            "source": (h.payload or {}).get("source", ""),
            "doc_id": (h.payload or {}).get("doc_id", ""),
        }
        for h in hits
    ]
    related: list[dict] = []
    if results and _cfg.neo4j_uri:
        drv = graph.shared_driver(_cfg.neo4j_uri, _cfg.neo4j_user, _cfg.neo4j_password)
        related = graph.related_docs(drv, results[0]["doc_id"], limit=6)
    return {"query": q, "results": results, "related": related}


@app.get("/api/graph")
def api_graph(q: str) -> dict:
    """상위 문서의 이웃(카테고리·저자·관련문서)을 노드/엣지로 반환."""
    qv = list(_embed_query(q))
    qc = store.shared_client(_cfg.qdrant_url, _cfg.qdrant_api_key)
    hits = store.search(qc, qv, limit=1)
    if not hits or not _cfg.neo4j_uri:
        return {"nodes": [], "edges": []}
    doc_id = (hits[0].payload or {}).get("doc_id", "")
    drv = graph.shared_driver(_cfg.neo4j_uri, _cfg.neo4j_user, _cfg.neo4j_password)
    nb = graph.neighborhood(drv, doc_id)
    if not nb:
        return {"nodes": [], "edges": []}
    nodes = [{"id": "doc", "label": (nb["title"] or "")[:40], "group": "doc"}]
    edges = []
    for c in nb["categories"]:
        nodes.append({"id": f"cat:{c}", "label": c, "group": "category"})
        edges.append({"from": "doc", "to": f"cat:{c}"})
    for a in nb["authors"]:
        nodes.append({"id": f"au:{a}", "label": a, "group": "author"})
        edges.append({"from": f"au:{a}", "to": "doc"})
    for o in nb["related"]:
        nid = f"rel:{o['id']}"
        nodes.append({"id": nid, "label": (o["title"] or "")[:38], "group": "related"})
        edges.append({"from": "doc", "to": nid, "dashes": True})
    return {"nodes": nodes, "edges": edges}


@app.get("/api/ask")
def api_ask(q: str) -> dict:
    """LangGraph 에이전트: 질문→하위질의→검색→그래프→인용 답변."""
    from ..knowledge import agent as kb_agent

    r = kb_agent.ask(_cfg, q)
    return {
        "question": q,
        "queries": r.get("queries", []),
        "answer": r.get("answer", ""),
        "docs": r.get("docs", []),
    }


@app.get("/api/trends")
def api_trends(days: int = 7) -> dict:
    """카테고리 급증 + 상위 키워드."""
    from ..knowledge import trends as kb_trends

    if not _cfg.neo4j_uri:
        return {"categories": [], "terms": []}
    drv = graph.shared_driver(_cfg.neo4j_uri, _cfg.neo4j_user, _cfg.neo4j_password)
    docs = kb_trends.fetch_docs(drv)
    cats = [
        {
            "category": r["category"], "recent": r["recent"], "prior": r["prior"],
            "surge": "∞" if r["surge"] == float("inf") else round(r["surge"], 1),
            "hot": r["surge"] >= 3 and r["recent"] >= 3,
        }
        for r in kb_trends.category_trends(docs, days=days)[:10]
    ]
    terms = [{"term": w, "count": n} for w, n in kb_trends.top_terms(docs, days=days, n=20)]
    return {"categories": cats, "terms": terms}


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return _PAGE


_PAGE = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AIRP GraphRAG 검색</title>
<style>
  :root { color-scheme: light dark; }
  * { box-sizing: border-box; }
  body { font-family: system-ui, -apple-system, "Segoe UI", sans-serif; max-width: 820px;
         margin: 0 auto; padding: 24px; line-height: 1.5; }
  h1 { font-size: 1.4rem; margin: 0 0 4px; }
  .sub { opacity: .65; font-size: .85rem; margin-bottom: 16px; }
  .bar { display: flex; gap: 8px; }
  input { flex: 1; padding: 10px 12px; border: 1px solid #8886; border-radius: 8px;
          font-size: 1rem; background: transparent; color: inherit; }
  button { padding: 10px 16px; border: 0; border-radius: 8px; background: #4f46e5; color: #fff;
           font-size: 1rem; cursor: pointer; }
  h2 { font-size: .95rem; opacity: .7; margin: 22px 0 8px; }
  .item { padding: 10px 12px; border: 1px solid #8883; border-radius: 8px; margin: 8px 0; }
  .item a { text-decoration: none; color: inherit; font-weight: 600; }
  .item a:hover { text-decoration: underline; }
  .meta { font-size: .78rem; opacity: .7; margin-top: 4px; display: flex; gap: 8px; flex-wrap: wrap; }
  .badge { background: #4f46e522; color: #6366f1; padding: 1px 7px; border-radius: 999px; }
  .score { font-variant-numeric: tabular-nums; }
  .empty { opacity: .6; }
  .ask { background: #059669; }
  .trend { background: #d97706; }
  .qtag { margin: 10px 0; display: flex; gap: 6px; flex-wrap: wrap; }
  .atext { white-space: pre-wrap; padding: 14px; border: 1px solid #8883; border-radius: 8px;
           background: #05966910; margin: 8px 0; }
</style></head>
<body>
  <h1>🔎 AIRP GraphRAG 검색</h1>
  <div class="sub">벡터 유사도 검색 + 지식 그래프 관련 문서</div>
  <div class="bar">
    <input id="q" placeholder="예: 효율적인 대형 언어모델 추론" autofocus>
    <button onclick="run()">검색</button>
    <button class="ask" onclick="ask()">AI 질문</button>
    <button class="trend" onclick="trends()">트렌드</button>
  </div>
  <div id="answer"></div>
  <div id="results"></div>
  <div id="related"></div>
  <h2 id="ghdr" style="display:none">🌐 지식 그래프 <span style="font-weight:400;opacity:.6;font-size:.8rem">(노드 클릭 → 그 주제로 재검색)</span></h2>
  <div id="graph" style="height:440px;border:1px solid #8883;border-radius:10px"></div>
<script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
<script>
const $ = (s) => document.querySelector(s);
function item(r, extra="") {
  return `<div class="item"><a href="${r.url}" target="_blank" rel="noopener">${r.title||"(제목 없음)"}</a>
    <div class="meta">${extra}${r.category?`<span class="badge">${r.category}</span>`:""}
    ${r.source?`<span>${r.source}</span>`:""}</div></div>`;
}
async function run() {
  const q = $("#q").value.trim(); if (!q) return;
  $("#results").innerHTML = "<p class='empty'>검색 중…</p>"; $("#related").innerHTML = "";
  try {
    const d = await (await fetch("/api/search?limit=8&q=" + encodeURIComponent(q))).json();
    $("#results").innerHTML = "<h2>유사 문서 " + d.results.length + "건</h2>" +
      d.results.map(r => item(r, `<span class="score">${r.score}</span>`)).join("") ||
      "<p class='empty'>결과 없음</p>";
    if (d.related && d.related.length)
      $("#related").innerHTML = "<h2>🕸️ 상위 문서와 관련 (카테고리·저자 공유)</h2>" +
        d.related.map(r => item(r, `<span class="score">공유 ${r.shared}</span>`)).join("");
    graph(q);
  } catch (e) { $("#results").innerHTML = "<p class='empty'>오류: " + e + "</p>"; }
}
async function graph(q) {
  try {
    const d = await (await fetch("/api/graph?q=" + encodeURIComponent(q))).json();
    $("#ghdr").style.display = d.nodes.length ? "block" : "none";
    if (!d.nodes.length) return;
    const groups = {
      doc: { color: "#4f46e5", shape: "box", font: { color: "#fff" } },
      category: { color: "#10b981" }, author: { color: "#f59e0b" }, related: { color: "#8b5cf6" }
    };
    const net = new vis.Network($("#graph"),
      { nodes: new vis.DataSet(d.nodes), edges: new vis.DataSet(d.edges) },
      { groups, nodes: { shape: "dot", size: 14, font: { size: 12 } },
        edges: { color: "#8886", smooth: false }, physics: { stabilization: true },
        interaction: { hover: true } });
    net.on("click", (params) => {          // 노드 클릭 → 그 라벨로 재검색(그래프 순회)
      if (!params.nodes.length) return;
      const n = d.nodes.find(x => x.id === params.nodes[0]);
      if (n && n.group !== "doc") { $("#q").value = n.label; run(); }
    });
  } catch (e) { /* 그래프 실패는 무시 */ }
}
async function ask() {
  const q = $("#q").value.trim(); if (!q) return;
  $("#results").innerHTML = ""; $("#related").innerHTML = ""; $("#ghdr").style.display = "none";
  $("#graph").innerHTML = ""; $("#answer").innerHTML = "<p class='empty'>🤖 생각 중… (검색·그래프·답변)</p>";
  try {
    const d = await (await fetch("/api/ask?q=" + encodeURIComponent(q))).json();
    const qtag = (d.queries || []).map(x => `<span class="badge">${x}</span>`).join(" ");
    const srcs = (d.docs || []).map((r, i) =>
      `<div class="item"><a href="${r.url}" target="_blank" rel="noopener">[${i + 1}] ${r.title}</a></div>`).join("");
    $("#answer").innerHTML =
      `<div class="qtag">🧭 ${qtag}</div><div class="atext"></div><h2>📚 근거</h2>${srcs}`;
    $("#answer .atext").textContent = d.answer || "(답변 없음)";
  } catch (e) { $("#answer").innerHTML = "<p class='empty'>오류: " + e + "</p>"; }
}
async function trends() {
  $("#results").innerHTML = ""; $("#related").innerHTML = ""; $("#ghdr").style.display = "none"; $("#graph").innerHTML = "";
  $("#answer").innerHTML = "<p class='empty'>📈 트렌드 계산 중…</p>";
  try {
    const d = await (await fetch("/api/trends?days=7")).json();
    if (!d.categories.length) { $("#answer").innerHTML = "<p class='empty'>데이터 없음</p>"; return; }
    let html = "<h2>📈 카테고리 트렌드 (최근 7일)</h2>";
    html += d.categories.map(c => {
      const s = c.surge === "∞" ? "∞" : c.surge + "x";
      return `<div class="item">${c.hot ? "🚨 " : ""}<b>${c.category}</b>
        <div class="meta"><span>최근 ${c.recent} / 이전 ${c.prior}</span><span class="badge">급증 ${s}</span></div></div>`;
    }).join("");
    html += "<h2>🔑 키워드</h2><div class='qtag'>" +
      d.terms.map(t => `<span class="badge">${t.term} ${t.count}</span>`).join(" ") + "</div>";
    $("#answer").innerHTML = html;
  } catch (e) { $("#answer").innerHTML = "<p class='empty'>오류: " + e + "</p>"; }
}
$("#q").addEventListener("keydown", e => { if (e.key === "Enter") run(); });
</script>
</body></html>"""


def main() -> None:
    """웹 UI 서버 실행: uv run airp-api [--host H] [--port P]

    Cloud Run 등 컨테이너 환경에서는 인자 없이 실행하면 HOST/PORT 환경변수를
    따른다(Cloud Run은 PORT를 주입한다). 컨테이너에서는 HOST=0.0.0.0 로 둔다.
    """
    import argparse
    import os

    import uvicorn

    p = argparse.ArgumentParser(prog="airp-api", description="AIRP GraphRAG 웹 UI 서버")
    p.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    p.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    a = p.parse_args()
    print(f"AIRP 웹 UI → http://{a.host}:{a.port}  (종료: Ctrl+C)")
    uvicorn.run(app, host=a.host, port=a.port)


if __name__ == "__main__":
    main()
