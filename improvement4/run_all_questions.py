"""Run the bounded agent over the 50-question FinanceBench subset."""
from __future__ import annotations

import json
import time
from pathlib import Path

from . import rag

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
RESULTS = OUT / "question_replies.json"
REVIEW = OUT / "question_replies_review.md"


def write_review(rows: list[dict], questions: list[dict]) -> None:
    expected = {item.get("financebench_id", ""): item.get("answer", "") for item in questions}
    lines = ["# FinanceBench Question and Answer Review — Improvement 4", "",
             "Improvement 4 uses bounded agent planning, iterative evidence retrieval and grading, answer drafting, and a citation-grounded verification pass. No grading is included in this review.", ""]
    number = 0
    for doc in [line.strip() for line in (ROOT / "data" / "subset.txt").read_text(encoding="utf-8-sig").splitlines() if line.strip()]:
        doc_rows = [x for x in rows if x["doc_name"] == doc]
        if not doc_rows:
            continue
        lines.extend([f"## {doc}", ""])
        for row in doc_rows:
            number += 1
            lines.extend([f"### {number}. {row['financebench_id']} · {row['elapsed_seconds']} seconds", "",
                          "**Question**", "", row["question"], "", "**Expected answer (FinanceBench)**", "",
                          expected.get(row["financebench_id"], ""), "", "**Generated answer (Improvement 4)**", "", row["answer"], ""])
            agent = row.get("agent", {})
            lines.extend(["**Agent status**", "",
                          f"- Evidence sufficient: {agent.get('evidence_sufficient', False)}",
                          f"- Verification supported: {agent.get('verification_supported', False)}",
                          f"- Retrieval rounds: {agent.get('retrieval_rounds', 0)}",
                          f"- Search queries: {'; '.join(agent.get('retrieval_queries', []))}", "",
                          "**Retrieved evidence**", ""])
            for source in row.get("sources", []):
                lines.append(f"- Rank {source['rank']} · Page {source.get('page') or 'unknown'} · {source['kind']} · {', '.join(source['methods'])}")
            if agent.get("verification_issues"):
                lines.extend(["", "**Verification notes**", ""])
                lines.extend(f"- {issue}" for issue in agent["verification_issues"])
            if row.get("error"):
                lines.extend(["", f"**Run error:** {row['error']}"])
            lines.extend(["", "---", ""])
    REVIEW.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    questions = json.loads((ROOT / "data" / "questions.json").read_text(encoding="utf-8"))
    rows: list[dict] = []
    if RESULTS.exists():
        existing = json.loads(RESULTS.read_text(encoding="utf-8"))
        rows = [row for row in existing if row.get("agent") and not row.get("error")]
    completed = {row["financebench_id"] for row in rows}
    for index, item in enumerate(questions, 1):
        ident = item.get("financebench_id", "")
        if ident in completed:
            print(f"[{index}/{len(questions)}] {ident}: already complete", flush=True)
            continue
        started = time.perf_counter()
        row = {"financebench_id": ident, "doc_name": item["doc_name"], "question": item["question"],
               "answer": "", "sources": [], "agent": {}, "elapsed_seconds": 0.0, "error": ""}
        try:
            row["answer"], row["sources"], row["agent"] = rag.answer(item["doc_name"], item["question"])
        except Exception as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
        row["elapsed_seconds"] = round(time.perf_counter() - started, 2)
        rows = [value for value in rows if value.get("financebench_id") != ident]
        rows.append(row)
        # Keep original benchmark ordering while allowing safe resume after interruption.
        order = {q.get("financebench_id", ""): i for i, q in enumerate(questions)}
        rows.sort(key=lambda value: order.get(value.get("financebench_id", ""), len(order)))
        RESULTS.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[{index}/{len(questions)}] {ident}: {row['elapsed_seconds']}s" +
              (f" ERROR: {row['error']}" if row["error"] else ""), flush=True)
        write_review(rows, questions)
    write_review(rows, questions)
    print(f"Saved {len(rows)} rows to {RESULTS} and {REVIEW}", flush=True)
