"""Run the external two-report FinanceBench QA set through the production workflow."""
from __future__ import annotations

import json
from pathlib import Path

from finance_rag.agent.workflow import ResearchWorkflow
from finance_rag.config import load_settings
from finance_rag.evaluation.runner import Evaluator
from finance_rag.ingestion.corpus import CorpusIndexer
from finance_rag.ingestion.store import DocumentStore
from finance_rag.retrieval.search import RetrievalService
from finance_rag.tools.operations import ResearchTools
from finance_rag.tracing import TraceWriter
from finance_rag.web.sources import ExternalSources


def main() -> None:
    settings = load_settings()
    dataset = settings.paths.data / "financebench_two_reports.jsonl"
    store = DocumentStore(settings.paths.documents)
    retrieval = RetrievalService(settings, store)
    CorpusIndexer(settings, store, retrieval).sync()
    trace = TraceWriter(settings.paths.runs / "two_report_evaluation_trace.jsonl")
    tools = ResearchTools(store, retrieval, None, ExternalSources(settings.web), trace)
    workflow = ResearchWorkflow(settings, tools, trace, settings.api.default_profile)
    try:
        result = Evaluator(settings, store, retrieval, workflow, trace).run(
            "stage2", "element", path=dataset, profile=settings.api.default_profile
        )
        print(json.dumps(result, indent=2, default=str))
    finally:
        workflow.close()


if __name__ == "__main__":
    main()
