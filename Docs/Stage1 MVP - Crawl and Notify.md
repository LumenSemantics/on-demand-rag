# Stage 1 MVP — Crawl & Notify

> **이 문서 하나가 1단계의 유일한 기준 문서입니다.**
> 기존 로드맵 3종(Stage-Gate / 개발 원칙 및 단계 / 권장 개발 로드맵)과 Architecture v1~v3는
> 2단계 이후를 위한 참고 자료로만 둡니다. 1단계는 이 문서만 따릅니다.

---

## 1. 목표 (한 문장)

**매일 정해진 시간에 AI 연구 소스를 크롤링해서, 새로 올라온 것만 골라, (선택) 한 줄 요약을 붙여 Slack/Email로 알림을 보낸다.**

완성됐을 때의 모습:

> 매일 아침 8시, Slack에 "오늘의 AI 연구 브리핑 — arXiv 신규 논문 12건, HuggingFace 인기 논문 5건" 알림이 자동으로 온다.

---

## 2. 범위 (Scope)

### 1단계에 **포함**되는 것

- 소스 크롤링 (arXiv API, HuggingFace Daily Papers, RSS 몇 개)
- 중복 제거 (이미 보낸 항목은 다시 안 보냄)
- (선택) LLM 한 줄 요약
- Markdown 리포트 생성
- Slack / Email 알림 발송
- 스케줄 실행 (cron 또는 GitHub Actions)

### 1단계에서 **의도적으로 빼는 것** (2단계 이후)

| 빼는 것 | 언제 |
|---|---|
| 벡터 DB (Qdrant) | 2단계 |
| 그래프 DB (Neo4j) | 2단계 |
| 임베딩 / RAG / GraphRAG | 2단계 |
| LangGraph 에이전트 | 3단계 |
| Rust 크롤러 | 2단계(스케일 필요 시) |
| Kafka / NATS / MinIO / Redis | 2단계 이후 |
| Next.js 대시보드 | 4단계 |
| Kubernetes / 인증 / 멀티테넌트 | 5단계 |

> **원칙:** 알림만 하는 단계에는 검색이 필요 없다 → 벡터/그래프 DB도 필요 없다.
> 저장소는 "이미 보낸 것"을 기억하는 **SQLite 한 개**로 충분하다.

---

## 3. 아키텍처 (1단계)

```
        ┌─────────────┐
        │  Scheduler  │  cron / GitHub Actions (매일 07:00)
        └──────┬──────┘
               │
        ┌──────▼──────┐
        │  Collector  │  arXiv · HuggingFace · RSS
        └──────┬──────┘
               │  (원본 항목들)
        ┌──────▼──────┐
        │    Dedup    │  SQLite: 이미 본 id 제외
        └──────┬──────┘
               │  (신규 항목만)
        ┌──────▼──────┐
        │ Summarize   │  (선택) LLM 한 줄 요약
        └──────┬──────┘
               │
        ┌──────▼──────┐
        │   Report    │  Markdown 조립
        └──────┬──────┘
               │
        ┌──────▼──────┐
        │   Notify    │  Slack Webhook / Email(SMTP)
        └─────────────┘
```

DB라고 부를 만한 건 **SQLite(`seen.db`)** 하나뿐입니다. 그마저도 "중복 방지"용입니다.

---

## 4. 기술 스택 (1단계)

| 영역 | 선택 | 이유 |
|---|---|---|
| 언어 | **Python 3.13** | 크롤링·알림 MVP엔 Rust 불필요. 가장 빠르게 가치 도달 |
| 패키지 관리 | **uv** | 빠르고 재현 가능 |
| HTTP | `httpx` | 비동기 지원 |
| HTML/RSS 파싱 | `feedparser`, `beautifulsoup4` | RSS·HTML |
| 저장(중복제거) | **SQLite** (`sqlite3` 표준) | 별도 서버 불필요 |
| 요약 LLM(선택) | OpenAI / Gemini / Anthropic **중 1개** | provider 하나로 확정 |
| 알림 | Slack Incoming Webhook, SMTP | 무료·간단 |
| 스케줄 | cron 또는 GitHub Actions `schedule` | 서버 없어도 GH Actions로 가능 |
| 설정 | `.env` + `config/sources.yaml` | 키/소스 분리 |

> **결정 필요 1건:** 요약 LLM provider 1개 확정.
> 요약을 아예 생략하면(제목·링크만 알림) LLM 키도 필요 없어 **완전 무료**로 돌릴 수 있음.

---

## 5. 폴더 구조

```
arip/
├── README.md
├── pyproject.toml
├── .env.example
├── .gitignore
├── config/
│   └── sources.yaml          # 크롤링할 소스 목록
├── src/arip/
│   ├── __init__.py
│   ├── main.py               # 진입점: 수집→중복제거→요약→리포트→알림
│   ├── config.py             # .env / yaml 로드
│   ├── collectors/
│   │   ├── base.py           # Collector 인터페이스
│   │   ├── arxiv.py          # arXiv API
│   │   ├── huggingface.py    # HF Daily Papers
│   │   └── rss.py            # 범용 RSS
│   ├── store/
│   │   └── dedup.py          # SQLite 중복제거
│   ├── summarize/
│   │   └── llm.py            # (선택) 한 줄 요약
│   ├── report/
│   │   └── builder.py        # Markdown 리포트 조립
│   └── notify/
│       ├── slack.py          # Slack Webhook
│       └── email.py          # SMTP
├── data/
│   └── seen.db               # SQLite (git 제외)
└── tests/
    └── test_dedup.py
```

