"""Ingest the baseline corpus, answer all benchmark questions, and write reviews."""
from __future__ import annotations

import json
import time
from pathlib import Path

from . import rag

OUT = Path(__file__).resolve().parent
RESULTS = OUT / "question_replies.json"
REVIEW = OUT / "question_replies_review.md"


def write_review(rows, expected):
    expected_by_id = {q.get("financebench_id", ""): q.get("answer", "") for q in expected}
    lines = ["# FinanceBench Question and Answer Review — Base Paper Baseline", "",
             "Generated replies are shown beside FinanceBench expected answers for manual review. No grading is included.", ""]
    number = 0
    for doc in rag.docs():
        doc_rows = [row for row in rows if row["doc_name"] == doc]
        if not doc_rows:
            continue
        lines.extend([f"## {doc}", ""])
        for row in doc_rows:
            number += 1
            lines.extend([f"### {number}. {row['financebench_id']} · {row['elapsed_seconds']} seconds", "",
                          "**Question**", "", row["question"], "",
                          "**Expected answer (FinanceBench)**", "", expected_by_id.get(row["financebench_id"], ""), "",
                          "**Generated answer (Base Paper Baseline)**", "", row["answer"], ""])
            if row.get("error"):
                lines.extend([f"**Run error:** {row['error']}", ""])
            lines.extend(["---", ""])
    REVIEW.write_text("\n".join(lines), encoding="utf-8")


def main():
    question_rows = rag.questions()
    names = rag.docs()
    print(f"Ingesting {len(names)} base-paper filings...", flush=True)
    for i, name in enumerate(names, 1):
        created = rag.ingest(name)
        print(f"[{i}/{len(names)}] {name}: {'indexed' if created else 'cached'}", flush=True)
    print(f"Warming MPNet and Ollama, then answering {len(question_rows)} questions...", flush=True)
    rag.warm_models()
    rows = []
    for i, item in enumerate(question_rows, 1):
        started = time.perf_counter()
        row = {"financebench_id": item.get("financebench_id", ""), "doc_name": item["doc_name"],
               "question": item["question"], "answer": "", "elapsed_seconds": 0.0, "error": ""}
        try:
            row["answer"], _sources = rag.answer(item["doc_name"], item["question"])
        except Exception as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
        row["elapsed_seconds"] = round(time.perf_counter() - started, 2)
        rows.append(row)
        RESULTS.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[{i}/{len(question_rows)}] {row['financebench_id']} — {row['elapsed_seconds']}s"
              + (f" ERROR: {row['error']}" if row["error"] else ""), flush=True)
    write_review(rows, question_rows)
    print(f"Saved {len(rows)} answers to {RESULTS} and {REVIEW}", flush=True)


if __name__ == "__main__":
    main()
