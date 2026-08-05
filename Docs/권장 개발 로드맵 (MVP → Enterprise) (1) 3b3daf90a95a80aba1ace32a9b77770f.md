# 권장 개발 로드맵 (MVP → Enterprise) (1)

### Phase 1. 프로젝트 기반 구축 (약 1주)

목표: 모든 서비스가 Docker에서 기동되고 서로 통신하는 상태

- GitHub Monorepo 생성
- Docker Compose
- Rust Workspace
- Python Workspace (uv 기반)
- 환경설정(.env)
- 공통 Config
- CI(GitHub Actions)
- 개발 문서

결과:

```
docker compose up

↓

Kafka
Neo4j
Qdrant
Redis
MinIO
FastAPI

모두 실행
```

---

### Phase 2. Rust Collector MVP

목표: 실제 데이터를 수집

구현 대상:

- arXiv
- Hugging Face Papers
- OpenAI
- Anthropic
- DeepSeek

이후 Plugin 구조로

```
Collector Plugin

trait Collector

↓

ArxivCollector

↓

HFPaperCollector

↓

DeepSeekCollector
```

확장됩니다.

---

### Phase 3. AI Pipeline

Python에서

```
Raw HTML

↓

Parser

↓

Chunk

↓

Embedding

↓

Qdrant 저장
```

까지 구현합니다.

---

### Phase 4. Knowledge Graph

Neo4j에

```
Paper

↓

Model

↓

Lab

↓

Technology

↓

Researcher
```

를 생성합니다.

---

### Phase 5. LangGraph Agent

Planner

↓

Retriever

↓

Graph Search

↓

Reasoning

↓

Report

---

### Phase 6. Daily Intelligence

매일

```
02:00 Crawl

04:00 Embedding

05:00 Graph Update

06:00 Trend Analysis

07:00 Report

08:00 Slack

08:05 Notion

08:10 Email
```

---

# 저는 이렇게 개발하겠습니다.

실제 오픈소스 프로젝트 수준으로 아래 순서대로 작성합니다.

## STEP 1 (Repository)

```
GitHub Monorepo

README

LICENSE

Architecture

Docker

CI

Coding Convention
```

---

## STEP 2

```
docker-compose.yml

Neo4j

Qdrant

Kafka

Redis

MinIO

FastAPI

Rust Collector
```

---

## STEP 3

Rust

```
Collector Framework

Scheduler

Retry

Queue

Plugin System
```

---

## STEP 4

Python

```
Embedding Pipeline

RAG

Graph Builder
```

---

## STEP 5

LangGraph

```
Planner

Search

Reasoner

Report
```

---

## STEP 6

Report Bot

```
Slack

Notion

Email

Markdown

PDF
```

---

# 제가 추가하고 싶은 기능

현재 설계에서 한 단계 더 발전시키면 차별성이 커집니다.

### 1. Event-driven Architecture

Kafka를 중심으로 모든 처리를 이벤트 기반으로 구성합니다.

```
Crawler

↓

Kafka

↓

Parser

↓

Embedding

↓

Graph Builder

↓

Trend Detector

↓

Report Generator
```

서비스 간 결합도가 낮아지고, Connector를 수십 개까지 쉽게 확장할 수 있습니다.

---

### 2. Plugin SDK

새로운 수집 대상을 추가할 때 코드를 거의 수정하지 않도록 합니다.

예를 들어 `OpenAICollector`, `MetaCollector`, `GitHubCollector`를 동일한 인터페이스로 구현할 수 있습니다.

---

### 3. Ontology-first Graph

Neo4j에 단순 노드가 아니라 AI 연구용 온톨로지를 정의합니다.

```
Paper

Researcher

Institution

Model

Technique

Dataset

Benchmark

License

Patent

Policy
```

GraphRAG 품질이 크게 향상됩니다.

---

### 4. Trend Detection

단순 요약이 아니라

- 새로운 기술 등장
- Citation 급증
- GitHub Star 증가
- 모델 릴리스 주기
- 연구기관 협업

등을 자동 감지하는 기능을 추가합니다.

---

### 5. MCP Server

향후 다른 AI Agent에서도 사용할 수 있도록

```
Research MCP Server
```

를 별도 서비스로 분리합니다.

---

## 제안하는 진행 방식

이 프로젝트는 규모가 크므로 **시리즈 형태**로 개발하는 것이 적합합니다.

1. **Repository + Docker + CI**
2. **Rust Collector Framework**
3. **Qdrant + Neo4j Schema**
4. **Python AI Pipeline**
5. **LangGraph Research Agent**
6. **Daily Report Bot**
7. **Web Dashboard (Next.js + FastAPI)**
8. **MCP Server**
9. **Kubernetes 배포**
10. **Enterprise 운영 기능**

이 순서대로 구현하면 최종적으로 GitHub에 공개 가능한 수준의 **AI Research Intelligence Platform**을 완성할 수 있습니다.