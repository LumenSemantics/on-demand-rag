# Stack (1)

---

# **AI Research Intelligence Platform** 수집 Pipeline

```
                    Scheduler
                       |
        ┌──────────────┼──────────────┐
        │              │              │
     arXiv        HF Papers       Blogs
        │              │              │
        └──────────────┼──────────────┘
                       |
                 Web Crawler
                 (RSS/API)
                       |
              Document Parser
                       |
             LLM Summarizer
                       |
        ┌──────────────┴──────────────┐
        │                             │
   Vector DB                     Knowledge Graph
   Qdrant                        Neo4j
        │                             │
        └──────────────┬──────────────┘
                       |
                AI Daily Briefing
```

---

# 수집 우선순위 추천

## Tier 1 (매일)

- arXiv
    - cs.AI
    - cs.CL
    - cs.LG
    - cs.IR
- Hugging Face Daily Papers
- DeepSeek
- Qwen
- Moonshot
- Z.ai
- MiniMax

## Tier 2 (주간)

- OpenAI Research
- Anthropic Research
- Google DeepMind
- Microsoft Research
- NVIDIA Research

## Tier 3 (정책 영향 분석)

- Federal Register
- White House AI 관련 문서
- NIST AI Safety

---

# 자동화 구현 추천 Stack

사용자께서 이전에 검토하셨던 RAG/GraphRAG 환경 기준이면:

```
Crawler
 ├─ Playwright
 ├─ Scrapy
 └─ RSS Parser

Processing
 ├─ LlamaParse
 ├─ Unstructured
 └─ BeautifulSoup

Storage
 ├─ Qdrant (Embedding Search)
 └─ Neo4j (Research Knowledge Graph)

Agent
 ├─ LangGraph
 ├─ FastAPI
 └─ n8n Scheduler

LLM
 ├─ GPT
 ├─ Claude
 ├─ Qwen
 └─ DeepSeek
```

특히 **"AI Research Radar + GraphRAG"** 형태로 구축하면

논문 → 연구자 → Lab → Model → Benchmark → Code Repository 관계를 그래프로 추적할 수 있습니다.