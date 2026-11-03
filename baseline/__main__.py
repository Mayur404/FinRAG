"""CLI for the base-paper baseline."""
from __future__ import annotations

import argparse

from . import rag


def main():
    parser = argparse.ArgumentParser(prog="python -m baseline")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("ingest", help="parse and index all 18 benchmark filings")
    ask = sub.add_parser("ask", help="answer a question using baseline retrieval")
    ask.add_argument("--doc-name", required=True)
    ask.add_argument("--question", required=True)
    ask.add_argument("--elements", help="optional pre-extracted elements JSON path (compatibility argument)")
    sub.add_parser("run-all", help="ingest and answer all 50 FinanceBench questions")
    args = parser.parse_args()
    if args.command == "ingest":
        for i, name in enumerate(rag.docs(), 1):
            print(f"[{i}/18] {name}: {'indexed' if rag.ingest(name) else 'cached'}", flush=True)
    elif args.command == "ask":
        if not (rag.INDEX_DIR / f"{args.doc_name}.json").exists():
            rag.ingest(args.doc_name)
        result, sources = rag.answer(args.doc_name, args.question)
        print(result)
        print("\nRetrieved sources:")
        for hit in sources:
            print(f"\n#{hit['rank']} · Page {hit.get('page') or 'unknown'} · {hit['kind']}\n{hit['text']}")
    else:
        from .run_all_questions import main as run_all
        run_all()


if __name__ == "__main__":
    main()
