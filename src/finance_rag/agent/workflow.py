"""Bounded LangGraph planner, router, retrieval, grading, synthesis and verification."""
from __future__ import annotations

import hashlib
import json
import re
import time
from decimal import Decimal, DivisionByZero
from typing import Any, TypedDict

import tiktoken
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from finance_rag.config import ExperimentProfile, Settings
from finance_rag.generation.provider import JSONResponseError, chat_model, invoke_json_response, invoke_text
from finance_rag.graph.store import REFERENCE
from finance_rag.models import Answer, Evidence, Traversal
from finance_rag.tools.calculator import extract_evidence_numbers
from finance_rag.tools.operations import ResearchTools
from finance_rag.tracing import TraceWriter


class Plan(BaseModel):
    question_type: str = Field(max_length=100)
    subquestions: list[str] = Field(max_length=6)
    retrieval_strategy: list[str]
    preferred_sources: list[str]
    needs_calculator: bool
    needs_tavily: bool
    context_budget: int = Field(gt=0)
    document_id: str | None


class Grade(BaseModel):
    sufficient: bool
    needs_calculator: bool
    reason: str = Field(max_length=600)
    rewritten_query: str = Field(max_length=1000)


class RouterDecision(BaseModel):
    paths: list[str] = Field(min_length=1)


class ProposedCalculation(BaseModel):
    label: str = Field(max_length=120)
    expression: str = Field(max_length=256, pattern=r"^[0-9+\-*/().\s]*$")
    operand_evidence_ids: list[str]


class CalculationProposal(BaseModel):
    calculations: list[ProposedCalculation] = Field(max_length=8)


class Verification(BaseModel):
    valid: bool
    reason: str = Field(max_length=600)
    supported_citations: list[str]


class State(TypedDict, total=False):
    question: str
    document_id: str | None
    document_ids: list[str] | None
    query: str
    plan: dict
    paths: list[str]
    rankings: list[list[dict]]
    evidence: list[dict]
    context_tokens: int
    traversal: dict | None
    grade: dict
    answer: str
    citations: list[str]
    calculations: list[dict]
    verification: dict
    iterations: int
    tool_calls: int
    llm_calls: int
    web_calls: int
    usage: dict
    status: str


