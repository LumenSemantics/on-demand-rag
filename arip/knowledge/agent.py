from __future__ import annotations

from typing import TypedDict

from ..config import Config
from ..summarize import llm
from . import embed, graph, store


class State(TypedDict):
    question: str
    docs: list
    related: list
    answer: str


def build_agent(cfg: Config):
    """LangGraph: retrieve(벡터) → expand(그래프) → generate(LLM 답변)."""
    from langgraph.graph import END, START, StateGraph

    def retrieve(state: State) -> dict:
        qv = embed.embed_texts([state["question"]], cfg.embed_provider, cfg.llm_api_key, cfg.embed_model)[0]
        qc = store.get_client(cfg.qdrant_url, cfg.qdrant_api_key)
        docs = []
        for h in store.search(qc, qv, limit=6):
            p = h.payload or {}
            docs.append(
                {
                    "title": p.get("title_ko") or p.get("title", ""),
                    "url": p.get("url", ""),
                    "summary": p.get("summary", ""),
                    "category": p.get("category", ""),
                    "doc_id": p.get("doc_id", ""),
                }
            )
        return {"docs": docs}

    def expand(state: State) -> dict:
        related: list = []
        if state["docs"] and cfg.neo4j_uri:
            drv = graph.get_driver(cfg.neo4j_uri, cfg.neo4j_user, cfg.neo4j_password)
            try:
                related = graph.related_docs(drv, state["docs"][0]["doc_id"], limit=4)
            finally:
                drv.close()
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
    g.add_node("retrieve", retrieve)
    g.add_node("expand", expand)
    g.add_node("generate", generate)
    g.add_edge(START, "retrieve")
    g.add_edge("retrieve", "expand")
    g.add_edge("expand", "generate")
    g.add_edge("generate", END)
    return g.compile()


def ask(cfg: Config, question: str) -> State:
    app = build_agent(cfg)
    return app.invoke({"question": question, "docs": [], "related": [], "answer": ""})
