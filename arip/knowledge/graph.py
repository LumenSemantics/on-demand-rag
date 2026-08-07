from __future__ import annotations

from collections.abc import Sequence

from neo4j import Driver, GraphDatabase

from ..collectors.base import Item

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
