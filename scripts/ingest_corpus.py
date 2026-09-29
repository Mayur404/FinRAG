"""Prepare the configured corpus without asking questions or running evaluations."""
from __future__ import annotations

import argparse
import json
import logging
import time
from datetime import datetime, timezone

from finance_rag.config import load_settings
from finance_rag.ingestion.corpus import CorpusIndexer
from finance_rag.ingestion.store import DocumentStore
from finance_rag.retrieval.search import RetrievalService


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()
    settings = load_settings(args.config)
    settings.paths.runs.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    log_path = settings.paths.runs / f"corpus_ingest_{stamp}.log"
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.StreamHandler(), logging.FileHandler(log_path, encoding="utf-8")],
                        force=True)
    result: dict = {"started_at": datetime.now(timezone.utc).isoformat(),
                    "corpus": str(settings.paths.corpus), "log": str(log_path)}
    started = time.perf_counter()
    try:
        store = DocumentStore(settings.paths.documents)
        retrieval = RetrievalService(settings, store)
        result.update(CorpusIndexer(settings, store, retrieval).sync())
        result["status"] = "completed"
        logging.info("Corpus ingestion completed: %s", result)
    except BaseException as exc:
        result.update(status="interrupted" if isinstance(exc, KeyboardInterrupt) else "failed",
                      error=str(exc))
        logging.exception("Corpus ingestion did not complete")
        raise
    finally:
        result["elapsed_seconds"] = time.perf_counter() - started
        (settings.paths.runs / f"corpus_ingest_{stamp}.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
