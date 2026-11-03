"""CLI for Improvement 4's bounded agent."""
from __future__ import annotations

import argparse
import json

from . import rag


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m improvement4")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("run-all", help="answer the 50 FinanceBench subset questions")
    ask = sub.add_parser("ask", help="answer one question with agent trace")
    ask.add_argument("--doc-name", required=True)
    ask.add_argument("--question", required=True)
    args = parser.parse_args()
    if args.command == "run-all":
        from .run_all_questions import main as run_all
        run_all()
        return
    import improvement1.rag as hierarchical
    import improvement2.rag as hybrid
    hierarchical.ingest(args.doc_name)
    hybrid.ingest(args.doc_name)
    rag.combined.warm_models()
    answer, sources, trace = rag.answer(args.doc_name, args.question)
    print(answer)
    print("\nAgent summary:", trace["agent"] if "agent" in trace else json.dumps(trace, ensure_ascii=False))
    for source in sources:
        print(f"\nE{source['rank']} Page {source.get('page') or 'unknown'} ({', '.join(source['methods'])})\n{source['text']}")


if __name__ == "__main__":
    main()
