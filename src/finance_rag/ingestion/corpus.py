"""Synchronize the configured PDF folder with parsed, vector, and graph indexes."""
from __future__ import annotations

import hashlib
import json
import logging
import re
import threading
import uuid
from pathlib import Path

from finance_rag.chunking.strategies import selected_chunks
from finance_rag.config import Settings
from finance_rag.generation.provider import chat_model, invoke_json
from finance_rag.graph.store import GraphStore
from finance_rag.ingestion.parser import parse_pdf
from finance_rag.ingestion.store import DocumentStore
from finance_rag.models import Element
from finance_rag.retrieval.search import RetrievalService
from finance_rag.tracing import TraceWriter

logger = logging.getLogger(__name__)


class CorpusIndexer:
    def __init__(self, settings: Settings, store: DocumentStore,
                 retrieval: RetrievalService) -> None:
        self.settings = settings
        self.store = store
        self.retrieval = retrieval
        self.manifest_path = settings.paths.data / "corpus_index.json"
        self.lock = threading.Lock()
        index_config = {
            "ingestion": settings.ingestion.model_dump(),
            "chunking": settings.chunking.model_dump(),
            "embeddings": settings.embeddings.model_dump(),
            "collection_prefix": settings.retrieval.collection_prefix,
            "graph": settings.graph.model_dump() if settings.graph.enabled else {"enabled": False},
        }
        if settings.graph.enabled:
            index_config["reference_resolver"] = {
                "llm": settings.llm.model_dump(),
                "prompt": settings.prompts.reference_resolver,
            }
        self.config_hash = hashlib.sha256(
            json.dumps(index_config, sort_keys=True).encode()
        ).hexdigest()

    def files(self) -> list[Path]:
        return sorted(path for path in self.settings.paths.corpus.rglob("*")
                      if path.is_file() and path.suffix.lower() == ".pdf")

    def _manifest(self) -> dict[str, dict[str, str]]:
        if not self.manifest_path.exists():
            return {}
        value = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or any(
                not isinstance(key, str) or not isinstance(item, dict)
                or not isinstance(item.get("document_id"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", item["document_id"])
                or not isinstance(item.get("config_hash"), str)
                for key, item in value.items()):
            raise ValueError("Invalid corpus index manifest")
        return value

    def _save_manifest(self, manifest: dict[str, dict[str, str]]) -> None:
        temp = self.manifest_path.with_suffix(".tmp")
        temp.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        temp.replace(self.manifest_path)

    def _index_file(self, path: Path, document_id: str, graph: GraphStore | None) -> None:
        name = path.relative_to(self.settings.paths.corpus).as_posix()
        trace = TraceWriter(self.settings.paths.runs / f"ingest_{uuid.uuid4().hex}.jsonl")
        try:
            parsed_id, elements = parse_pdf(
                path, self.settings.ingestion.parser,
                docling_ocr=self.settings.ingestion.docling_ocr,
                docling_table_structure=self.settings.ingestion.docling_table_structure,
            )
            if parsed_id != document_id:
                raise RuntimeError(f"PDF changed while indexing: {name}")
            if not elements:
                raise ValueError(f"No elements parsed from {name}")
            if self.settings.ingestion.parser == "pdfium_text":
                import pypdfium2 as pdfium

                pdf = pdfium.PdfDocument(str(path))
                try:
                    total_pages = len(pdf)
                finally:
                    pdf.close()
                extracted_pages = {element.page for element in elements}
                trace.write("parser_coverage", document_id=document_id,
                            parser=self.settings.ingestion.parser,
                            total_pages=total_pages, extracted_pages=len(extracted_pages),
                            pages_without_text=sorted(set(range(1, total_pages + 1)) - extracted_pages))
            chunks = selected_chunks(elements, self.settings.chunking,
                                     self.settings.ingestion.strategies)
            resolver_model = None
            resolver_calls = 0

            def resolve_reference(source: Element, label: str,
                                  candidates: list[Element]) -> str | None:
                nonlocal resolver_model, resolver_calls
                if resolver_calls >= self.settings.graph.max_reference_resolution_calls:
                    trace.write("reference_resolution_skipped", source_id=source.element_id,
                                label=label, reason="configured_call_budget")
                    return None
                if resolver_model is None:
                    resolver_model = chat_model(self.settings)
                resolver_calls += 1
                decision, usage = invoke_json(
                    resolver_model,
                    self.settings.prompts.reference_resolver.format(
                        source=json.dumps(source.model_dump(), ensure_ascii=False),
                        label=label,
                        candidates=json.dumps([{
                            "element_id": candidate.element_id,
                            "page": candidate.page,
                            "text": candidate.text,
                            "section_path": candidate.section_path,
                        } for candidate in candidates], ensure_ascii=False),
                    ),
                )
                trace.write("reference_resolution", source_id=source.element_id,
                            label=label, candidate_ids=[item.element_id for item in candidates],
                            target_id=decision.get("target_id"), usage=usage)
                return decision.get("target_id")

            graph_edges = graph.index(document_id, name, elements, resolve_reference) if graph else None
            self.store.save(document_id, name, elements, chunks)
            indexed = {strategy: self.retrieval.index(strategy, entries)
                       for strategy, entries in chunks.items()}
            trace.write("ingestion", document_id=document_id, file_name=name,
                        elements=len(elements), chunks={key: len(value) for key, value in chunks.items()},
                        vectors_indexed=indexed, graph_edges=graph_edges,
                        graph_enabled=self.settings.graph.enabled,
                        config_hash=self.config_hash)
        except Exception as exc:
            trace.write("ingestion_error", file_name=name, error=str(exc))
            raise

    def sync(self) -> dict[str, int]:
        with self.lock:
            files = self.files()
            if not files:
                raise ValueError(f"No PDF reports found in {self.settings.paths.corpus}")
            manifest = self._manifest()
            previous_ids = {entry["document_id"] for entry in manifest.values()}
            previous_ids.update(doc["document_id"] for doc in self.store.documents())
            current: dict[str, str] = {}
            for path in files:
                relative = path.relative_to(self.settings.paths.corpus).as_posix()
                digest = hashlib.sha256()
                with path.open("rb") as source:
                    for block in iter(lambda: source.read(1024 * 1024), b""):
                        digest.update(block)
                current[relative] = digest.hexdigest()
            indexed = 0
            removed = 0
            graph = GraphStore(self.settings.graph) if self.settings.graph.enabled else None
            try:
                if graph is not None:
                    graph.verify()
                for path in files:
                    relative = path.relative_to(self.settings.paths.corpus).as_posix()
                    document_id = current[relative]
                    expected = {"document_id": document_id, "config_hash": self.config_hash}
                    if manifest.get(relative) == expected and (
                            self.store.root / document_id / "meta.json").is_file():
                        continue
                    logger.info("Indexing %s", relative)
                    self._index_file(path, document_id, graph)
                    manifest[relative] = expected
                    # Checkpoint completed reports so an interrupted bulk import can resume.
                    # Old document IDs remain in DocumentStore until cleanup below.
                    self._save_manifest(manifest)
                    indexed += 1
                    logger.info("Indexed %s", relative)
                active_ids = set(current.values())
                strategies = [f"base_{size}" for size in self.settings.chunking.base_sizes]
                strategies.extend(["element", "hierarchical"])
                for document_id in previous_ids - active_ids:
                    if graph is not None:
                        graph.delete_document(document_id)
                    self.retrieval.delete_document(document_id, strategies)
                    self.store.delete(document_id)
                for relative in list(manifest):
                    if relative in current:
                        continue
                    del manifest[relative]
                    removed += 1
                self._save_manifest(manifest)
            finally:
                if graph is not None:
                    graph.close()
            return {"files": len(files), "indexed": indexed, "removed": removed}
