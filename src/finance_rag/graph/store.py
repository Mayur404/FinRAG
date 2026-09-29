"""Document structure and verified cross-reference navigation in Neo4j."""
from __future__ import annotations

import re
from collections import deque
from collections.abc import Iterable
from typing import Callable

from neo4j import GraphDatabase

from finance_rag.config import GraphSettings
from finance_rag.models import Element, Traversal

REFERENCE = re.compile(r"\b(note|item|exhibit|schedule|section)\s+([A-Z]?\d+[A-Z]?(?:\.\d+)*|[A-Z])\b", re.I)
EDGE_TYPES = {"CONTAINS", "PARENT_OF", "PRECEDES", "SAME_SECTION", "TABLE_CONTEXT", "REFERENCES", "REFERENCED_BY"}


def reference_key(text: str) -> str | None:
    match = REFERENCE.search(text)
    return f"{match[1].lower()}:{match[2].lower()}" if match else None


class GraphStore:
    def __init__(self, settings: GraphSettings) -> None:
        if not settings.password:
            raise ValueError("NEO4J_PASSWORD is required for graph operations")
        self.settings = settings
        self.driver = GraphDatabase.driver(settings.uri, auth=(settings.user, settings.password))

    def close(self) -> None:
        self.driver.close()

    def verify(self) -> None:
        self.driver.verify_connectivity()

    def delete_document(self, document_id: str) -> None:
        self.verify()
        with self.driver.session() as session:
            session.run("MATCH (e:Element {document_id:$doc}) DETACH DELETE e", doc=document_id).consume()
            session.run("MATCH (d:Document {id:$doc}) DETACH DELETE d", doc=document_id).consume()

    def index(self, document_id: str, name: str, elements: list[Element],
              resolver: Callable[[Element, str, list[Element]], str | None] | None = None) -> int:
        self.verify()
        headings = [e for e in elements if e.element_type in {"title", "section_header"}]
        targets: dict[str, list[Element]] = {}
        for heading in headings:
            key = reference_key(heading.text)
            if key:
                targets.setdefault(key, []).append(heading)
        edges: set[tuple[str, str, str]] = set()
        for index, element in enumerate(elements):
            if index:
                previous = elements[index - 1]
                edges.add((previous.element_id, element.element_id, "PRECEDES"))
                if previous.section_path == element.section_path and element.section_path:
                    edges.add((previous.element_id, element.element_id, "SAME_SECTION"))
                if element.element_type == "table":
                    edges.add((previous.element_id, element.element_id, "TABLE_CONTEXT"))
            for key in set(f"{kind.lower()}:{label.lower()}" for kind, label in REFERENCE.findall(element.text)):
                matches = [target for target in targets.get(key, []) if target.element_id != element.element_id]
                target = matches[0] if len(matches) == 1 else None
                if len(matches) > 1 and resolver is not None:
                    chosen_id = resolver(element, key, matches)
                    if chosen_id is not None:
                        target = next((candidate for candidate in matches
                                       if candidate.element_id == chosen_id), None)
                        if target is None:
                            raise ValueError(f"Reference resolver chose unknown target: {chosen_id}")
                if target is not None:
                    edges.add((element.element_id, target.element_id, "REFERENCES"))
                    edges.add((target.element_id, element.element_id, "REFERENCED_BY"))
            if element.section_path:
                parent = next((h for h in reversed(headings) if h.order < element.order and
                               h.text == element.section_path[-1]), None)
                if parent and parent.element_id != element.element_id:
                    edges.add((parent.element_id, element.element_id, "PARENT_OF"))
        with self.driver.session() as session:
            session.run("CREATE CONSTRAINT document_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE").consume()
            session.run("CREATE CONSTRAINT element_id IF NOT EXISTS FOR (e:Element) REQUIRE e.id IS UNIQUE").consume()
            session.run("MERGE (d:Document {id:$id}) SET d.name=$name", id=document_id, name=name).consume()
            for start in range(0, len(elements), self.settings.write_batch_size):
                batch = elements[start:start + self.settings.write_batch_size]
                rows = [{"id": e.element_id, "page": e.page, "text": e.text,
                         "kind": e.element_type, "section": e.section_path} for e in batch]
                session.run("MATCH (d:Document {id:$doc}) UNWIND $rows AS row "
                            "MERGE (e:Element {id:row.id}) SET e.document_id=$doc, "
                            "e.page=row.page, e.text=row.text, e.element_type=row.kind, "
                            "e.section_path=row.section MERGE (d)-[:CONTAINS]->(e)",
                            doc=document_id, rows=rows).consume()
            for kind in sorted(EDGE_TYPES - {"CONTAINS"}):
                typed_edges = [(source, target) for source, target, edge_kind in edges
                               if edge_kind == kind]
                for start in range(0, len(typed_edges), self.settings.write_batch_size):
                    batch = typed_edges[start:start + self.settings.write_batch_size]
                    session.run(f"UNWIND $rows AS row MATCH (a:Element {{id:row.source}}), "
                                f"(b:Element {{id:row.target}}) MERGE (a)-[:{kind}]->(b)",
                                rows=[{"source": source, "target": target}
                                      for source, target in batch]).consume()
        return len(edges) + len(elements)

    def traverse(self, seeds: Iterable[str], depth: int | None = None,
                 relation_types: set[str] | None = None) -> Traversal:
        self.verify()
        limit = min(depth if depth is not None else self.settings.max_traversal_depth,
                    self.settings.max_traversal_depth)
        allowed = relation_types or {"REFERENCES", "REFERENCED_BY", "PARENT_OF", "TABLE_CONTEXT", "PRECEDES"}
        if not allowed.issubset(EDGE_TYPES):
            raise ValueError("Invalid graph relation type")
        queue = deque((seed, 0, []) for seed in dict.fromkeys(seeds))
        visited_nodes: set[str] = set()
        visited_edges: set[tuple[str, str, str]] = set()
        paths: list[list[dict]] = []
        while (queue and len(visited_nodes) < self.settings.max_nodes_per_query
               and len(visited_edges) < self.settings.max_edges_per_query):
            current, hops, path = queue.popleft()
            if current in visited_nodes:
                continue
            visited_nodes.add(current)
            if path:
                paths.append(path)
            if hops >= limit:
                continue
            with self.driver.session() as session:
                records = session.run(
                    "MATCH (a:Element {id:$id})-[r]->(b:Element) "
                    "WHERE type(r) IN $types AND a.document_id=b.document_id "
                    "RETURN b.id AS target, type(r) AS kind ORDER BY target LIMIT $remaining",
                    id=current, types=sorted(allowed),
                    remaining=self.settings.max_edges_per_query - len(visited_edges))
                for record in records:
                    edge = (current, record["target"], record["kind"])
                    if edge in visited_edges:
                        continue
                    visited_edges.add(edge)
                    if (record["target"] not in visited_nodes and
                            len(visited_nodes) + len(queue) < self.settings.max_nodes_per_query):
                        step = {"source": current, "target": record["target"], "relation": record["kind"]}
                        queue.append((record["target"], hops + 1, path + [step]))
        return Traversal(nodes=sorted(visited_nodes),
                         edges=[{"source": a, "target": b, "relation": kind}
                                for a, b, kind in sorted(visited_edges)
                                if a in visited_nodes and b in visited_nodes], paths=paths,
                         depth=max((len(path) for path in paths), default=0))

    def find_reference(self, document_id: str, label: str) -> list[str]:
        key = reference_key(label)
        if key is None:
            return []
        with self.driver.session() as session:
            records = session.run("MATCH (e:Element {document_id:$doc}) "
                                  "WHERE e.element_type IN ['title','section_header'] "
                                  "RETURN e.id AS id, e.text AS text", doc=document_id)
            return [r["id"] for r in records if reference_key(r["text"]) == key]
