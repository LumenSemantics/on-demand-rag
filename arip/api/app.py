from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from ..config import load_config
from ..knowledge import embed, graph, store

app = FastAPI(title="ARIP GraphRAG")
_cfg = load_config()


@app.get("/api/search")
def api_search(q: str, limit: int = 8) -> dict:
    """벡터 유사도 검색 + 상위 문서의 그래프 관련 문서(GraphRAG)."""
    qv = embed.embed_texts([q], _cfg.embed_provider, _cfg.llm_api_key, _cfg.embed_model)[0]
    qc = store.get_client(_cfg.qdrant_url, _cfg.qdrant_api_key)
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
        drv = graph.get_driver(_cfg.neo4j_uri, _cfg.neo4j_user, _cfg.neo4j_password)
        try:
            related = graph.related_docs(drv, results[0]["doc_id"], limit=6)
        finally:
            drv.close()
    return {"query": q, "results": results, "related": related}


@app.get("/api/graph")
def api_graph(q: str) -> dict:
    """상위 문서의 이웃(카테고리·저자·관련문서)을 노드/엣지로 반환."""
    qv = embed.embed_texts([q], _cfg.embed_provider, _cfg.llm_api_key, _cfg.embed_model)[0]
    qc = store.get_client(_cfg.qdrant_url, _cfg.qdrant_api_key)
    hits = store.search(qc, qv, limit=1)
    if not hits or not _cfg.neo4j_uri:
        return {"nodes": [], "edges": []}
    doc_id = (hits[0].payload or {}).get("doc_id", "")
    drv = graph.get_driver(_cfg.neo4j_uri, _cfg.neo4j_user, _cfg.neo4j_password)
    try:
        nb = graph.neighborhood(drv, doc_id)
    finally:
        drv.close()
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


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return _PAGE


_PAGE = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ARIP GraphRAG 검색</title>
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
</style></head>
<body>
  <h1>🔎 ARIP GraphRAG 검색</h1>
  <div class="sub">벡터 유사도 검색 + 지식 그래프 관련 문서</div>
  <div class="bar">
    <input id="q" placeholder="예: 효율적인 대형 언어모델 추론" autofocus>
    <button onclick="run()">검색</button>
  </div>
  <div id="results"></div>
  <div id="related"></div>
  <h2 id="ghdr" style="display:none">🌐 지식 그래프 (문서·카테고리·저자·관련문서)</h2>
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
    new vis.Network($("#graph"),
      { nodes: new vis.DataSet(d.nodes), edges: new vis.DataSet(d.edges) },
      { groups, nodes: { shape: "dot", size: 14, font: { size: 12 } },
        edges: { color: "#8886", smooth: false }, physics: { stabilization: true },
        interaction: { hover: true } });
  } catch (e) { /* 그래프 실패는 무시 */ }
}
$("#q").addEventListener("keydown", e => { if (e.key === "Enter") run(); });
</script>
</body></html>"""


def main() -> None:
    """개발 서버 실행: uv run arip-api"""
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
