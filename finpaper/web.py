"""Unified local web interface for the FinanceBench retrieval methods."""
from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
STATIC = Path(__file__).resolve().parent / "static"
MAX_BODY = 32_000
_MODEL_LOCK = threading.Lock()

METHODS = {
    "baseline": {"label": "Base paper", "description": "Structural chunks with dense MPNet retrieval."},
    "hierarchical": {"label": "Hierarchical · Improvement 1", "description": "Docling extraction with child-to-parent context."},
    "hybrid": {"label": "Hybrid BM25 · Improvement 2", "description": "Dense + BM25 search, reciprocal-rank fusion, and reranking."},
    "combined": {"label": "Combined · Improvement 3", "description": "Fuses hierarchical and hybrid retrieval evidence."},
    "agentic": {"label": "Agentic · Improvement 4", "description": "Plans searches, grades evidence, retries, and verifies the answer."},
}


def _documents() -> list[str]:
    path = ROOT / "data" / "subset.txt"
    return [line.strip() for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def _ensure_index(method: str, doc: str) -> None:
    """Create/reuse only the indexes required by the selected method."""
    if method == "baseline":
        from baseline import rag
        stem = rag.INDEX_DIR / doc
        if not (stem.with_suffix(".json").exists() and stem.with_suffix(".npy").exists()):
            rag.ingest(doc)
    elif method == "hierarchical":
        from improvement1 import rag
        if not (rag.INDEX_DIR / f"{doc}.json").exists() or not (rag.INDEX_DIR / f"{doc}.npy").exists():
            rag.ingest(doc)
    elif method == "hybrid":
        from improvement2 import rag
        if not (rag.INDEX_DIR / f"{doc}.json").exists() or not (rag.INDEX_DIR / f"{doc}.npy").exists():
            rag.ingest(doc)
    else:
        from improvement1 import rag as hierarchical
        from improvement2 import rag as hybrid
        for module in (hierarchical, hybrid):
            if not (module.INDEX_DIR / f"{doc}.json").exists() or not (module.INDEX_DIR / f"{doc}.npy").exists():
                module.ingest(doc)


def _run(method: str, doc: str, question: str) -> dict:
    if method not in METHODS:
        raise ValueError("Choose one of the available answer methods.")
    if doc not in _documents():
        raise ValueError("The selected filing is not in the FinanceBench subset.")
    if not question or len(question) > 8_000:
        raise ValueError("Enter a question (up to 8,000 characters).")

    started = time.perf_counter()
    with _MODEL_LOCK:
        _ensure_index(method, doc)
        if method == "baseline":
            from baseline import rag
            answer, sources = rag.answer(doc, question)
            agent = None
        elif method == "hierarchical":
            from improvement1 import rag
            answer, sources = rag.answer(doc, question)
            agent = None
        elif method == "hybrid":
            from improvement2 import rag
            answer, sources = rag.answer(doc, question)
            agent = None
        elif method == "combined":
            from improvement3 import rag
            answer, sources = rag.answer(doc, question)
            agent = None
        else:
            from improvement4 import rag
            answer, sources, record = rag.answer(doc, question)
            # Surface compact, user-facing run metadata, not the internal trace/drafts.
            agent = {
                "retrieval_rounds": record.get("retrieval_rounds", 0),
                "evidence_sufficient": record.get("evidence_sufficient"),
                "verification_supported": record.get("verification_supported"),
                "verification_issues": record.get("verification_issues", []),
                "retrieval_queries": record.get("retrieval_queries", []),
            }
    return {
        "method": METHODS[method]["label"], "document": doc, "answer": answer,
        "elapsed_seconds": round(time.perf_counter() - started, 2),
        "sources": [_source_for_ui(source, i) for i, source in enumerate(sources or [], 1)],
        "agent": agent,
    }


def _source_for_ui(source: dict, position: int) -> dict:
    text = str(source.get("text", ""))
    return {
        "rank": source.get("rank", position),
        "page": source.get("page", source.get("page_number")),
        "kind": source.get("kind", source.get("type", "Evidence")),
        "methods": source.get("methods", []),
        "score": source.get("score", source.get("rrf_score")),
        "text": text[:12_000], "truncated": len(text) > 12_000,
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "FinanceBenchUI/1.0"

    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/config":
            self._json({"documents": _documents(), "methods": METHODS})
            return
        files = {"/": "index.html", "/styles.css": "styles.css", "/app.js": "app.js"}
        filename = files.get(path)
        if filename:
            content_type = "text/html; charset=utf-8" if filename.endswith(".html") else (
                "text/javascript; charset=utf-8" if filename.endswith(".js") else "text/css; charset=utf-8")
            body = (STATIC / filename).read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/ask":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_BODY:
                raise ValueError("Request body is empty or too large.")
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("Request must be a JSON object.")
            self._json(_run(str(data.get("method", "")), str(data.get("document", "")),
                            str(data.get("question", "")).strip()))
        except Exception as exc:
            self._json({"error": str(exc)}, 500)

    def log_message(self, *_args) -> None:
        pass


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Run the unified local FinanceBench question UI.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: localhost only).")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        parser.error("The local UI only supports loopback addresses.")
    print(f"FinanceBench workspace: http://127.0.0.1:{args.port}", flush=True)
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
