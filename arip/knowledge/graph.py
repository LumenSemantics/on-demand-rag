from __future__ import annotations

import os
from collections.abc import Sequence

import certifi
from neo4j import Driver, GraphDatabase

from ..collectors.base import Item

# Windows 파이썬의 기본 SSL 컨텍스트에 CA가 비어 있어 Aura(neo4j+s) 인증서 검증이
# "self-signed certificate in certificate chain"으로 실패하는 경우가 있다.
# httpx가 쓰는 certifi CA 번들을 지정해 해결한다(이미 설정돼 있으면 존중).
os.environ.setdefault("SSL_CERT_FILE", certifi.where())

# Document 중심 온톨로지: Document-[FROM]->Source, -[HAS_CATEGORY]->Category, Author-[AUTHORED]->Document
_MERGE = """
MERGE (d:Document {id: $id})
  SET d.title = $title, d.title_ko = $title_ko, d.url = $url,
      d.summary = $summary, d.published = $published
MERGE (s:Source {name: $source})
MERGE (d)-[:FROM]->(s)
FOREACH (_ IN CASE WHEN $category <> '' THEN [1] ELSE [] END |
  MERGE (c:Category {label: $category})
  MERGE (d)-[:HAS_CATEGORY]->(c)
)
FOREACH (name IN $authors |
  MERGE (a:Author {name: name})
  MERGE (a)-[:AUTHORED]->(d)
)
"""


def get_driver(uri: str, user: str, password: str) -> Driver:
    """Neo4j Aura 드라이버."""
    return GraphDatabase.driver(uri, auth=(user, password))


def ensure_constraints(driver: Driver) -> None:
    with driver.session() as session:
        session.run("CREATE CONSTRAINT doc_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE")
        session.run("CREATE CONSTRAINT source_name IF NOT EXISTS FOR (s:Source) REQUIRE s.name IS UNIQUE")


def index(driver: Driver, items: Sequence[Item]) -> int:
    """항목들을 그래프에 MERGE(멱등)한다. 반환: 처리 건수."""
    n = 0
    with driver.session() as session:
        for it in items:
            session.run(
                _MERGE,
                id=it.id,
                title=it.title,
                title_ko=it.title_ko,
                url=it.url,
                summary=it.summary,
                published=it.published,
                source=it.source,
                category=it.category or "",
                authors=[a for a in (it.authors or []) if a],
            )
            n += 1
    return n


# 같은 카테고리 또는 같은 저자를 공유하는 다른 문서를, 공유 수가 많은 순으로.
# title_ko는 번역 안 된 문서에서 ""(빈 문자열)이라 coalesce가 안 먹혀 CASE로 처리.
_TITLE = "CASE WHEN o.title_ko <> '' THEN o.title_ko ELSE o.title END"

_RELATED = f"""
MATCH (d:Document {{id: $id}})-[:HAS_CATEGORY|AUTHORED]-(x)-[:HAS_CATEGORY|AUTHORED]-(o:Document)
WHERE o.id <> d.id
RETURN o.id AS id, {_TITLE} AS title, o.url AS url, count(DISTINCT x) AS shared
ORDER BY shared DESC
LIMIT $limit
"""

_BY_AUTHOR = f"""
MATCH (d:Document {{id: $id}})<-[:AUTHORED]-(a:Author)-[:AUTHORED]->(o:Document)
WHERE o.id <> d.id
RETURN DISTINCT o.id AS id, {_TITLE} AS title, o.url AS url,
       collect(DISTINCT a.name)[0] AS author
LIMIT $limit
"""


def related_docs(driver: Driver, doc_id: str, limit: int = 8) -> list[dict]:
    """카테고리/저자를 공유하는 관련 문서(공유 수 내림차순)."""
    with driver.session() as session:
        return [dict(r) for r in session.run(_RELATED, id=doc_id, limit=limit)]


def by_author(driver: Driver, doc_id: str, limit: int = 8) -> list[dict]:
    """같은 저자의 다른 문서."""
    with driver.session() as session:
        return [dict(r) for r in session.run(_BY_AUTHOR, id=doc_id, limit=limit)]


_NEIGHBORHOOD = f"""
MATCH (d:Document {{id: $id}})
OPTIONAL MATCH (d)-[:HAS_CATEGORY]->(c:Category)
OPTIONAL MATCH (d)<-[:AUTHORED]-(a:Author)
WITH d, collect(DISTINCT c.label) AS cats, collect(DISTINCT a.name)[..5] AS authors
OPTIONAL MATCH (d)-[:HAS_CATEGORY|AUTHORED]-()-[:HAS_CATEGORY|AUTHORED]-(o:Document)
WHERE o.id <> d.id
WITH d, cats, authors,
     collect(DISTINCT {{id: o.id, title: {_TITLE}}})[..6] AS related
RETURN (CASE WHEN d.title_ko <> '' THEN d.title_ko ELSE d.title END) AS title,
       cats, authors, related
"""


def neighborhood(driver: Driver, doc_id: str) -> dict | None:
    """문서의 이웃(카테고리·저자·관련문서)을 그래프 시각화용으로 조회."""
    with driver.session() as session:
        r = session.run(_NEIGHBORHOOD, id=doc_id).single()
        if not r:
            return None
        return {"title": r["title"], "categories": [c for c in r["cats"] if c],
                "authors": r["authors"], "related": r["related"]}
