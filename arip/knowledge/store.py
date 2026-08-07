from __future__ import annotations

import uuid
from collections.abc import Sequence

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from ..collectors.base import Item

COLLECTION = "documents"
# 문자열 id(arXiv URL 등)를 Qdrant point id(UUID)로 결정적으로 변환하기 위한 네임스페이스
_NS = uuid.UUID("6f1a0000-0000-4000-8000-000000000001")


def get_client(url: str, api_key: str) -> QdrantClient:
    """Qdrant Cloud 클라이언트."""
    return QdrantClient(url=url, api_key=api_key or None)


def ensure_collection(qc: QdrantClient, dim: int) -> None:
    """컬렉션이 없으면 생성(코사인 거리)."""
    if not qc.collection_exists(COLLECTION):
        qc.create_collection(COLLECTION, vectors_config=VectorParams(size=dim, distance=Distance.COSINE))


def point_id(item_id: str) -> str:
    return str(uuid.uuid5(_NS, item_id))


def index(qc: QdrantClient, items: Sequence[Item], vectors: Sequence[Sequence[float]]) -> int:
    """항목+벡터를 upsert(멱등)한다. 반환: 저장 건수."""
    points = [
        PointStruct(
            id=point_id(it.id),
            vector=list(v),
            payload={
                "doc_id": it.id,
                "title": it.title,
                "title_ko": it.title_ko,
                "url": it.url,
                "source": it.source,
                "category": it.category,
                "summary": it.summary,
                "published": it.published,
            },
        )
        for it, v in zip(items, vectors)
    ]
    if points:
        qc.upsert(COLLECTION, points=points)
    return len(points)


def search(qc: QdrantClient, query_vector: Sequence[float], limit: int = 5):
    """쿼리 벡터로 유사 문서 검색."""
    return qc.query_points(COLLECTION, query=list(query_vector), limit=limit).points
