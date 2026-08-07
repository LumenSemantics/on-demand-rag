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