class ResearchWorkflow:
    def __init__(self, settings: Settings, tools: ResearchTools, trace: TraceWriter,
                 profile_name: str = "G", graph_depth: int | None = None,
                 fixed_context_budget: int | None = None) -> None:
        self.settings, self.tools, self.trace = settings, tools, trace
        if profile_name not in settings.evaluation.profiles:
            raise ValueError(f"Unknown experiment profile: {profile_name}")
        self.profile_name = profile_name
        self.profile: ExperimentProfile = settings.evaluation.profiles[profile_name]
        self.available_paths = {"dense", "bm25"}
        if settings.ingestion.parser == "docling":
            self.available_paths.add("table")
        if settings.graph.enabled:
            self.available_paths.add("graph")
        if not set(self.profile.paths).issubset(self.available_paths):
            raise ValueError(f"Profile {profile_name} requires a disabled retrieval service")
        if graph_depth is not None and not 0 <= graph_depth <= settings.graph.max_traversal_depth:
            raise ValueError("Graph depth exceeds configured bound")
        self.graph_depth = graph_depth
        self.fixed_context_budget = fixed_context_budget
        if self.profile.web and not settings.web.enabled:
            raise ValueError("Web ablation requires web.enabled=true")
        self.model = chat_model(settings)
        self.verifier_model = chat_model(settings, settings.llm.verifier_model)
        self.tokenizer = tiktoken.get_encoding(settings.chunking.tokenizer)
        graph = StateGraph(State)
        for name, method in [("plan", self._plan), ("route", self._route),
                             ("retrieve", self._retrieve), ("prepare", self._prepare),
                             ("grade", self._grade), ("rewrite", self._rewrite),
                             ("synthesize", self._synthesize), ("verify", self._verify)]:
            graph.add_node(name, method)
        graph.add_edge(START, "plan" if self.profile.planner else "route" if self.profile.router else "retrieve")
        if self.profile.planner:
            graph.add_edge("plan", "route" if self.profile.router else "retrieve")
        if self.profile.router:
            graph.add_edge("route", "retrieve")
        graph.add_edge("retrieve", "prepare")
        if self.profile.grader:
            graph.add_edge("prepare", "grade")
            graph.add_conditional_edges("grade", self._after_grade,
                                        {"rewrite": "rewrite", "synthesize": "synthesize"})
            graph.add_edge("rewrite", "route" if self.profile.router else "retrieve")
        else:
            graph.add_edge("prepare", "synthesize")
        graph.add_edge("synthesize", "verify" if self.profile.verifier else END)
        if self.profile.verifier:
            graph.add_edge("verify", END)
        self.graph = graph.compile()

    def _log(self, event: str, payload: dict) -> dict:
        self.trace.write(event, **payload)
        return payload

    @staticmethod
    def _usage(state: State, new: dict) -> dict:
        total = dict(state.get("usage", {}))
        for key, value in new.items():
            if isinstance(value, (int, float)):
                total[key] = total.get(key, 0) + value
        return total

    def _invoke_json(self, operation: str, prompt: str,
                     schema: dict[str, Any], *, verifier: bool = False
                     ) -> tuple[dict[str, Any], dict]:
        try:
            model = self.verifier_model if verifier else self.model
            data, usage, raw = invoke_json_response(model, prompt, schema)
        except JSONResponseError as exc:
            self.trace.write("llm_response_error", operation=operation,
                             raw_response=exc.raw_response, error=str(exc))
            raise
        self.trace.write("llm_response", operation=operation,
                         raw_response=raw, parsed_response=data, usage=usage)
        return data, usage

    def _plan(self, state: State) -> dict:
        documents = self.tools.scan_corpus()
        known_ids = {item["document_id"] for item in documents}
        requested_documents = state.get("document_ids")
        if requested_documents:
            unknown = set(requested_documents) - known_ids
            if unknown:
                raise ValueError(f"Requested documents are not indexed: {sorted(unknown)}")
            documents = [item for item in documents if item["document_id"] in requested_documents]
        candidates = [{"document_id": item["document_id"], "name": item["name"]}
                      for item in documents]
        data, usage = self._invoke_json(
            "planner",
            self.settings.prompts.planner.format(
                question=state["question"],
                available_documents=json.dumps(candidates, ensure_ascii=False),
            ),
            Plan.model_json_schema(),
        )
        requested_budget = data.get("context_budget")
        if isinstance(requested_budget, int) and requested_budget <= 0:
            data["context_budget"] = self.settings.agent.context_tokens
        plan = Plan.model_validate(data)
        candidate_ids = {item["document_id"] for item in candidates}
        if requested_documents:
            plan.document_id = requested_documents[0] if len(requested_documents) == 1 else None
            selected_documents = requested_documents
        elif plan.document_id is not None and plan.document_id not in candidate_ids:
            raise ValueError("Planner selected a document that is not indexed")
        else:
            selected_documents = [plan.document_id] if plan.document_id else None
        plan.context_budget = (self.fixed_context_budget if self.fixed_context_budget is not None
                               else max(self.settings.agent.min_context_tokens,
                                        min(plan.context_budget, self.settings.agent.context_tokens)))
        return self._log("planner", {"plan": plan.model_dump(),
                                     "document_id": plan.document_id,
                                     "document_ids": selected_documents,
                                     "tool_calls": state.get("tool_calls", 0) + 1,
                                     "requested_context_budget": requested_budget,
                                     "llm_calls": state.get("llm_calls", 0) + 1,
                                     "usage": self._usage(state, usage)})

    def _route(self, state: State) -> dict:
        prompt = self.settings.prompts.router.format(
            question=state["query"], plan=json.dumps(state["plan"]),
            available_paths=json.dumps(sorted(self.available_paths)),
        )
        data, usage = self._invoke_json("router", prompt, RouterDecision.model_json_schema())
        decision = RouterDecision.model_validate(data)
        if any(path not in self.available_paths for path in decision.paths):
            self.trace.write("router_invalid", decision=data,
                             allowed_paths=sorted(self.available_paths))
            raise ValueError(f"Router selected an unavailable retrieval path: {decision.paths}")
        paths = list(decision.paths)
        if state["plan"].get("needs_calculator") and "table" in self.available_paths:
            paths.append("table")
        return self._log("router", {
            "paths": list(dict.fromkeys(paths)), "decision": data,
            "llm_calls": state.get("llm_calls", 0) + 1,
            "usage": self._usage(state, usage),
        })

    def _retrieve(self, state: State) -> dict:
        query, document_ids = state["query"], state.get("document_ids")
        rankings: list[list[Evidence]] = []
        tool_calls = state.get("tool_calls", 0)
        scanned_documents = 0
        if document_ids is None:
            scanned_documents = len(self.tools.store.documents())
        else:
            scanned_documents = len(document_ids)
        traversal: Traversal | None = None
        paths = state["paths"]
        for path in paths:
            if tool_calls >= self.settings.agent.max_tool_calls:
                break
            if path == "dense":
                rankings.append(self.tools.search_dense(query, document_ids))
            elif path == "bm25":
                rankings.append(self.tools.search_bm25(query, document_ids))
            elif path == "table":
                rankings.append(self.tools.search_table(query, document_ids))
            elif path == "graph":
                seeds = [e.element_id for rank in rankings for e in rank[:3]]
                if not seeds:
                    lexical = self.tools.search_bm25(query, document_ids)
                    rankings.append(lexical)
                    seeds = [e.element_id for e in lexical[:3]]
                    tool_calls += 1
                for document_id in document_ids or []:
                    for kind, number in REFERENCE.findall(query):
                        if tool_calls >= self.settings.agent.max_tool_calls:
                            break
                        seeds.extend(self.tools.find_reference(document_id, f"{kind} {number}"))
                        tool_calls += 1
                if seeds and tool_calls < self.settings.agent.max_tool_calls:
                    graph_evidence, traversal = self.tools.search_graph(list(dict.fromkeys(seeds)), self.graph_depth)
                    rankings.append(graph_evidence)
            tool_calls += 1
        web_calls = state.get("web_calls", 0)
        if (state.get("iterations", 0) > 0 and self.profile.web and state["plan"].get("needs_tavily")
                and self.settings.web.enabled and web_calls < self.settings.agent.max_web_calls
                and tool_calls < self.settings.agent.max_tool_calls):
            results = self.tools.web_search_tavily(query)
            rankings.append([Evidence(evidence_id=item["url"], document_id=item["url"],
                                      page=0, element_id=item["url"], section_path=[],
                                      element_type="web", text=item["content"],
                                      score=item.get("score"), sources=["tavily"],
                                      source_url=item["url"], source_title=item["title"])
                             for item in results])
            tool_calls += 1
            web_calls += 1
        if not rankings:
            raise RuntimeError("No retrieval tools were available within the configured budget")
        return self._log("retrieval", {"rankings": [[e.model_dump() for e in rank] for rank in rankings],
                                       "traversal": traversal.model_dump() if traversal else None,
                                       "tool_calls": tool_calls, "web_calls": web_calls,
                                       "scanned_documents": scanned_documents})

    def _prepare(self, state: State) -> dict:
        rankings = [[Evidence.model_validate(e) for e in rank] for rank in state["rankings"]]
        guaranteed = [item for ranking in rankings
                      for item in ranking[:self.settings.retrieval.source_context_k]]
        fused = self.tools.retrieval.fuse(rankings)
        table_context: list[Evidence] = []
        expanded_tables: set[str] = set()
        tool_calls = state.get("tool_calls", 0)
        retrieval_limit = self.settings.agent.max_tool_calls - (1 if self.profile.calculator else 0)
        for item in fused:
            if (item.element_type != "table" or item.element_id in expanded_tables
                    or len(expanded_tables) >= self.settings.retrieval.parent_context_seeds
                    or tool_calls >= retrieval_limit):
                continue
            table_context.extend(self.tools.get_table_context(item.element_id))
            expanded_tables.add(item.element_id)
            tool_calls += 1
        if table_context:
            fused = self.tools.retrieval.fuse([fused, table_context])
        can_rerank = self.profile.rerank and tool_calls < retrieval_limit
        reranked = (self.tools.retrieval.rerank(state["query"], fused) if can_rerank
                    else fused[:self.settings.retrieval.rerank_top_k])
        tool_calls += 1 if fused and can_rerank else 0
        guaranteed_ids = {item.evidence_id for item in guaranteed}
        reranked = guaranteed + [item for item in reranked if item.evidence_id not in guaranteed_ids]
        if table_context:
            ranked_ids = {item.evidence_id for item in reranked}
            reranked += [item for item in table_context if item.evidence_id not in ranked_ids]
        hierarchical: list[Evidence] = []
        for seed in reranked[:self.settings.retrieval.parent_context_seeds]:
            if tool_calls >= retrieval_limit or seed.element_type == "web":
                break
            context = self.tools.get_parent_context(seed.element_id)
            tool_calls += 1
            source_order = context["element"]["order"]
            nearby = sorted((item for item in context["section"] if item["element_id"] != seed.element_id),
                            key=lambda item: abs(item["order"] - source_order))
            for item in nearby[:self.settings.retrieval.parent_context_neighbors]:
                hierarchical.append(Evidence(evidence_id=item["element_id"],
                                             document_id=item["document_id"], page=item["page"],
                                             element_id=item["element_id"],
                                             section_path=item["section_path"],
                                             element_type=item["element_type"], text=item["text"],
                                             sources=["hierarchical"]))
        known = {e.evidence_id for e in reranked}
        reranked += [e for e in hierarchical if e.evidence_id not in known]
        traversal = state.get("traversal")
        if traversal and traversal.get("nodes"):
            graph_items = self.tools.retrieval.graph_evidence(Traversal.model_validate(traversal))
            known = {e.evidence_id for e in reranked}
            reranked += [e for e in graph_items if e.evidence_id not in known]
        unique: list[Evidence] = []
        by_content: dict[tuple[str, str], Evidence] = {}
        for item in reranked:
            key = (item.document_id, item.text.strip())
            previous = by_content.get(key)
            if previous is None:
                by_content[key] = item
                unique.append(item)
            else:
                previous.sources = sorted(set(previous.sources + item.sources))
                if item.traversal_path and not previous.traversal_path:
                    previous.traversal_path = item.traversal_path
        packed: list[Evidence] = []
        budget = min(state["plan"]["context_budget"], self.settings.retrieval.context_tokens)
        for item in unique:
            item.citation_label = f"E{len(packed) + 1}"
            size = len(self.tokenizer.encode(self._evidence_text([item.model_dump()]))) + 2
            if size <= budget:
                packed.append(item)
                budget -= size
        return self._log("context", {"evidence": [e.model_dump() for e in packed],
                                     "context_tokens": state["plan"]["context_budget"] - budget,
                                     "tool_calls": tool_calls})

    def _evidence_text(self, evidence: list[dict]) -> str:
        names = {item["document_id"]: item["name"] for item in self.tools.store.documents()}
        return "\n\n".join(f"[{e.get('citation_label') or e['evidence_id']}] source "
                           f"{names.get(e['document_id'], e['document_id'])}, page {e['page']} "
                           f"section {' > '.join(e['section_path'])}: {e['text']}" for e in evidence)

    def _grade(self, state: State) -> dict:
        if not state.get("evidence"):
            grade = Grade(sufficient=False, needs_calculator=False,
                          reason="No evidence retrieved", rewritten_query=state["query"])
            usage = {}
        else:
            data, usage = self._invoke_json("grader", self.settings.prompts.grader.format(
                question=state["question"], evidence=self._evidence_text(state["evidence"])),
                Grade.model_json_schema())
            grade = Grade.model_validate(data)
        return self._log("grader", {"grade": grade.model_dump(),
                                    "llm_calls": state.get("llm_calls", 0) + (1 if state.get("evidence") else 0),
                                    "usage": self._usage(state, usage)})

    def _after_grade(self, state: State) -> str:
        if state["grade"]["sufficient"]:
            return "synthesize"
        if state.get("iterations", 0) < min(self.settings.agent.max_retries, self.settings.agent.max_iterations - 1) \
                and state.get("tool_calls", 0) < self.settings.agent.max_tool_calls:
            return "rewrite"
        return "synthesize"

    def _rewrite(self, state: State) -> dict:
        parts = [state["question"], state["grade"]["rewritten_query"].strip(),
                 *state["plan"].get("subquestions", [])]
        query = " ".join(dict.fromkeys(part for part in parts if part))
        return self._log("rewrite", {"query": query, "iterations": state.get("iterations", 0) + 1})

    def _synthesize(self, state: State) -> dict:
        evidence = [Evidence.model_validate(e) for e in state.get("evidence", [])]
        if not evidence:
            return self._log("synthesis", {"answer": "No answer", "citations": [],
                                           "calculations": [], "status": "insufficient_evidence"})
        usage = dict(state.get("usage", {}))
        calculations: list[dict] = []
        tool_calls = state.get("tool_calls", 0)
        llm_calls = state.get("llm_calls", 0)
        context = self._evidence_text(state["evidence"])
        calculator_needed = (state["plan"]["needs_calculator"]
                             or state.get("grade", {}).get("needs_calculator", False))
        if (self.profile.calculator and calculator_needed and
                tool_calls < self.settings.agent.max_tool_calls):
            raw_proposal, call_usage = self._invoke_json("calculator", self.settings.prompts.calculator.format(
                question=state["question"], plan=json.dumps(state["plan"]),
                grade=json.dumps(state.get("grade", {})), evidence=context),
                CalculationProposal.model_json_schema())
            proposal = CalculationProposal.model_validate(raw_proposal)
            usage = self._usage({"usage": usage}, call_usage)
            llm_calls += 1
            for proposed in proposal.calculations:
                expression = proposed.expression.strip()
                if not expression:
                    continue
                known_ids = {e.citation_label: e.evidence_id for e in evidence}
                ids = [known_ids[label] for label in proposed.operand_evidence_ids if label in known_ids]
                scale_constants = {Decimal(1), Decimal(100), Decimal(1000), Decimal(1000000)}
                operand_values = {
                    Decimal(token) for token in re.findall(r"(?<![\w.])[-+]?(?:\d+(?:\.\d+)?|\.\d+)", expression)
                    if Decimal(token) not in scale_constants
                }
                cited = [item for item in evidence if item.evidence_id in ids]
                cited_values = {num for item in cited for num in extract_evidence_numbers(item.text)}
                for value in operand_values - cited_values:
                    if any(v in cited_values for v in (
                        value * 100, value / 100, value * 1000, value / 1000,
                        value * 1000000, value / 1000000
                    )):
                        continue
                    source = next((item for item in evidence if (
                        value in extract_evidence_numbers(item.text) or
                        (value * 100) in extract_evidence_numbers(item.text) or
                        (value / 100) in extract_evidence_numbers(item.text) or
                        (value * 1000) in extract_evidence_numbers(item.text) or
                        (value / 1000) in extract_evidence_numbers(item.text) or
                        (value * 1000000) in extract_evidence_numbers(item.text) or
                        (value / 1000000) in extract_evidence_numbers(item.text)
                    )), None)
                    if source is not None and source.evidence_id not in ids:
                        ids.append(source.evidence_id)
                ids = list(dict.fromkeys(ids))
                try:
                    result = self.tools.calculate(expression, evidence, ids)
                    result["label"] = proposed.label
                    calculations.append(result)
                    tool_calls += 1
                except (ValueError, DivisionByZero) as exc:
                    self.trace.write("tool_error", tool="calculate", expression=expression,
                                     label=proposed.label, error=str(exc))
        synthesis_grade = dict(state.get("grade", {}))
        if calculations:
            synthesis_grade["sufficient"] = True
            synthesis_grade["calculator_results_available"] = True
        answer, call_usage = invoke_text(self.model, self.settings.prompts.synthesis.format(
            question=state["question"], grade=json.dumps(synthesis_grade),
            evidence=context + "\nCalculations: " + json.dumps(calculations)))
        usage = self._usage({"usage": usage}, call_usage)
        llm_calls += 1
        available = {e.citation_label or e.evidence_id: e.evidence_id for e in evidence}
        citations = [available[cid] for cid in re.findall(r"\[([^\]]+)\]", answer)
                     if cid in available]
        if answer.lower().startswith("no answer"):
            citations = []
        return self._log("synthesis", {"answer": answer, "citations": list(dict.fromkeys(citations)),
                                       "calculations": calculations, "usage": usage,
                                       "tool_calls": tool_calls,
                                       "llm_calls": llm_calls,
                                       "status": "unverified" if citations else "no_answer"})

    def _verify(self, state: State) -> dict:
        if state["answer"].strip().lower().startswith("no answer"):
            return self._log("verification", {"verification": Verification(
                valid=True, reason="Abstained", supported_citations=[]).model_dump(),
                "answer": "No answer", "citations": [],
                "status": "no_answer"})
        data, usage = self._invoke_json("verifier", self.settings.prompts.verifier.format(
            question=state["question"], evidence=self._evidence_text(state["evidence"]),
            calculations=json.dumps(state["calculations"]), answer=state["answer"]),
            Verification.model_json_schema(), verifier=True)
        verification = Verification.model_validate(data)
        known = {e["evidence_id"] for e in state["evidence"]}
        aliases = {e.get("citation_label") or e["evidence_id"]: e["evidence_id"]
                   for e in state["evidence"]}
        cited = set(state["citations"])
        supported = {aliases[label] for label in verification.supported_citations if label in aliases}
        valid = (verification.valid and bool(cited) and cited.issubset(known)
                 and cited.issubset(supported))
        verification.valid = valid
        return self._log("verification", {"verification": verification.model_dump(),
                                          "answer": state["answer"] if valid else "No answer",
                                          "citations": state["citations"] if valid else [],
                                          "status": "answered" if valid else "verification_failed",
                                          "llm_calls": state.get("llm_calls", 0) + 1,
                                          "usage": self._usage(state, usage)})

    def run(self, question: str, document_ids: str | list[str] | None = None) -> Answer:
        if not question.strip():
            raise ValueError("Question cannot be empty")
        started = time.perf_counter()
        state = self.graph.invoke(self._initial_state(question, document_ids),
                                  config={"recursion_limit": self.settings.agent.max_iterations * 6 + 8})
        return self._finish(question, state, started)

    def stream(self, question: str, document_ids: str | list[str] | None = None):
        if not question.strip():
            raise ValueError("Question cannot be empty")
        started = time.perf_counter()
        state: State = self._initial_state(question, document_ids)
        for update in self.graph.stream(state, stream_mode="updates",
                                        config={"recursion_limit": self.settings.agent.max_iterations * 6 + 8}):
            node, changes = next(iter(update.items()))
            state.update(changes)
            yield {"event": "step", "node": node,
                   "status": state.get("status"),
                   "evidence_count": len(state.get("evidence", [])),
                   "tool_calls": state.get("tool_calls", 0)}
        yield {"event": "answer", "data": self._finish(question, state, started).model_dump()}

    def _initial_state(self, question: str,
                       document_ids: str | list[str] | None) -> State:
        selected = ([document_ids] if isinstance(document_ids, str)
                    else list(dict.fromkeys(document_ids)) if document_ids else None)
        return {"question": question, "document_id": selected[0] if selected and len(selected) == 1 else None,
                "document_ids": selected, "query": question,
                "iterations": 0, "tool_calls": 0, "llm_calls": 0,
                "web_calls": 0, "usage": {},
                "paths": self.profile.paths,
                "plan": {"context_budget": self.settings.agent.context_tokens,
                         "needs_calculator": False, "needs_tavily": False,
                         "subquestions": []}}

    def _finish(self, question: str, state: State, started: float) -> Answer:
        answer = Answer(question=question, answer=state["answer"],
                        citations=state.get("citations", []),
                        evidence=[Evidence.model_validate(e) for e in state.get("evidence", [])],
                        traversal=Traversal.model_validate(state["traversal"]) if state.get("traversal") else None,
                        calculations=state.get("calculations", []), status=state["status"],
                        metadata={"latency_seconds": time.perf_counter() - started,
                                  "usage": state.get("usage", {}), "tool_calls": state.get("tool_calls", 0),
                                  "llm_calls": state.get("llm_calls", 0),
                                  "iterations": state.get("iterations", 0),
                                  "context_tokens": state.get("context_tokens", 0),
                                  "web_calls": state.get("web_calls", 0),
                                  "model": self.settings.llm.model,
                                  "profile": self.profile_name,
                                  "graph_depth_limit": self.graph_depth,
                                  "config_hash": hashlib.sha256(self.settings.model_dump_json().encode()).hexdigest()})
        answer.metadata["verification"] = state.get("verification")
        answer.metadata["selected_document_id"] = state.get("document_id")
        answer.metadata["selected_document_ids"] = state.get("document_ids")
        self.trace.write("answer", answer=answer.model_dump())
        return answer

    def close(self) -> None:
        self.tools.close()
