"""Generate replies for every benchmark question and save JSON and Markdown.

Run from the repository root with:
    python -m improvement1.run_all_questions
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from . import rag


OUTPUT = Path(__file__).resolve().parent / "question_replies.json"
REVIEW = Path(__file__).resolve().parent / "question_replies_review.md"


def write_review(rows, expected):
    expected_by_id = {q.get("financebench_id", ""): q.get("answer", "") for q in expected}
    lines = ["# FinanceBench Question and Answer Review — Improvement 1", "",
             "Generated replies are shown beside FinanceBench expected answers for manual review. No grading is included.", ""]
    number = 0
    for doc in rag.docs():
        doc_rows = [x for x in rows if x["doc_name"] == doc]
        if not doc_rows:
            continue
        lines.extend([f"## {doc}", ""])
        for row in doc_rows:
            number += 1
            lines.extend([f"### {number}. {row['financebench_id']} · {row['elapsed_seconds']} seconds", "",
                          "**Question**", "", row["question"], "",
                          "**Expected answer (FinanceBench)**", "", expected_by_id.get(row["financebench_id"], ""), "",
                          "**Generated answer (Improvement 1)**", "", row["answer"], ""])
            if row.get("error"):
                lines.extend([f"**Run error:** {row['error']}", ""])
            lines.extend(["---", ""])
    REVIEW.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    questions = rag.questions()
    print(f"Warming models, then answering {len(questions)} questions...", flush=True)
    rag.warm_models()

    rows = []
    for number, item in enumerate(questions, 1):
        started = time.perf_counter()
        row = {
            "financebench_id": item.get("financebench_id", ""),
            "doc_name": item["doc_name"],
            "question": item["question"],
            "answer": "",
            "elapsed_seconds": "",
            "error": "",
        }
        try:
            answer, _sources = rag.answer(item["doc_name"], item["question"])
            row["answer"] = answer
        except Exception as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
        row["elapsed_seconds"] = round(time.perf_counter() - started, 2)
        rows.append(row)
        OUTPUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[{number}/{len(questions)}] {row['financebench_id']} — {row['elapsed_seconds']}s"
              + (f" ERROR: {row['error']}" if row["error"] else ""), flush=True)

    print(f"Saved replies to {OUTPUT}", flush=True)
    write_review(rows, questions)
    print(f"Saved review to {REVIEW}", flush=True)


if __name__ == "__main__":
    main()
