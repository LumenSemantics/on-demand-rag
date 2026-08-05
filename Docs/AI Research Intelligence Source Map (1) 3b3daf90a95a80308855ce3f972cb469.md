# AI Research Intelligence Source Map (1)

특히 **Qdrant + Neo4j GraphRAG** 구조에서는 단순 논문보다:

- 논문(Paper)
- 코드(Code)
- 모델(Model)
- 데이터셋(Dataset)
- Benchmark
- 연구자(Researcher)
- 기업(Lab)
- 특허(Patent)
- 정책(Policy)

관계를 만들어야 하므로 아래 사이트를 추가하는 것이 좋습니다.

---

# 1. AI 논문 Discovery Layer (필수 추가)

| 사이트 | 역할 | 중요도 |
| --- | --- | --- |
| Semantic Scholar | AI 기반 논문 검색 + Citation Graph | ★★★★★ |
| Papers With Code | 논문 + GitHub Code + SOTA Benchmark 연결 | ★★★★★ |
| OpenReview | NeurIPS/ICLR/ICML 논문 리뷰 추적 | ★★★★★ |
| Google Scholar | 전체 학술 인용 추적 | ★★★★ |
| DBLP | CS 연구자/논문 관계 | ★★★★ |

Semantic Scholar는 2억 개 이상의 논문을 색인하고 AI 기반 검색·추천 기능을 제공하며, 논문 관계 그래프 구축에 활용하기 좋습니다. ([Semantic Scholar](https://www.semanticscholar.org/about?utm_source=chatgpt.com))

Papers With Code는 논문과 구현 코드, Benchmark 결과를 연결하는 데 유용합니다. ([Leaderboards Pro](https://leaderboards.pro/leaderboards/top-ml-benchmark-paper-tracking-platforms-june-2026-mq8fusf5?utm_source=chatgpt.com))

---

# 2. Benchmark / Evaluation 데이터

AI 연구 동향 분석에서는 매우 중요합니다.

## 추가 수집 대상

| 사이트 | 수집 데이터 |
| --- | --- |
| Papers With Code | SOTA Ranking |
| MLCommons | MLPerf Benchmark |
| OpenML | Dataset + Experiment |
| EvalAI | AI Challenge 결과 |

Graph:

```
Model
 |
 | evaluated_on
 |
Benchmark
 |
 | achieved
 |
Score
```

예:

```
GPT-5
 |
MMLU
 |
95.2%

DeepSeek
 |
HumanEval
 |
89%
```

---

# 3. GitHub / Open Source Intelligence Layer

AI 연구는 논문보다 GitHub에서 먼저 움직이는 경우가 많습니다.

추가:

| 사이트 | 역할 |
| --- | --- |
| GitHub | 코드 변화 |
| GitHub Trending | 인기 프로젝트 |
| GitHub Archive | 개발 활동 분석 |

수집:

```
Paper

 ↓

GitHub Repo

 ↓

Stars 증가율

 ↓

Adoption Signal
```

---

# 4. AI 기업 Research Blog 추가

현재:

```
OpenAI
Anthropic
DeepMind
DeepSeek
Qwen
Moonshot
Z.ai
MiniMax
```

추가 추천:

| Lab | 이유 |
| --- | --- |
| Microsoft Research | Phi, Copilot 연구 |
| NVIDIA Research | GPU + AI System |
| Meta AI | Llama 연구 |
| Allen Institute for AI | Semantic Scholar 운영, 연구 |
| Google Research | Gemini, TPU 연구 |

---

# 5. AI Conference Tracking Layer

최신 연구 흐름은 학회가 가장 빠릅니다.

## 필수

| Conference | 분야 |
| --- | --- |
| NeurIPS | ML |
| ICML | ML |
| ICLR | Deep Learning |
| ACL | NLP |
| CVPR | Vision |
| AAAI | AI |
| KDD | Data Mining |
| MLSys | AI System |

수집:

```
Conference

 |
Paper

 |
Author

 |
Institution
```

---

# 6. AI 뉴스 / 산업 Intelligence

논문만 보면 시장 흐름을 놓칩니다.

추가:

| 사이트 | 용도 |
| --- | --- |
| MIT Technology Review | AI 산업 분석 |
| The Batch | AI Weekly |
| Import AI | 연구 분석 |
| Ben's Bites | 산업 동향 |

---

# 7. 특허 / 산업화 Tracking

AI 연구 → 제품화 분석용

| 사이트 | 역할 |
| --- | --- |
| Google Patents | AI 특허 |
| USPTO | 미국 특허 |
| WIPO Patentscope | 국제 특허 |

Graph:

```
Research Paper

      |

Technology

      |

Patent

      |

Company Product
```

---

# 8. 모델 Registry 추가

현재:

```
HuggingFace
```

추가:

| 사이트 | 목적 |
| --- | --- |
| ModelScope | 중국 모델 |
| Replicate | 실행 가능한 모델 |
| Ollama | Local LLM |
| LM Studio | Desktop LLM |

---

# 9. 정책 / Regulation Layer 확대

현재:

```
Federal Register
```

추가:

| 기관 | 역할 |
| --- | --- |
| NIST | AI Risk Framework |
| European Commission | EU AI Act |
| OECD AI Policy Observatory | 국제 정책 |
| UNESCO | AI Ethics |

---

# 10. 최종 AI Research Intelligence Source Map

추천 최종 구성:

```
                 AI Intelligence Platform

                    Research Data

 ┌───────────────┬───────────────┬───────────────┐

 Papers          Models          Code

 arXiv           HF              GitHub

 Semantic        ModelScope      Trending

 OpenReview      Ollama

 └───────────────┴───────────────┴───────────────┘

                 Knowledge Graph

 Paper
   |
 Model
   |
 Code
   |
 Benchmark
   |
 Company
   |
 Patent
   |
 Policy

                 Agent

 Daily Research Brief

 Trend Detection

 Market Signal

 Technology Radar
```

---

# 최종 추천 수집 Priority

## Tier 0 (매일)

```
arXiv
HuggingFace
Semantic Scholar
Papers With Code
OpenReview
GitHub Trending
DeepSeek
Qwen
OpenAI
Anthropic
```

## Tier 1 (주간)

```
NeurIPS
ICML
ICLR
CVPR
MLSys

NVIDIA Research
Meta AI
Microsoft Research
Google Research
```

## Tier 2 (월간)

```
Patents
Federal Register
EU AI Act
NIST
Investment News
```

---

현재 설계한 **Rust Collector + Qdrant + Neo4j + LangGraph Agent** 구조라면 최종적으로 약 **40~60개 Source Connector**를 가진 **AI Research OS** 형태까지 확장 가능합니다.