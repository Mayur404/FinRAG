"""Website API and actual LangGraph execution stream."""
from __future__ import annotations

import json
import uuid
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from finance_rag.agent.workflow import ResearchWorkflow
from finance_rag.config import Settings, load_settings
from finance_rag.evaluation.runner import Evaluator
from finance_rag.graph.store import GraphStore
from finance_rag.ingestion.corpus import CorpusIndexer
from finance_rag.ingestion.store import DocumentStore
from finance_rag.retrieval.search import RetrievalService
from finance_rag.tools.operations import ResearchTools
from finance_rag.tracing import TraceWriter
from finance_rag.web.sources import ExternalSources


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    document_id: str | None = None
    document_ids: list[str] = Field(default_factory=list)


class EvaluationRequest(BaseModel):
    stage: str
    strategy: str = "element"
    profile: str = "G"
    graph_depth: int | None = Field(default=None, ge=0)
    limit: int | None = Field(default=None, gt=0)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    for path in (settings.paths.data, settings.paths.runs, settings.paths.documents,
                 settings.paths.corpus, settings.paths.chroma):
        path.mkdir(parents=True, exist_ok=True)
    store = DocumentStore(settings.paths.documents)
    retrieval = RetrievalService(settings, store)
    corpus = CorpusIndexer(settings, store, retrieval)
    external = ExternalSources(settings.web)
    app = FastAPI(title="FinRAG")
    frontend = Path(__file__).resolve().parents[3] / "frontend"
    app.mount("/assets", StaticFiles(directory=frontend), name="assets")

    def graph_store() -> GraphStore:
        return GraphStore(settings.graph)

    def service(profile: str | None = None, graph_depth: int | None = None,
                fixed_context_budget: int | None = None) -> tuple[ResearchWorkflow, TraceWriter]:
        selected_profile = profile or settings.api.default_profile
        trace = TraceWriter(settings.paths.runs / f"trace_{uuid.uuid4().hex}.jsonl")
        public_config = settings.model_dump(mode="json")
        public_config["graph"]["password"] = "REDACTED"
        public_config["web"]["tavily_api_key"] = "REDACTED"
        public_config["web"]["sec_user_agent"] = "REDACTED"
        trace.write("run_config", config=public_config, profile=selected_profile, graph_depth=graph_depth)
        graph = graph_store() if settings.graph.enabled else None
        tools = ResearchTools(store, retrieval, graph, external, trace)
        return ResearchWorkflow(settings, tools, trace, selected_profile, graph_depth,
                                fixed_context_budget), trace

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(frontend / "index.html")

    @app.get("/api/status")
    def status() -> dict:
        try:
            with httpx.Client(timeout=3) as client:
                response = client.get(settings.llm.base_url.rstrip("/") + "/api/tags")
                response.raise_for_status()
                models = [m["name"] for m in response.json().get("models", [])]
            ollama = {"status": "available", "models": models}
        except Exception as exc:
            ollama = {"status": "unavailable", "error": str(exc)}
        if settings.graph.enabled:
            try:
                graph = graph_store()
                try:
                    graph.verify()
                finally:
                    graph.close()
                neo4j = {"status": "available"}
            except Exception as exc:
                neo4j = {"status": "unavailable", "error": str(exc)}
        else:
            neo4j = {"status": "disabled"}
        return {"ollama": ollama, "neo4j": neo4j,
                "documents": len(store.documents()), "corpus_files": len(corpus.files()),
                "corpus_path": str(settings.paths.corpus),
                "ingestion_parser": settings.ingestion.parser,
                "ingestion_strategies": settings.ingestion.strategies,
                "default_profile": settings.api.default_profile,
                "benchmark_present": settings.paths.benchmark.is_file(),
                "web_enabled": settings.web.enabled,
                "llm_provider": settings.llm.provider,
                "llm_model": settings.llm.model,
                "embedding_model": settings.embeddings.model}

    @app.get("/api/documents")
    def documents() -> list[dict]:
        return store.documents()

    @app.post("/api/ask")
    def ask(request: AskRequest) -> dict:
        try:
            corpus.sync()
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        except Exception as exc:
            raise HTTPException(503, f"Corpus indexing failed: {exc}") from exc
        workflow, trace = service()
        try:
            selection: str | list[str] | None = request.document_ids or request.document_id
            return workflow.run(request.question, selection).model_dump()
        except Exception as exc:
            trace.write("run_error", question=request.question, error=str(exc))
            raise HTTPException(500, str(exc)) from exc
        finally:
            workflow.close()

    @app.post("/api/ask/stream")
    def ask_stream(request: AskRequest) -> StreamingResponse:
        def events():
            workflow = None
            trace = None
            try:
                yield f"data: {json.dumps({'event': 'indexing', 'files': len(corpus.files())})}\n\n"
                summary = corpus.sync()
                yield f"data: {json.dumps({'event': 'indexed', 'data': summary})}\n\n"
                workflow, trace = service()
                selection: str | list[str] | None = request.document_ids or request.document_id
                for event in workflow.stream(request.question, selection):
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            except Exception as exc:
                if trace is not None:
                    trace.write("run_error", question=request.question, error=str(exc))
                yield f"data: {json.dumps({'event': 'error', 'error': str(exc)})}\n\n"
            finally:
                if workflow is not None:
                    workflow.close()
        return StreamingResponse(events(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache"})

    @app.post("/api/evaluate")
    def evaluate(request: EvaluationRequest) -> dict:
        if request.stage not in {"stage1", "stage2"}:
            raise HTTPException(400, "Stage must be stage1 or stage2")
        if request.stage == "stage1" and request.strategy not in {
                f"base_{size}" for size in settings.chunking.base_sizes} | {"element"}:
            raise HTTPException(400, "Unknown Stage 1 strategy")
        if request.stage == "stage1" and request.strategy not in settings.ingestion.strategies:
            raise HTTPException(409, f"Strategy {request.strategy} is not indexed in the current ingestion mode")
        if request.stage == "stage2" and request.profile not in settings.evaluation.profiles and request.profile != "A":
            raise HTTPException(400, "Unknown ablation profile")
        if (request.stage == "stage2" and request.profile in settings.evaluation.profiles
                and "graph" in settings.evaluation.profiles[request.profile].paths
                and not settings.graph.enabled):
            raise HTTPException(409, f"Profile {request.profile} requires Neo4j graph mode")
        if request.graph_depth is not None and request.graph_depth > settings.graph.max_traversal_depth:
            raise HTTPException(400, "Graph depth exceeds configured bound")
        try:
            corpus.sync()
        except Exception as exc:
            raise HTTPException(503, f"Corpus indexing failed: {exc}") from exc
        workflow, trace = service("G" if request.profile == "A" else request.profile,
                                  request.graph_depth, settings.agent.context_tokens)
        evaluator = Evaluator(settings, store, retrieval, workflow, trace)
        try:
            return evaluator.run(request.stage, request.strategy, limit=request.limit,
                                 profile=request.profile)
        except Exception as exc:
            trace.write("evaluation_error", stage=request.stage, profile=request.profile,
                        error=str(exc))
            raise HTTPException(500, str(exc)) from exc
        finally:
            workflow.close()

    @app.get("/api/runs")
    def runs() -> list[dict]:
        return [{"name": path.name, "bytes": path.stat().st_size}
                for path in sorted(settings.paths.runs.glob("*.jsonl"), reverse=True)]

    return app


app = create_app()
