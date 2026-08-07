from __future__ import annotations

from typing import TypedDict

from ..config import Config
from ..summarize import llm
from . import embed, graph, store


class State(TypedDict):
    question: str
    queries: list
    docs: list
    related: list
    answer: str


def build_agent(cfg: Config):
    """LangGraph: retrieve(벡터) → expand(그래프) → generate(LLM 답변)."""
    from langgraph.graph import END, START, StateGraph

    def plan(state: State) -> dict:
        prompt = (
            "다음 질문에 답하기 위해 검색할 핵심 하위 질의를 2~3개, 한 줄에 하나씩만 출력하라. "
            "설명·번호 없이 질의문만.\n\n질문: " + state["question"]
        )
        try:
            raw = llm.complete(prompt, cfg.llm_provider, cfg.llm_api_key, cfg.llm_model, max_tokens=150)
            queries = [ln.strip(" -•*\t") for ln in raw.splitlines() if ln.strip()][:3]
        except Exception:  # noqa: BLE001
            queries = []
        return {"queries": queries or [state["question"]]}

    def retrieve(state: State) -> dict:
        qc = store.shared_client(cfg.qdrant_url, cfg.qdrant_api_key)
        seen: dict = {}
        for q in state["queries"]:
            qv = embed.embed_texts([q], cfg.embed_provider, cfg.llm_api_key, cfg.embed_model)[0]
            for h in store.search(qc, qv, limit=4):
                p = h.payload or {}
                did = p.get("doc_id", "")
                if did and did not in seen:
                    seen[did] = {
                        "title": p.get("title_ko") or p.get("title", ""),
                        "url": p.get("url", ""),
                        "summary": p.get("summary", ""),
                        "category": p.get("category", ""),
                        "doc_id": did,
                    }
        return {"docs": list(seen.values())[:8]}

    def expand(state: State) -> dict:
        related: list = []
        if state["docs"] and cfg.neo4j_uri:
            drv = graph.shared_driver(cfg.neo4j_uri, cfg.neo4j_user, cfg.neo4j_password)
            related = graph.related_docs(drv, state["docs"][0]["doc_id"], limit=4)
        return {"related": related}

    def generate(state: State) -> dict:
        ctx = "\n".join(
            f"[{i}] {d['title']} — {(d.get('summary') or '')[:200]} ({d['url']})"
            for i, d in enumerate(state["docs"], 1)
        )
        prompt = (
            "다음 문서들을 근거로 질문에 한국어로 간결히 답하라. "
            "각 핵심 주장 끝에 [번호]로 근거 문서를 인용하고, 문서에 없는 내용은 추측하지 마라.\n\n"
            f"질문: {state['question']}\n\n문서:\n{ctx}\n\n답변:"
        )
        try:
            answer = llm.complete(prompt, cfg.llm_provider, cfg.llm_api_key, cfg.llm_model, max_tokens=600)
        except Exception as e:  # noqa: BLE001
            answer = f"(생성 실패: {e})"
        return {"answer": answer}

    g = StateGraph(State)
    g.add_node("plan", plan)
    g.add_node("retrieve", retrieve)
    g.add_node("expand", expand)
    g.add_node("generate", generate)
    g.add_edge(START, "plan")
    g.add_edge("plan", "retrieve")
    g.add_edge("retrieve", "expand")
    g.add_edge("expand", "generate")
    g.add_edge("generate", END)
    return g.compile()


_COMPILED = None


def ask(cfg: Config, question: str) -> State:
    # 컴파일된 그래프를 프로세스 단위로 1회만 만들어 재사용(웹 서버 요청마다 재컴파일 방지).
    global _COMPILED
    if _COMPILED is None:
        _COMPILED = build_agent(cfg)
    return _COMPILED.invoke({"question": question, "queries": [], "docs": [], "related": [], "answer": ""})
