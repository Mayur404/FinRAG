"""Combined Improvement 1 hierarchical and Improvement 2 hybrid RAG.

Both retrievers run over their own precomputed indexes. Their evidence is
rank-fused, deduplicated, and jointly supplied to a single generator call.
"""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

from improvement1 import rag as hierarchical
from improvement2 import rag as hybrid

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


def docs():
    return hierarchical.docs()


def questions():
    return json.loads((DATA_DIR / "questions.json").read_text(encoding="utf-8"))


def _share_dense_model():
    """Keep one resident BGE embedder for both methods on the 8 GB GPU."""
    model = hierarchical._EMBEDDING_MODEL
    if model is None:
        hierarchical.embed(["warmup retrieval query"])
        model = hierarchical._EMBEDDING_MODEL
    hybrid._DENSE_MODEL = model
    hybrid._TOKENIZER = model.tokenizer


def warm_models():
    _share_dense_model()
    hybrid._ensure_reranker()
    payload = {"model": "qwen3.5:4b", "prompt": "Reply OK.", "stream": False,
               "think": False, "keep_alive": "30m",
               "options": {"temperature": 0, "num_predict": 1, "num_ctx": 16384, "num_gpu": 99}}
    request = urllib.request.Request("http://127.0.0.1:11434/api/generate",
        data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=180) as response:
        response.read()


def _normalize(text: str):
    return re.sub(r"\W+", " ", text.lower()).strip()


def retrieve(doc_name: str, question: str, top_k: int = 10):
    # Method 1: granular hierarchical leaf search, parent grouping, section expansion.
    tree_hits, tree_meta = hierarchical.retrieve(doc_name, question, top_k=10)
    tree_context = hierarchical.pack_context(tree_hits, tree_meta["chunks"], budget=3000)

    # Method 2: dense + number-preserving BM25, RRF, and cross-encoder reranking.
    hybrid_hits, _ = hybrid.retrieve(doc_name, question, top_k=6)

    fused = {}
    for method_name, hits in (("hierarchical", tree_context), ("hybrid_rerank", hybrid_hits)):
        for rank, hit in enumerate(hits, 1):
            text = str(hit.get("text", "")).strip()
            if not text:
                continue
            key = _normalize(text)
            if key not in fused:
                fused[key] = {"text": text, "page": hit.get("page"),
                              "kind": hit.get("kind", "NarrativeText"),
                              "id": hit.get("id", ""), "methods": [], "rrf_score": 0.0}
            item = fused[key]
            if method_name not in item["methods"]:
                item["methods"].append(method_name)
            item["rrf_score"] += 1.0 / (60 + rank)
            if item.get("page") is None:
                item["page"] = hit.get("page")
            # A precise table hit is useful metadata when equivalent text occurs
            # in a larger parent scope.
            if hit.get("kind") == "Table":
                item["kind"] = "Table"
    ranked = sorted(fused.values(), key=lambda item: item["rrf_score"], reverse=True)

    # Pack the merged evidence within the generator context window. Keep sources
    # whole so figures and table rows are not cut in the middle.
    packed = []
    token_budget = 8500
    used = 0
    for item in ranked:
        cost = hybrid._token_count(item["text"])
        if used + cost > token_budget:
            continue
        packed.append({**item, "rank": len(packed) + 1,
                       "text": f"[Retrieved by {', '.join(item['methods'])}; page {item.get('page') or 'unknown'}; {item['kind']}]\n{item['text']}"})
        used += cost
        if len(packed) >= top_k:
            break
    return packed


def generate(question: str, sources, model: str = "qwen3.5:4b"):
    source_text = "\n\n".join(f"{i} - {source['text']}" for i, source in enumerate(sources, 1))
    prompt = ("please answer the question below using the list of sources provided after the question. "
              "If the sources are insufficient, give your best answer and state uncertainty rather than refusing. "
              'The sources are listed after "Sources:".\n'
              f"Question: {question}\nSources:\n{source_text}")
    payload = {"model": model, "prompt": prompt, "stream": False, "think": False,
               "keep_alive": "30m", "options": {"temperature": 0, "seed": 0,
               "num_ctx": 16384, "num_gpu": 99, "num_predict": -1}}
    request = urllib.request.Request("http://127.0.0.1:11434/api/generate",
        data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=300) as response:
        answer = json.loads(response.read()).get("response", "")
    return re.sub(r"<think>.*?</think>", "", answer, flags=re.S).strip()


def answer(doc_name: str, question: str):
    sources = retrieve(doc_name, question)
    return generate(question, sources), sources
