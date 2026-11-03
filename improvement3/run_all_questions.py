"""Generate combined-method replies and write JSON/Markdown review files."""
from __future__ import annotations

import json
import time
from pathlib import Path

from . import rag

method1 = rag.hierarchical
method2 = rag.hybrid

OUT = Path(__file__).resolve().parent
RESULTS = OUT / "question_replies.json"
REVIEW = OUT / "question_replies_review.md"


def write_review(rows, expected):
    expected_by_id = {q.get("financebench_id", ""): q.get("answer", "") for q in expected}
    lines = ["# FinanceBench Question and Answer Review — Improvement 3", "",
             "Improvement 3 combines hierarchical parent expansion and hybrid reranked retrieval. Generated replies are shown beside FinanceBench expected answers; no grading is included.", ""]
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
                          "**Generated answer (Improvement 3)**", "", row["answer"], ""])
            if row.get("sources"):
                lines.extend(["**Retrieved evidence**", ""])
                for source in row["sources"]:
                    lines.extend([f"- Rank {source['rank']} · Page {source.get('page') or 'unknown'} · {source['kind']} · {', '.join(source['methods'])}"])
                lines.append("")
            if row.get("error"):
                lines.extend([f"**Run error:** {row['error']}", ""])
            lines.extend(["---", ""])
    REVIEW.write_text("\n".join(lines), encoding="utf-8")


def main():
    question_rows = rag.questions()
    names = rag.docs()
    print(f"Checking {len(names)} combined-method indexes...", flush=True)
    for index, name in enumerate(names, 1):
        # Each method preserves and validates its own independent index.
        left = method1.ingest(name)
        right = method2.ingest(name)
        print(f"[{index}/{len(names)}] {name}: hierarchical={'indexed' if left else 'cached'}, hybrid={'indexed' if right else 'cached'}", flush=True)
    print("Warming shared BGE, BGE reranker, and Ollama...", flush=True)
    rag.warm_models()
    rows = []
    for index, item in enumerate(question_rows, 1):
        started = time.perf_counter()
        row = {"financebench_id": item.get("financebench_id", ""), "doc_name": item["doc_name"],
               "question": item["question"], "answer": "", "sources": [],
               "elapsed_seconds": 0.0, "error": ""}
        try:
            row["answer"], row["sources"] = rag.answer(item["doc_name"], item["question"])
        except Exception as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
        row["elapsed_seconds"] = round(time.perf_counter() - started, 2)
        rows.append(row)
        RESULTS.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[{index}/{len(question_rows)}] {row['financebench_id']} — {row['elapsed_seconds']}s"
              + (f" ERROR: {row['error']}" if row["error"] else ""), flush=True)
    write_review(rows, question_rows)
    print(f"Saved {len(rows)} replies to {RESULTS} and {REVIEW}", flush=True)


if __name__ == "__main__":
    main()