---

## 6. 데이터 소스 (1단계 최소)

| 소스 | 방식 | 키 필요 | 비고 |
|---|---|---|---|
| arXiv `cs.AI` `cs.CL` `cs.LG` `cs.IR` | **공식 API** (`http://export.arxiv.org/api/query`) | ❌ | 1단계 핵심. robots/ToS 안전 |
| HuggingFace Daily Papers | 페이지/API | 토큰 선택 | 인기 논문 큐레이션 |
| RSS 몇 개 (The Batch, HF Blog 등) | `feedparser` | ❌ | `sources.yaml`에 URL만 추가 |

> **X(트위터)·크롤링 리스크 있는 사이트는 1단계에서 제외.** 공식 API/RSS만 사용.

`config/sources.yaml` 예시:

```yaml
arxiv:
  categories: [cs.AI, cs.CL, cs.LG, cs.IR]
  max_results: 30
huggingface:
  daily_papers: true
rss:
  - name: The Batch
    url: https://www.deeplearning.ai/the-batch/feed/
  - name: HuggingFace Blog
    url: https://huggingface.co/blog/rss.xml
```

---

## 7. 중복 제거 (Dedup)

- SQLite 테이블 `seen(id TEXT PRIMARY KEY, source TEXT, first_seen TIMESTAMP)`
- 항목 고유 id = arXiv ID / 논문 URL / RSS `guid`
- 수집 후 `seen`에 없는 것만 "신규"로 통과 → 알림 발송 후 `seen`에 기록
- 효과: 매일 돌려도 같은 논문을 두 번 알리지 않음

---

## 8. 알림 (Notify)

- **Slack**: Incoming Webhook URL 하나면 됨. Markdown 블록으로 발송.
- **Email(선택)**: SMTP(Gmail 앱 비밀번호 등) 또는 SendGrid.
- 리포트 형식은 기존 `Report Templete` 문서를 간소화해서 사용:
  - 헤더(수집 일시 / 총 건수)
  - arXiv 신규 논문 (제목·요약·링크)
  - HuggingFace 인기 논문
  - RSS 하이라이트

---

## 9. 스케줄 실행

두 가지 중 택1:

**A. 서버/PC에 cron (매일 07:00)**
```bash
0 7 * * * cd /path/to/arip && uv run python -m arip.main >> data/run.log 2>&1
```

**B. GitHub Actions (서버 없이)**
```yaml
# .github/workflows/daily.yml
on:
  schedule:
    - cron: "0 22 * * *"   # UTC 22:00 = KST 07:00
jobs:
  brief:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv run python -m arip.main
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
          LLM_API_KEY: ${{ secrets.LLM_API_KEY }}
```

> GitHub Actions를 쓰면 SQLite 상태가 매 실행마다 초기화되므로, 이때는 dedup 상태를
> 리포지토리 커밋 또는 Actions 캐시/아티팩트로 유지해야 함(또는 B 대신 A 권장).

---

## 10. `.env.example`

```
# ── 알림 (필수 최소 1개) ──
SLACK_WEBHOOK_URL=

# ── Email (선택) ──
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
EMAIL_TO=

# ── 요약 LLM (선택: 생략 시 제목·링크만 알림) ──
LLM_PROVIDER=openai          # openai | gemini | anthropic
LLM_API_KEY=
LLM_MODEL=gpt-4o-mini        # 저비용 모델 권장

# ── 기타 ──
DB_PATH=data/seen.db
```

---

## 11. 실행 방법

```bash
# 1. 의존성 설치
uv sync

# 2. 설정
cp .env.example .env    # 값 채우기
# config/sources.yaml 확인

# 3. 1회 실행 (테스트)
uv run python -m arip.main

# 4. 스케줄 등록 (cron 또는 GitHub Actions)
```

---

## 12. 완료 기준 (Exit Criteria) — 이걸 만족하면 1단계 끝

- [ ] `uv run python -m arip.main` 실행 시 arXiv 신규 논문이 Slack으로 온다
- [ ] 같은 명령을 두 번 실행해도 중복 항목이 다시 오지 않는다 (dedup 동작)
- [ ] cron 또는 GitHub Actions로 매일 자동 실행된다
- [ ] LLM 키 없이도(요약 생략 모드) 정상 동작한다
- [ ] 소스 추가가 `sources.yaml`에 URL 한 줄 넣는 것으로 된다

---

## 13. 필요 준비물 (1단계)

| 준비물 | 필수 | 비용 |
|---|---|---|
| GitHub 저장소 | ✅ | 무료 |
| Python 3.13 + uv | ✅ | 무료 |
| Slack Incoming Webhook | ✅ | 무료 |
| LLM API 키 (요약용) | 선택 | 소액 (생략 시 0원) |
| 서버/PC 또는 GitHub Actions | ✅ | 무료 |

**→ 요약을 생략하면 1단계는 완전 무료로 운영 가능.**

---

## 14. 다음 단계로 넘어가는 신호 (2단계 트리거)

아래가 필요해지면 그때 벡터/그래프 DB를 붙인다:

- "지난주에 나온 MoE 논문 찾아줘" 같은 **과거 검색**이 필요할 때 → Qdrant
- "이 모델을 만든 랩이 낸 다른 논문" 같은 **관계 질의**가 필요할 때 → Neo4j
- 소스가 많아져 Python 크롤러 속도가 부족할 때 → Rust 이관

그 전까지는 1단계로 충분하다.
