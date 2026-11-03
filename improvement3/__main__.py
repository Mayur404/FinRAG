"""CLI for the combined retriever."""
from __future__ import annotations

import argparse

from . import rag


def main():
    parser = argparse.ArgumentParser(prog="python -m improvement3")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("run-all", help="answer all 50 FinanceBench questions")
    ask = sub.add_parser("ask", help="answer one question")
    ask.add_argument("--doc-name", required=True)
    ask.add_argument("--question", required=True)
    args = parser.parse_args()
    if args.command == "run-all":
        from .run_all_questions import main as run_all
        run_all()
        return
    import improvement1.rag as method1
    import improvement2.rag as method2
    method1.ingest(args.doc_name)
    method2.ingest(args.doc_name)
    rag.warm_models()
    answer, sources = rag.answer(args.doc_name, args.question)
    print(answer)
    for source in sources:
        print(f"\n#{source['rank']} Page {source.get('page') or 'unknown'} ({', '.join(source['methods'])})\n{source['text']}")


if __name__ == "__main__":
    main()
