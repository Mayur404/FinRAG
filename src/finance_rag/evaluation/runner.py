"""Measured FinanceBench retrieval and QA evaluation; no baked-in results."""
from __future__ import annotations

import json
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from rouge_score import rouge_scorer
from sacrebleu.metrics import BLEU
import tiktoken

from finance_rag.agent.workflow import ResearchWorkflow
from finance_rag.config import Settings
from finance_rag.generation.provider import chat_model, invoke_text
from finance_rag.ingestion.store import DocumentStore
from finance_rag.retrieval.search import RetrievalService
from finance_rag.tracing import TraceWriter


def _normal(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def load_questions(path: Path, store: DocumentStore) -> list[dict]:
    if not path.is_file():
        raise FileNotFoundError(f"Benchmark questions not found: {path}")
    documents = store.documents()

    def resolve_document(name: str | None, document_id: str | None = None) -> str:
        if document_id:
            return document_id
        matches = [d["document_id"] for d in documents
                   if name and _normal(Path(d["name"]).stem) == _normal(name)]
        if len(matches) != 1:
            raise ValueError(f"Benchmark report must match one indexed PDF: {name}")
        return matches[0]

    rows: list[dict] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        raw = json.loads(line)
        question = raw.get("question")
        truth = raw.get("answer") or raw.get("ground_truth_answer")
        name = raw.get("doc_name") or raw.get("document_name")
        document_id = resolve_document(name, raw.get("document_id"))
        if not question or not truth:
            raise ValueError(f"Benchmark line {line_number} lacks question, answer, or a uniquely matched report")
        gold_evidence = []
        if isinstance(raw.get("evidence"), list):
            for item in raw["evidence"]:
                # FinanceBench publishes zero-based PDF page indices; Docling uses one-based pages.
                page_index = item.get("evidence_page_num")
                if not isinstance(page_index, int) or page_index < 0:
                    raise ValueError(f"Benchmark line {line_number} has an invalid evidence page")
                gold_evidence.append({
                    "document_id": resolve_document(item.get("doc_name")
                                                    or item.get("evidence_doc_name") or name),
                    "page": page_index + 1,
                    "text": item["evidence_text"],
                })
        else:
            gold_evidence.append({"document_id": document_id,
                                  "page": raw.get("page_number", raw.get("page")),
                                  "text": raw.get("evidence_text") or raw.get("evidence")})
        rows.append({"id": raw.get("financebench_id", line_number), "question": question,
                     "answer": truth, "document_id": document_id,
                     "gold_evidence": gold_evidence})
    if not rows:
        raise ValueError("Benchmark file contains no questions")
    return rows


class Evaluator:
    def __init__(self, settings: Settings, store: DocumentStore,
                 retrieval: RetrievalService, workflow: ResearchWorkflow,
                 trace: TraceWriter) -> None:
        self.settings, self.store, self.retrieval = settings, store, retrieval
        self.workflow, self.trace = workflow, trace
        self.model = chat_model(settings)
        self.rouge = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)
        self.bleu = BLEU(effective_order=True)
        self.tokenizer = tiktoken.get_encoding(settings.chunking.tokenizer)

    def _judge(self, question: str, truth: str, prediction: str) -> bool:
        if prediction.strip().lower().startswith("no answer"):
            return False
        response, usage = invoke_text(self.model, self.settings.prompts.judge.format(
            question=question, ground_truth=truth, prediction=prediction))
        self.trace.write("judge", question=question, truth=truth, prediction=prediction,
                         response=response, usage=usage)
        if response.startswith("True"):
            return True
        if response.startswith("False"):
            return False
        raise ValueError(f"QA judge did not begin with True or False: {response[:100]}")

    def run(self, stage: str, strategy: str, path: Path | None = None,
            limit: int | None = None, profile: str = "G") -> dict:
        questions = load_questions(path or self.settings.paths.benchmark, self.store)
        if limit is not None:
            questions = questions[:limit]
        output = self.settings.paths.runs / f"evaluation_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{stage}_{strategy}_{profile}_{uuid.uuid4().hex[:8]}.jsonl"
        output.parent.mkdir(parents=True, exist_ok=True)
        rows: list[dict] = []
        for question in questions:
            start = time.perf_counter()
            try:
                if stage == "stage1" or (stage == "stage2" and profile == "A"):
                    baseline_strategy = "element" if stage == "stage2" else strategy
                    evidence = self.retrieval.dense(question["question"], baseline_strategy,
                                                    [question["document_id"]],
                                                    self.settings.retrieval.stage1_top_k)
                    if stage == "stage2":
                        budget = self.settings.agent.context_tokens
                        packed = []
                        for item in evidence:
                            size = len(self.tokenizer.encode(f"[{item.evidence_id}] {item.text}")) + 1
                            if size <= budget:
                                packed.append(item)
                                budget -= size
                        evidence = packed
                    context = "\n".join(f"[{e.evidence_id}] {e.text}" for e in evidence)
                    answer, usage = invoke_text(self.model, self.settings.prompts.synthesis.format(
                        question=question["question"], grade=json.dumps({"sufficient": bool(evidence)}),
                        evidence=context))
                    tool_calls, llm_calls, hops = 1, 1, 0
                elif stage == "stage2":
                    result = self.workflow.run(question["question"], question["document_id"])
                    evidence, answer = result.evidence, result.answer
                    usage = result.metadata.get("usage", {})
                    tool_calls = result.metadata.get("tool_calls", 0)
                    llm_calls = result.metadata.get("llm_calls", 0)
                    hops = result.traversal.depth if result.traversal else 0
                else:
                    raise ValueError(f"Unknown evaluation stage: {stage}")
                gold_pages = {(gold["document_id"], int(gold["page"]))
                              for gold in question["gold_evidence"] if gold["page"] is not None}
                retrieved_pages = {(e.document_id, page) for e in evidence
                                   for page in self._pages(e, strategy if stage == "stage1" else "element")}
                page_hit = bool(gold_pages & retrieved_pages) if gold_pages else None
                gold_texts = [gold["text"] for gold in question["gold_evidence"] if gold["text"]]
                rouge = max((self.rouge.score(gold, e.text)["rougeL"].fmeasure
                             for gold in gold_texts for e in evidence), default=0) if gold_texts else None
                bleu = max((self.bleu.sentence_score(e.text, [gold]).score / 100
                            for gold in gold_texts for e in evidence), default=0) if gold_texts else None
                recovered_hops = min((len(e.traversal_path) for e in evidence
                                      if (e.document_id, e.page) in gold_pages and e.traversal_path),
                                     default=None)
                answer_produced = not answer.strip().lower().startswith("no answer")
                final_status = "answered" if answer_produced else "no_answer"
                verification = (result.metadata.get("verification")
                                if stage == "stage2" and profile != "A" else None)
                citations = (result.citations if stage == "stage2" and profile != "A" else [])
                row = {**question, "prediction": answer,
                       "retrieved_evidence": [e.model_dump() for e in evidence],
                       "answer_produced": answer_produced,
                       "retrieved_evidence_count": len(evidence),
                       "answer_supported_by_retrieved_evidence": (
                           verification.get("valid") if answer_produced
                           and isinstance(verification, dict) else None),
                       "citations_returned": bool(citations),
                       "citation_count": len(citations),
                       "final_status": final_status,
                       "page_hit": page_hit, "rouge_l": rouge, "bleu": bleu,
                       "qa_correct": self._judge(question["question"], question["answer"], answer),
                       "no_answer": answer.strip().lower().startswith("no answer"),
                       "traversal_depth": hops, "hops_recovered": recovered_hops,
                       "context_tokens": (result.metadata.get("context_tokens") if stage == "stage2" and profile != "A"
                                          else sum(len(self.tokenizer.encode(f"[{e.evidence_id}] {e.text}")) + 1
                                                   for e in evidence)),
                       "tool_calls": tool_calls,
                       "llm_calls": llm_calls,
                       "usage": usage, "latency_seconds": time.perf_counter() - start,
                       "status": "completed"}
            except Exception as exc:
                row = {**question, "status": "failed", "final_status": "error",
                       "answer_produced": False, "retrieved_evidence_count": 0,
                       "answer_supported_by_retrieved_evidence": None,
                       "citations_returned": False, "citation_count": 0,
                       "error": str(exc),
                       "latency_seconds": time.perf_counter() - start}
            rows.append(row)
            with output.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        completed = [r for r in rows if r["status"] == "completed"]
        def mean(key: str) -> float | None:
            values = [r[key] for r in completed if r.get(key) is not None]
            return sum(values) / len(values) if values else None
        result = {"stage": stage, "strategy": strategy, "profile": profile,
                  "graph_depth_limit": self.workflow.graph_depth,
                  "questions": len(rows),
                  "completed": len(completed), "failed": len(rows) - len(completed),
                  "chunk_count": len(self.store.chunks(strategy if stage == "stage1" else "element")),
                  "page_hit_rate": mean("page_hit"), "rouge_l": mean("rouge_l"),
                  "bleu": mean("bleu"), "qa_accuracy": mean("qa_correct"),
                  "no_answer_rate": mean("no_answer"),
                  "hops_recovered": mean("hops_recovered"),
                  "context_tokens": mean("context_tokens"),
                  "latency_seconds": mean("latency_seconds"),
                  "tool_calls": mean("tool_calls"), "run_file": str(output),
                  "llm_calls": mean("llm_calls"),
                  "timestamp": datetime.now(timezone.utc).isoformat(),
                  "config": self._public_config()}
        self.trace.write("evaluation", **result)
        return result

    def _pages(self, evidence, strategy: str) -> list[int]:
        chunks = self.store.chunks(strategy, evidence.document_id)
        return next((c.pages for c in chunks if c.chunk_id == evidence.evidence_id), [evidence.page])

    def _public_config(self) -> dict:
        config = self.settings.model_dump(mode="json")
        config["graph"]["password"] = "REDACTED"
        config["web"]["tavily_api_key"] = "REDACTED"
        config["web"]["sec_user_agent"] = "REDACTED"
        return config
