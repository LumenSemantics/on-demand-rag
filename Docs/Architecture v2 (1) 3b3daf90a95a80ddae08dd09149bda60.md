# Architecture v2 (1)

#### **Rust(고성능 크롤링) + Python(LLM·데이터 처리) + Qdrant(벡터 검색) + Neo4j(GraphRAG) + Gemini(요약·분석)**를 결합한 확장성과 운영성을 갖춘 연구 플랫폼

---

# AI Research Intelligence Platform v1.0

```
                +-----------------------------+
                |        Scheduler            |
                |  Cron / Temporal / Airflow  |
                +-------------+---------------+
                              |
                              v
                 +---------------------------+
                 |   Rust Web Crawler        |
                 | (Tokio + Reqwest + HTML)  |
                 +-------------+-------------+
                               |
               +---------------+---------------+
               |                               |
               v                               v
        Kafka / NATS                    Object Storage
       (Streaming Queue)            (MinIO / S3 / NAS)
               |
               v
      +-----------------------+
      | Python FastAPI Worker |
      | Document Pipeline     |
      +-----------------------+
               |
               +-------------------------+
               |                         |
               v                         v
      Gemini 2.5 API              Local Embedding
      (Summary / Metadata)        (BGE-M3, Qwen3-Embedding)
               |                         |
               +------------+------------+
                            |
                            v
                    Chunking Engine
                            |
          +-----------------+------------------+
          |                                    |
          v                                    v
      Qdrant VectorDB                  Neo4j GraphDB
     Semantic Search              Citation / Author / Topic
          |                                    |
          +-----------------+------------------+
                            |
                            v
                 GraphRAG Retrieval Layer
                            |
                            v
                 FastAPI Research API
                            |
          +-----------------+------------------+
          |                                    |
          v                                    v
      Web UI (Next.js)                 MCP Server
```

---

# 프로젝트 구조

```
ai-research-platform/

├── crawler/
│   ├── rust/
│   │   ├── src/
│   │   ├── Cargo.toml
│   │   └── Dockerfile
│   │
│   └── config/
│       └── sources.yaml
│
├── pipeline/
│   ├── app/
│   │   ├── chunking/
│   │   ├── embedding/
│   │   ├── gemini/
│   │   ├── graph/
│   │   ├── vector/
│   │   └── api/
│   │
│   ├── requirements.txt
│   └── Dockerfile
│
├── docker/
│   ├── qdrant/
│   ├── neo4j/
│   ├── kafka/
│   ├── minio/
│   └── prometheus/
│
├── docker-compose.yml
│
├── .env
├── .env.example
└── README.md
```

---

# Rust Web Crawler

추천 라이브러리

```toml
tokio
reqwest
scraper
select
serde
serde_json
chrono
regex
url
governor
tracing
```

Crawler Flow

```
URL Queue

↓

Fetch

↓

HTML Parser

↓

Extract

↓

Normalize

↓

Duplicate Check

↓

Kafka

↓

Next URL
```

---

# FastAPI Pipeline

```
POST /ingest

↓

Cleaning

↓

Chunking

↓

Gemini Summary

↓

Embedding

↓

Knowledge Graph

↓

Qdrant

↓

Neo4j
```

---

# Gemini 활용

Gemini는 **생성 모델**로 사용하고, 임베딩은 별도 모델을 사용하는 구성을 권장합니다.

### 사용하는 작업

- 논문 요약
- 핵심 기여점 추출
- Novelty 분석
- 연구 분야 분류
- 키워드 생성
- 태그 생성
- Citation Summary
- Research Trend 분석

사용하지 않는 작업

- Vector Embedding
- Similarity Search

---

# .env

```
####################
# Gemini
####################

GEMINI_API_KEY=

####################
# Neo4j
####################

NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

####################
# Qdrant
####################

QDRANT_URL=http://qdrant:6333

####################
# Kafka
####################

KAFKA_BOOTSTRAP_SERVERS=kafka:9092

####################
# MinIO
####################

MINIO_ENDPOINT=minio:9000

####################
# Embedding
####################

EMBEDDING_MODEL=BAAI/bge-m3

####################
# Gemini
####################

LLM_MODEL=gemini-2.5-pro
```

---

# Docker Compose

```yaml
services:

  crawler:
    build: ./crawler/rust

  pipeline:
    build: ./pipeline

  qdrant:
    image: qdrant/qdrant

  neo4j:
    image: neo4j:latest

  kafka:
    image: apache/kafka

  minio:
    image: minio/minio

  prometheus:
    image: prom/prometheus

  grafana:
    image: grafana/grafana
```

---

# Rate Limit 대응

Rust에서는 **governor** 또는 **tower** 기반 Rate Limiter를 권장합니다.

```
Request

↓

Rate Limiter

↓

Retry

↓

Exponential Backoff

↓

Circuit Breaker
```

권장 정책:

- 초당 요청 제한(RPS) 적용
- 지수 백오프(Exponential Backoff)
- `Retry-After` 헤더 존중
- 요청 타임아웃 설정
- Circuit Breaker로 연속 실패 차단

---

# 캐시

```
Gemini Request

↓

Redis Cache

↓

Hit?

YES → Return

NO

↓

Gemini API

↓

Redis 저장
```

효과:

- API 비용 절감
- 응답 속도 향상
- 동일 논문 재처리 방지

---

# GraphRAG

Neo4j 노드 예시

```
Paper

Author

Institution

Model

Dataset

Task

Method

Evaluation

Conference

Organization

Repository
```

관계 예시

```
Author
    |
WROTE
    |
Paper
    |
USES
    |
Dataset

Paper
    |
PROPOSES
    |
Method

Paper
    |
EVALUATED_ON
    |
Benchmark

Paper
    |
IMPLEMENTED_AS
    |
GitHub Repository
```

---

# 추천 임베딩 모델

| 용도 | 모델 |
| --- | --- |
| 논문 검색 | BAAI BGE-M3 |
| 멀티링구얼 | Qwen3-Embedding |
| GraphRAG | BGE-M3 |
| 재순위화 | BGE-Reranker-v2 |
| 경량 환경 | Nomic Embed |

---

# 모니터링

```
Prometheus

↓

Grafana

↓

Loki

↓

Tempo

↓

OpenTelemetry
```

모니터링 항목:

- 크롤링 성공률
- API 응답 시간
- Gemini 호출 횟수
- 토큰 사용량
- Qdrant 검색 지연
- Neo4j 쿼리 시간
- Kafka 큐 적체
- FastAPI TPS
- GPU 사용률
- 메모리 및 디스크 사용량

---

## 현재 프로젝트에 맞는 확장 방향

사용자의 AI Research Intelligence Platform 목표를 고려하면 다음 기술을 추가하면 완성도가 더욱 높아집니다.

- **워크플로 오케스트레이션**: `Temporal`(복잡한 장기 워크플로) 또는 `Apache Airflow`(배치 중심)
- **객체 저장소**: `MinIO`를 원본 PDF와 파싱 결과 저장소로 활용
- **문서 파싱**: `LlamaParse`, `Docling`, `Marker`를 조합하여 PDF 품질 향상
- **재순위화(Reranking)**: `BGE-Reranker-v2`를 Qdrant 검색 후 적용
- **관측성(Observability)**: `OpenTelemetry` 기반으로 Rust 크롤러와 FastAPI를 함께 추적
- **MCP Server**: IDE, Claude Desktop, VS Code 등과 연동 가능한 연구 데이터 인터페이스 제공