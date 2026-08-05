# ARIP — AI Research Intelligence Platform

[![CI](https://github.com/LumenSemantics/on-demand-rag/actions/workflows/ci.yml/badge.svg)](https://github.com/LumenSemantics/on-demand-rag/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)

AI 연구 동향(논문·모델·블로그·정책)을 자동 수집하고, 지식 그래프와 GraphRAG로 분석·요약해
매일 리서치 브리핑을 만들어 주는 플랫폼입니다.

> 이 저장소는 **단계(Stage)별로** 점진적으로 구축합니다.
> 현재 구현 범위는 **Stage 1 (Crawl & Notify)** 입니다.

---

## 단계 로드맵

| 단계 | 이름 | 핵심 가치 | 추가되는 것 | 상태 |
|---|---|---|---|---|
| **1** | **Crawl & Notify** | 매일 AI 소식이 알림으로 온다 | 크롤러 · 중복제거 · 요약 · 알림 | ✅ **구현 중** |
| 2 | Knowledge | 모은 걸 검색·질의한다 | 임베딩 · **Qdrant** · **Neo4j** · GraphRAG · 검색 API | ⬜ 예정 |
| 3 | Intelligence | 트렌드·심층 분석 | LangGraph 에이전트 · 트렌드 감지 | ⬜ 예정 |
| 4 | Application | 웹에서 본다 | Next.js 대시보드 · MCP 서버 | ⬜ 예정 |
| 5 | Enterprise | 다중 사용자·운영 | K8s · 인증 · 멀티테넌트 · 모니터링 | ⬜ 예정 |

자세한 기획·아키텍처 문서는 [`Docs/`](Docs) 참고.
Stage 1 상세 스펙: [`Docs/Stage1 MVP - Crawl and Notify.md`](Docs/Stage1%20MVP%20-%20Crawl%20and%20Notify.md)

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
uv run arip --dry-run

# 4. 실제 실행 (Slack/Email로 발송)
uv run arip
```

### 자주 쓰는 옵션

| 명령 | 설명 |
|---|---|
| `uv run arip --dry-run` | 알림 발송·seen 기록 없이 리포트만 콘솔 출력 |
| `uv run arip --no-summary` | LLM 요약 건너뛰기 |
| `uv run arip --limit-summary 5` | 요약할 항목 수 제한(비용 절감) |

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
CLI로도 덮어쓸 수 있습니다: `uv run arip --group-by source --classify keyword`

### 매일 자동 실행

**cron (매일 07:00):**
```bash
0 7 * * * cd /path/to/arip && uv run arip >> data/run.log 2>&1
```

**GitHub Actions:** `.github/workflows/`에 스케줄 워크플로 추가 (Stage 1 문서 §9 참고).

### 테스트

```bash
uv run --extra dev pytest
```

---

## 프로젝트 구조 (Stage 1)

```
arip/
├── main.py            # 진입점: 수집→중복제거→요약→리포트→알림
├── config.py          # .env / sources.yaml 로드
├── collectors/        # arxiv, huggingface, rss
├── store/dedup.py     # SQLite 중복 제거
├── summarize/llm.py   # (선택) 한 줄 요약 (openai/anthropic/gemini)
├── report/builder.py  # Markdown 리포트
└── notify/            # slack, email
```

---

## 기여

기여를 환영합니다. [CONTRIBUTING.md](CONTRIBUTING.md)를 참고하세요.
버그·제안은 [이슈](https://github.com/LumenSemantics/on-demand-rag/issues)로 남겨주세요.
참여 시 [행동 규범](CODE_OF_CONDUCT.md)을 따릅니다.

## 라이선스

[MIT](LICENSE) © 2026 LumenSemantics
