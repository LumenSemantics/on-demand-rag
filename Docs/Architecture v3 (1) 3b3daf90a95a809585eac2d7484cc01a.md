# Architecture v3 (1)

## 1. GitHub Monorepo 구조

Yarn Berry 또는 Turborepo 기반의 고성능 모노레포 레이아웃입니다.

Plaintext

# 

```
my-ai-monorepo/
├── .github/workflows/         # CI/CD 파이프라인 (Lint, Test, Build)
├── apps/
│   ├── collector-rust/        # 고성능 데이터 수집 및 청킹 파이프라인 (Rust)
│   └── agent-service/         # LangGraph 기반 오케스트레이션 서버 (Python/FastAPI)
├── packages/
│   ├── db-schemas/            # Qdrant 컬렉션 및 Neo4j Cypher 마이그레이션 스크립트
│   └── shared-types/          # 공통 타입 정의 (Protocol Buffers / JSON Schema)
├── docker-compose.yml         # 전체 인프라 및 서비스 통합 구동
├── package.json
└── turbo.json
```

## 2. Docker Compose (`docker-compose.yml`)

Qdrant(벡터 저장소), Neo4j(그래프 DB), 그리고 Rust 수집기와 LangGraph 에이전트 서비스를 한 번에 관리합니다.

YAML

# 

```
version: '3.8'

services:
  qdrant:
    image: qdrant/qdrant:latest
    container_name: ai_qdrant
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage
    environment:
      - QDRANT__SERVICE__HTTP_PORT=6333

  neo4j:
    image: neo4j:5.15.0
    container_name: ai_neo4j
    ports:
      - "7474:7474" # HTTP Browser
      - "7687:7687" # Bolt Protocol
    environment:
      - NEO4J_AUTH=neo4j/securepassword123
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs

  collector:
    build:
      context: ./apps/collector-rust
      dockerfile: Dockerfile
    container_name: ai_collector
    environment:
      - QDRANT_URL=http://qdrant:6333
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=securepassword123
    depends_on:
      - qdrant
      - neo4j

  agent-service:
    build:
      context: ./apps/agent-service
      dockerfile: Dockerfile
    container_name: ai_agent_service
    ports:
      - "8000:8000"
    environment:
      - QDRANT_URL=http://qdrant:6333
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=securepassword123
      - OPENAI_API_KEY=your_openai_api_key_here
    depends_on:
      - qdrant
      - neo4j

volumes:
  qdrant_data:
  neo4j_data:
  neo4j_logs:
```

## 3. Rust Collector 코드 (`apps/collector-rust`)

문서를 비동기로 수집하고 정제하여 Qdrant와 Neo4j에 각각 적재하는 경량화된 Rust 백엔드 스니펫입니다.

Rust

# 

```
// Cargo.toml dependencies (snippet):
// tokio = { version = "1.0", features = ["full"] }, reqwest = "0.11", serde = { version = "1.0", features = ["derive"] }

use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, Debug)]
pub struct DocumentChunk {
    pub id: String,
    pub content: String,
    pub embedding: Vec<f32>,
    pub entities: Vec<String>,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("Starting Rust High-Performance Collector...");

    // 1. 문서 크롤링 및 청킹 시뮬레이션
    let chunk = DocumentChunk {
        id: "doc_uuid_001".to_string(),
        content: "LangGraph enables building robust stateful multi-agent applications.".to_string(),
        embedding: vec![0.12; 1536], // OpenAI embedding dimension size mock
        entities: vec!["LangGraph".to_string(), "Multi-Agent".to_string()],
    };

    // 2. Qdrant 벡터 적재 (HTTP Client 활용 예시)
    let client = reqwest::Client::new();
    let qdrant_payload = serde_json::json!({
        "points": [{
            "id": chunk.id,
            "vector": chunk.embedding,
            "payload": { "text": chunk.content }
        }]
    });

    let _res = client
        .put("http://localhost:6333/collections/documents/points")
        .json(&qdrant_payload)
        .send()
        .await?;

    println!("Successfully pushed vector chunk to Qdrant.");
    Ok.unwrap_or(());
    Ok(())
}
```

## 4. Qdrant / Neo4j Schema 설계

### Qdrant Collection Schema (`documents`)

- **Vector Dimension**: `1536` (OpenAI `text-embedding-3-small` 기준)
- **Distance Metric**: `Cosine`
- **Payload Indexing**: `text` (Text match 검색용), `source_id` (메타데이터 필터링용)

### Neo4j Cypher Schema (Knowledge Graph)

Cypher

# 

```
// 제약 조건(Constraints) 및 인덱스 설정
CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS
FOR (c:Chunk) REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT entity_name_unique IF NOT EXISTS
FOR (e:Entity) REQUIRE e.name IS UNIQUE;

// 관계 구조 예시: (Chunk)-[:MENTIONS]->(Entity), (Entity)-[:RELATED_TO]->(Entity)
```

## 5. LangGraph Agent 코드 (`apps/agent-service`)

Qdrant의 벡터 검색과 Neo4j의 그래프 탐색 결과를 결합하여 답변을 생성하는 LangGraph 상태 기반 에이전트 코드입니다.

Python

# 

```
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from qdrant_client import QdrantClient
from neo4j import GraphDatabase

# 1. State 정의
class AgentState(TypedDict):
    query: str
    context_chunks: List[str]
    graph_relations: List[str]
    answer: str

# 클라이언트 초기화
qdrant_client = QdrantClient(url="http://localhost:6333")
neo4j_driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "securepassword123"))

# 2. 노드 함수 정의: Hybrid Retrieval (Qdrant + Neo4j)
def retrieve_node(state: AgentState) -> AgentState:
    query = state["query"]

    # Qdrant 벡터 검색 시뮬레이션
    # hits = qdrant_client.search(collection_name="documents", query_vector=get_embedding(query), limit=3)
    retrieved_texts = ["LangGraph coordinates complex agent workflows with built-in memory."]

    # Neo4j 그래프 탐색 시뮬레이션
    with neo4j_driver.session() as session:
        result = session.run("MATCH (e:Entity {name: 'LangGraph'})-[:RELATED_TO]->(o) RETURN o.name LIMIT 5")
        relations = [record["o"] for record in result] if result else ["Multi-Agent System"]

    state["context_chunks"] = retrieved_texts
    state["graph_relations"] = relations
    return state

# 3. 노드 함수 정의: LLM 응답 생성
def generate_node(state: AgentState) -> AgentState:
    context = "\n".join(state["context_chunks"])
    relations = ", ".join(state["graph_relations"])

    # 프롬프트 조합 및 LLM 호출 로직 (생략)
    state["answer"] = f"Based on vector context [{context}] and graph links [{relations}], here is the synthesized answer."
    return state

# 4. LangGraph 워크플로우 조립
workflow = StateGraph(AgentState)
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("generate", generate_node)

workflow.set_entry_point("retrieve")
workflow.add_edge("retrieve", "generate")
workflow.add_edge("generate", END)

app = workflow.compile()
```

[Building Modular AI Agents with LangGraph, MCP, and Neo4j](https://www.youtube.com/watch?v=rMXz_Upv1Dw)

이 영상은 LangGraph와 Neo4j를 연동하여 모듈형 AI 에이전트 파이프라인을 구축하는 실무 아키텍처를 시각적으로 이해하는 데 유용합니다.