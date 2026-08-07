# AIRP — AI Research Intelligence Platform

[![CI](https://github.com/LumenSemantics/on-demand-rag/actions/workflows/ci.yml/badge.svg)](https://github.com/LumenSemantics/on-demand-rag/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)

AI 연구 동향(논문·모델·블로그·정책)을 자동 수집하고, 지식 그래프와 GraphRAG로 분석·요약해
매일 리서치 브리핑을 만들어 주는 플랫폼입니다.

> 이 저장소는 **단계(Stage)별로** 점진적으로 구축합니다.
> 현재 **Stage 1~3 구현 완료** — 크롤·알림 + 지식계층(Qdrant·Neo4j·GraphRAG) + LangGraph 에이전트.
> 웹 UI는 **Google Cloud Run(서울)** 에 배포되어 있습니다.
>
> 🌐 **라이브:** https://airp-105639816783.asia-northeast3.run.app (검색 · AI 질문 · 트렌드 · 그래프)

---

## 단계 로드맵

| 단계 | 이름 | 핵심 가치 | 추가되는 것 | 상태 |
|---|---|---|---|---|
| **1** | **Crawl & Notify** | 매일 AI 소식이 알림으로 온다 | 크롤러 · 중복제거 · 요약 · 알림 | ✅ **완료** |
| **2** | **Knowledge** | 모은 걸 검색·질의한다 | 임베딩 · **Qdrant** · **Neo4j** · GraphRAG · 검색 API | ✅ **완료** |
| **3** | **Intelligence** | 트렌드·심층 분석 | LangGraph 에이전트 · 트렌드 감지 · 주간 다이제스트 | ✅ **완료** |
| 4 | Application | 웹에서 본다 | FastAPI 웹 UI + **Cloud Run 배포** (Next.js·MCP 예정) | 🟡 부분 |
| 5 | Enterprise | 다중 사용자·운영 | K8s · 인증 · 멀티테넌트 · 모니터링 | ⬜ 예정 |

📚 문서: **[프로젝트 개요](Docs/AIRP%20%ED%94%84%EB%A1%9C%EC%A0%9D%ED%8A%B8%20%EA%B0%9C%EC%9A%94.md)** (비전·아키텍처·소스·스택·로드맵) · [Stage 1 스펙](Docs/Stage1%20MVP%20-%20Crawl%20and%20Notify.md) · [ERD](Docs/ERD.md) · [문서 색인](Docs)

🏛️ 설계·기록: **[아키텍처 & 데이터 흐름](Docs/AIRP-%EC%95%84%ED%82%A4%ED%85%8D%EC%B2%98.md)** ([PDF](Docs/AIRP-%EC%95%84%ED%82%A4%ED%85%8D%EC%B2%98.pdf)) · **[시행착오 · 트러블슈팅](Docs/%EC%8B%9C%ED%96%89%EC%B0%A9%EC%98%A4-%ED%8A%B8%EB%9F%AC%EB%B8%94%EC%8A%88%ED%8C%85.md)**

---

## Stage 1 — Crawl & Notify

**매일 AI 소스를 크롤링 → 새 항목만 골라 → (선택) 한 줄 요약 → Slack/Email 알림.**

```
Scheduler → Collector(arXiv·HuggingFace·RSS) → Dedup(SQLite) → (요약) → Report → Notify(Slack/Email)
```

벡터 DB·그래프 DB·RAG·에이전트는 이 단계에 **없습니다**(Stage 2 이후). 저장소는 중복 방지용 SQLite 하나뿐입니다.

### 요구사항

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- (선택) 요약용 LLM API 키 1개 — 없으면 제목·링크만 알림(완전 무료)
- (선택) Slack Incoming Webhook

### 빠른 시작

```bash
# 1. 의존성 설치
uv sync

# 2. 설정
cp .env.example .env        # 값 채우기 (Windows: copy .env.example .env)

# 3. 발송 없이 콘솔에서 결과만 확인 (권장 첫 실행)
uv run airp --dry-run

# 4. 실제 실행 (Slack/Email로 발송)
uv run airp
```

### 자주 쓰는 옵션

| 명령 | 설명 |
|---|---|
| `uv run airp --dry-run` | 알림 발송·seen 기록 없이 리포트만 콘솔 출력 |
| `uv run airp --no-summary` | LLM 요약 건너뛰기 |
| `uv run airp --limit-summary 5` | 요약할 항목 수 제한(비용 절감) |

### 소스 추가

[`config/sources.yaml`](config/sources.yaml)에 RSS 항목을 한 줄 추가하면 됩니다.

```yaml
rss:
  - name: My Feed
    url: https://example.com/feed.xml
    limit: 10
```

### 볼륨 조절 · 필터

같은 파일의 `filter` 섹션으로 브리핑 양을 조절합니다 (제목+초록 기준, 대소문자 무시):

```yaml
filter:
  include: [rag, agent, llm]   # 이 중 하나라도 있어야 통과 (비면 전체)
  exclude: [robotics]          # 걸리면 제외
  max_per_source: 10           # 소스마다 최대 N건 (HuggingFace는 upvotes 높은 순)
```

상한으로 잘린 항목도 "본 것"으로 기록되어 다음날 다시 알림되지 않습니다.

### 카탈로그 분류

브리핑을 AI 주제(에이전트·RAG·추론·멀티모달·안전·정책 …)로 묶습니다.

```yaml
report:
  group_by: category   # category(주제별) | source(소스별)
  classify: llm        # llm(정확, LLM 키 필요) | keyword(무료, 규칙)
```

`classify: llm`인데 LLM 키가 없으면 자동으로 `keyword`로 폴백합니다.
CLI로도 덮어쓸 수 있습니다: `uv run airp --group-by source --classify keyword`

### 매일 자동 실행

**cron (매일 07:00):**
```bash
0 7 * * * cd /path/to/airp && uv run airp >> data/run.log 2>&1
```

**GitHub Actions:** `.github/workflows/`에 스케줄 워크플로 추가 (Stage 1 문서 §9 참고).

### 테스트

```bash
uv run --extra dev pytest
```

---

## Stage 2~3 — 지식 계층 & 웹 UI

수집한 문서를 **Qdrant(벡터) + Neo4j(그래프)** 에 색인하고, GraphRAG 검색·LangGraph 에이전트로 질의합니다.

```bash
# 의존성 (지식계층 + 웹 API)
uv sync --extra api

# .env 에 클라우드 자격증명 추가:
#   QDRANT_URL / QDRANT_API_KEY / NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD / LLM_API_KEY

uv run airp-kb check           # 클라우드 연결 확인
uv run airp-kb index           # 최근 브리핑을 Qdrant/Neo4j에 색인
uv run airp-kb search "효율적인 LLM 추론"   # 벡터 + 그래프 검색
uv run airp-kb ask "최근 LLM 효율화 동향"    # LangGraph 에이전트(인용 답변)
uv run airp-kb trends          # 카테고리 급상승 트렌드
uv run airp-kb weekly          # 주간 다이제스트

uv run airp-api                # 웹 UI 서버 → http://127.0.0.1:8000
```

일일 배치(`airp`)는 실행 시 신규 항목을 자동으로 색인하고 리포트에 트렌드 섹션을 넣습니다.

### 배포 (Google Cloud Run)

웹 UI는 서울 리전 Cloud Run에 배포되어 있습니다 → **https://airp-105639816783.asia-northeast3.run.app**
컨테이너·배포 절차는 [Cloud Run 배포 가이드](Docs/Cloud%20Run%20%EB%B0%B0%ED%8F%AC.md)를 참고하세요. GitHub `main`에 push하면 Cloud Build가 자동 재배포합니다.

> 역할 분리: **GitHub Actions**가 매일 지식계층에 *쓰고*, **Cloud Run** 웹 UI가 실시간으로 *읽습니다*. → [아키텍처 다이어그램](Docs/AIRP-%EC%95%84%ED%82%A4%ED%85%8D%EC%B2%98.md)

---

## 프로젝트 구조

```
airp/
├── main.py            # 진입점: 수집→중복제거→요약→색인→트렌드→알림
├── config.py          # .env / sources.yaml 로드
├── collectors/        # arxiv, huggingface, rss
├── store/dedup.py     # SQLite 중복 제거
├── summarize/llm.py   # (선택) 한 줄 요약 (openai/anthropic/gemini)
├── catalog.py         # 카탈로그 분류 (keyword / llm)
├── report/builder.py  # Markdown 리포트 · 다이제스트
├── notify/            # slack, email, kakao
├── knowledge/         # Stage 2~3: embed · store(Qdrant) · graph(Neo4j)
│                      #   · trends · agent(LangGraph) · cli(airp-kb)
└── api/app.py         # Stage 2~3: FastAPI 웹 UI (airp-api)
```

주요 진입점(스크립트): `airp`(배치) · `airp-kb`(지식 CLI) · `airp-api`(웹 UI).

---

## 기여

기여를 환영합니다. [CONTRIBUTING.md](CONTRIBUTING.md)를 참고하세요.
버그·제안은 [이슈](https://github.com/LumenSemantics/on-demand-rag/issues)로 남겨주세요.
참여 시 [행동 규범](CODE_OF_CONDUCT.md)을 따릅니다.

## 라이선스

[MIT](LICENSE) © 2026 LumenSemantics
