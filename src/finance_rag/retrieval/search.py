"""Dense, BM25, table, and graph retrieval with reciprocal rank fusion."""
from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict

import chromadb
from llama_index.core.schema import TextNode
from rank_bm25 import BM25Okapi

from finance_rag.config import Settings
from finance_rag.generation.provider import embedding_model
from finance_rag.ingestion.store import DocumentStore
from finance_rag.models import Chunk, Evidence, Traversal


def _tokens(text: str) -> list[str]:
    return re.findall(r"[\w.%-]+", text.lower())


class RetrievalService:
    def __init__(self, settings: Settings, store: DocumentStore) -> None:
        self.settings = settings
        self.store = store
        self.client = chromadb.PersistentClient(path=str(settings.paths.chroma))
        self.embeddings = embedding_model(settings)
        self._reranker = None

    def _collection(self, strategy: str):
        config_key = hashlib.sha256(json.dumps({
            "embedding_provider": self.settings.embeddings.provider,
            "embedding_model": self.settings.embeddings.model,
            "chunking": self.settings.chunking.model_dump(), "strategy": strategy,
        }, sort_keys=True).encode()).hexdigest()[:12]
        name = f"{self.settings.retrieval.collection_prefix}_{strategy}_{config_key}"
        return self.client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})

    def index(self, strategy: str, chunks: list[Chunk]) -> int:
        collection = self._collection(strategy)
        batch_size = self.settings.embeddings.batch_size
        indexed = 0
        for start in range(0, len(chunks), batch_size):
            batch = chunks[start:start + batch_size]
            existing = set(collection.get(ids=[c.chunk_id for c in batch], include=[])["ids"])
            batch = [c for c in batch if c.chunk_id not in existing]
            if not batch:
                continue
            vectors = self.embeddings.embed_documents([c.text for c in batch])
            collection.upsert(ids=[c.chunk_id for c in batch], embeddings=vectors,
                              documents=[c.text for c in batch], metadatas=[{
                                  "document_id": c.document_id,
                                  "pages": json.dumps(c.pages),
                                  "element_ids": json.dumps(c.element_ids),
                                  "section_path": json.dumps(c.section_path),
                                  "element_type": c.element_type,
                                  "strategy": c.strategy,
                              } for c in batch])
            indexed += len(batch)
        return indexed

    def delete_document(self, document_id: str, strategies: list[str]) -> None:
        for strategy in strategies:
            collection = self._collection(strategy)
            ids = collection.get(where={"document_id": document_id}, include=[])["ids"]
            if ids:
                collection.delete(ids=ids)

    @staticmethod
    def _evidence(chunk: Chunk, score: float | None, source: str) -> Evidence:
        return Evidence(evidence_id=chunk.chunk_id, document_id=chunk.document_id,
                        page=chunk.pages[0], element_id=chunk.element_ids[0],
                        section_path=chunk.section_path, element_type=chunk.element_type,
                        text=chunk.text, score=score, sources=[source])

    def dense(self, query: str, strategy: str = "element", document_ids: list[str] | None = None,
              limit: int | None = None, tables_only: bool = False) -> list[Evidence]:
        collection = self._collection(strategy)
        count = collection.count()
        if count == 0:
            return []
        filters = []
        if document_ids:
            filters.append({"document_id": (document_ids[0] if len(document_ids) == 1
                                             else {"$in": document_ids})})
        if tables_only:
            filters.append({"element_type": "table"})
        where = (filters[0] if len(filters) == 1 else {"$and": filters}) if filters else None
        kwargs = {"where": where} if where else {}
        result = collection.query(query_embeddings=[self.embeddings.embed_query(query)],
                                  n_results=min(limit or self.settings.retrieval.per_source_k, count),
                                  include=["documents", "metadatas", "distances"], **kwargs)
        evidence = []
        for cid, text, meta, distance in zip(result["ids"][0], result["documents"][0],
                                              result["metadatas"][0], result["distances"][0]):
            evidence.append(Evidence(evidence_id=cid, document_id=meta["document_id"],
                                     page=json.loads(meta["pages"])[0],
                                     element_id=json.loads(meta["element_ids"])[0],
                                     section_path=json.loads(meta["section_path"]),
                                     element_type=meta["element_type"], text=text,
                                     score=1 - distance, sources=["dense"]))
        return evidence

    def table(self, query: str, document_ids: list[str] | None = None,
              limit: int | None = None) -> list[Evidence]:
        requested = limit or self.settings.retrieval.per_source_k
        lexical = self.bm25(query, document_ids=document_ids, limit=requested,
                            tables_only=True)
        semantic = self.dense(query, document_ids=document_ids, limit=requested,
                              tables_only=True)
        return self.fuse([lexical, semantic])[:requested]

    def bm25(self, query: str, strategy: str = "element", document_ids: list[str] | None = None,
             limit: int | None = None, tables_only: bool = False) -> list[Evidence]:
        chunks = ([chunk for document_id in document_ids
                   for chunk in self.store.chunks(strategy, document_id)]
                  if document_ids else self.store.chunks(strategy))
        if tables_only:
            chunks = [c for c in chunks if c.element_type == "table"]
        if not chunks:
            return []
        nodes = [TextNode(id_=c.chunk_id, text=c.text, metadata={"document_id": c.document_id})
                 for c in chunks]
        ranker = BM25Okapi([_tokens(node.text) for node in nodes])
        query_terms = set(_tokens(query))
        scores = ranker.get_scores(list(query_terms))
        indices = sorted((i for i, node in enumerate(nodes)
                          if query_terms.intersection(_tokens(node.text))),
                         key=lambda i: scores[i], reverse=True)
        source = "table" if tables_only else "bm25"
        return [self._evidence(chunks[i], float(scores[i]), source)
                for i in indices[:limit or self.settings.retrieval.per_source_k]]

    def rerank(self, query: str, evidence: list[Evidence]) -> list[Evidence]:
        if not evidence:
            return []
        if self._reranker is None:
            from sentence_transformers import CrossEncoder
            self._reranker = CrossEncoder(
                self.settings.retrieval.reranker_model,
                local_files_only=self.settings.retrieval.reranker_local_files_only,
            )
        document_names = {item["document_id"]: item["name"]
                          for item in self.store.documents()}
        passages = [
            f"source: {document_names.get(e.document_id, e.document_id)}\n"
            f"section: {' > '.join(e.section_path)}\n{e.text}"
            for e in evidence
        ]
        scores = self._reranker.predict(list(zip([query] * len(passages), passages)))
        for e, score in zip(evidence, scores):
            e.score = float(score)
            e.sources.append("reranker")
        return sorted(evidence, key=lambda e: e.score or 0, reverse=True)[:self.settings.retrieval.rerank_top_k]

    def fuse(self, rankings: list[list[Evidence]]) -> list[Evidence]:
        fused: dict[str, Evidence] = {}
        scores: dict[str, float] = defaultdict(float)
        for ranking in rankings:
            for rank, item in enumerate(ranking, 1):
                if item.evidence_id not in fused:
                    fused[item.evidence_id] = item.model_copy(deep=True)
                else:
                    fused[item.evidence_id].sources.extend(item.sources)
                scores[item.evidence_id] += 1 / (self.settings.retrieval.fusion_k + rank)
        for key, item in fused.items():
            item.score = scores[key]
            item.sources = sorted(set(item.sources))
        return sorted(fused.values(), key=lambda item: item.score or 0, reverse=True)

    def graph_evidence(self, traversal: Traversal) -> list[Evidence]:
        paths = {path[-1]["target"]: path for path in traversal.paths if path}
        output: list[Evidence] = []
        for element_id in traversal.nodes:
            element = self.store.element(element_id)
            output.append(Evidence(evidence_id=element_id, document_id=element.document_id,
                                   page=element.page, element_id=element_id,
                                   section_path=element.section_path,
                                   element_type=element.element_type, text=element.text,
                                   sources=["graph"], traversal_path=paths.get(element_id, [])))
        return output
