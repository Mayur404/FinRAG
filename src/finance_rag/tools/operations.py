"""Callable research operations backed by stored data and configured services."""
from __future__ import annotations

from finance_rag.graph.store import GraphStore
from finance_rag.ingestion.store import DocumentStore
from finance_rag.models import Evidence, Traversal
from finance_rag.retrieval.search import RetrievalService
from finance_rag.tools.calculator import calculate
from finance_rag.tracing import TraceWriter
from finance_rag.web.sources import ExternalSources


class ResearchTools:
    def __init__(self, store: DocumentStore, retrieval: RetrievalService,
                 graph: GraphStore | None, external: ExternalSources,
                 trace: TraceWriter) -> None:
        self.store, self.retrieval = store, retrieval
        self.graph, self.external, self.trace = graph, external, trace

    def close(self) -> None:
        if self.graph is not None:
            self.graph.close()

    def _record(self, name: str, arguments: dict, result: object) -> object:
        self.trace.write("tool", name=name, arguments=arguments, result=result)
        return result

    def scan_corpus(self) -> list[dict]:
        return self._record("scan_corpus", {}, self.store.documents())

    def preview_report(self, document_id: str) -> dict:
        elements = self.store.elements(document_id)
        result = {"document_id": document_id, "pages": max(e.page for e in elements),
                  "sections": sorted({tuple(e.section_path) for e in elements if e.section_path}),
                  "first_elements": [e.model_dump() for e in elements[:5]]}
        return self._record("preview_report", {"document_id": document_id}, result)

    def list_sections(self, document_id: str) -> list[list[str]]:
        result = [list(path) for path in dict.fromkeys(tuple(e.section_path)
                  for e in self.store.elements(document_id)) if path]
        return self._record("list_sections", {"document_id": document_id}, result)

    def read_page(self, document_id: str, page: int) -> list[dict]:
        result = [e.model_dump() for e in self.store.elements(document_id) if e.page == page]
        return self._record("read_page", {"document_id": document_id, "page": page}, result)

    def read_section(self, document_id: str, section_path: list[str]) -> list[dict]:
        result = [e.model_dump() for e in self.store.elements(document_id)
                  if e.section_path[:len(section_path)] == section_path]
        return self._record("read_section", {"document_id": document_id, "section_path": section_path}, result)

    def search_dense(self, query: str, document_ids: list[str] | None = None,
                     strategy: str = "element") -> list[Evidence]:
        result = self.retrieval.dense(query, strategy, document_ids)
        self._record("search_dense", {"query": query, "document_ids": document_ids,
                                      "strategy": strategy}, [e.model_dump() for e in result])
        return result

    def search_bm25(self, query: str, document_ids: list[str] | None = None) -> list[Evidence]:
        result = self.retrieval.bm25(query, document_ids=document_ids)
        self._record("search_bm25", {"query": query, "document_ids": document_ids},
                     [e.model_dump() for e in result])
        return result

    def search_table(self, query: str, document_ids: list[str] | None = None) -> list[Evidence]:
        result = self.retrieval.table(query, document_ids=document_ids)
        self._record("search_table", {"query": query, "document_ids": document_ids},
                     [e.model_dump() for e in result])
        return result

    def search_graph(self, seeds: list[str], depth: int | None = None) -> tuple[list[Evidence], Traversal]:
        if self.graph is None:
            raise RuntimeError("Neo4j graph is not configured")
        traversal = self.graph.traverse(seeds, depth)
        result = self.retrieval.graph_evidence(traversal)
        self._record("search_graph", {"seeds": seeds, "depth": depth},
                     {"evidence": [e.model_dump() for e in result], "traversal": traversal.model_dump()})
        return result, traversal

    def get_parent_context(self, element_id: str) -> dict:
        element = self.store.element(element_id)
        neighbors = [e for e in self.store.elements(element.document_id)
                     if e.section_path == element.section_path and e.element_id != element_id]
        neighbors.sort(key=lambda e: abs(e.order - element.order))
        result = {"element": element.model_dump(),
                  "section": [e.model_dump() for e in neighbors[
                      :self.retrieval.settings.retrieval.parent_context_neighbors]]}
        return self._record("get_parent_context", {"element_id": element_id}, result)

    def get_table_context(self, element_id: str) -> list[Evidence]:
        document_id = element_id.split(":", 1)[0]
        chunks = [chunk for chunk in self.store.chunks("element", document_id)
                  if chunk.element_type == "table" and element_id in chunk.element_ids]
        result = [self.retrieval._evidence(chunk, None, "table_context") for chunk in chunks]
        self._record("get_table_context", {"element_id": element_id},
                     [item.model_dump() for item in result])
        return result

    def find_reference(self, document_id: str, label: str) -> list[str]:
        if self.graph is None:
            raise RuntimeError("Neo4j graph is not configured")
        result = self.graph.find_reference(document_id, label)
        return self._record("find_reference", {"document_id": document_id, "label": label}, result)

    def follow_reference(self, element_id: str) -> tuple[list[Evidence], Traversal]:
        return self.search_graph([element_id])

    def calculate(self, expression: str, evidence: list[Evidence], evidence_ids: list[str]) -> dict:
        result = calculate(expression, evidence, evidence_ids)
        return self._record("calculate", {"expression": expression,
                                          "evidence_ids": evidence_ids}, result)

    def web_search_tavily(self, query: str) -> list[dict]:
        result = self.external.tavily(query)
        return self._record("web_search_tavily", {"query": query}, result)

    def fetch_web_result(self, url: str) -> dict:
        result = self.external.fetch_web_result(url)
        return self._record("fetch_web_result", {"url": url}, result)

    def search_edgar(self, company: str) -> list[dict]:
        result = self.external.search_edgar(company)
        return self._record("search_edgar", {"company": company}, result)

    def get_sec_company_facts(self, cik: str) -> dict:
        result = self.external.get_sec_company_facts(cik)
        return self._record("get_sec_company_facts", {"cik": cik}, result)
