"""Reproduction baseline for Prefix & Table Description (Chipper).

Uses Unstructured hi_res elements, flat 2,048-character element chunks,
search-only prefix/table-caption enrichment, MPNet dot-product retrieval, and
the same local Ollama generator used by the other methods.
"""
from __future__ import annotations

import gc
import json
import os
import re
import shutil
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "financebench" / "pdfs"
DATA_DIR = ROOT / "data"
ELEMENT_DIR = ROOT / "baseline" / "elements"
INDEX_DIR = ROOT / "baseline" / "indexes"
MODEL_DIR = ROOT / "baseline" / "models" / "huggingface"
PARSER_ID = "unstructured-hi-res-chipper-elements"
MODEL_ID = "sentence-transformers/multi-qa-mpnet-base-dot-v1"
CHUNK_CHARS = 2048


def docs():
    return [s.strip() for s in (DATA_DIR / "subset.txt").read_text(encoding="utf-8-sig").splitlines() if s.strip()]


def questions():
    path = DATA_DIR / "questions.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def parse_pdf(pdf: Path):
    """Extract Chipper-like semantic elements with Unstructured's hi_res path."""
    os.environ.setdefault("HF_HOME", str(MODEL_DIR))
    os.environ.setdefault("UNSTRUCTURED_HI_RES_MODEL_NAME", "yolox")
    from unstructured.partition.pdf import partition_pdf

    def docling_cache_fallback():
        cached_path = ROOT / "improvement1" / "elements" / f"{pdf.stem}.json"
        if not cached_path.exists():
            raise RuntimeError(
                "Unstructured hi_res needs Tesseract, and there is no cached "
                f"Docling extraction to fall back to for {pdf.name}."
            )
        cached = json.loads(cached_path.read_text(encoding="utf-8"))
        fallback = []
        for page in cached.get("pages", []):
            for element in page.get("elements", []):
                typ = element.get("type", "NarrativeText")
                kind = "Title" if typ == "Title" else "Table" if typ == "Table" else "NarrativeText"
                text = str(element.get("text", "")).strip()
                if text:
                    fallback.append({"type": kind, "text": text,
                                     "page_number": element.get("page_number", page.get("page_number"))})
        if not fallback:
            raise RuntimeError(f"Cached Docling extraction has no elements for {pdf.name}")
        return fallback, "docling-cached-fallback-tesseract-unavailable"

    # Avoid spending time rasterizing every page when the required OCR binary is
    # absent and a complete structural extraction cache is already available.
    if shutil.which("tesseract") is None:
        return docling_cache_fallback()

    try:
        elements = partition_pdf(
            filename=str(pdf), strategy="hi_res", infer_table_structure=True,
            include_page_breaks=False,
        )
    except Exception as exc:
        # Unstructured hi_res currently invokes Tesseract on these PDFs. If the
        # optional system binary is missing, use the locally cached layout-aware
        # Docling elements rather than silently degrading to plain text parsing.
        if "TesseractNotFoundError" not in type(exc).__name__:
            raise
        try:
            return docling_cache_fallback()
        except Exception as fallback_exc:
            raise fallback_exc from exc
    output = []
    for element in elements:
        text = str(getattr(element, "text", "") or "").strip()
        if not text:
            continue
        category = str(getattr(element, "category", "NarrativeText") or "NarrativeText")
        metadata = getattr(element, "metadata", None)
        page = getattr(metadata, "page_number", None) if metadata else None
        try:
            page = int(page) if page is not None else None
        except (TypeError, ValueError):
            page = None
        if category in {"Header", "Footer", "PageNumber", "PageBreak", "Image"}:
            continue
        if category == "Table":
            # Keep raw extracted table text in generator context. HTML is retained
            # when Unstructured exposes it, matching its structured-table output.
            text_as_html = getattr(metadata, "text_as_html", None) if metadata else None
            if text_as_html:
                text = str(text_as_html).strip()
            kind = "Table"
        elif category in {"Title", "SectionHeader"}:
            kind = "Title"
        elif category in {"Caption", "FigureCaption"}:
            kind = "Caption"
        else:
            kind = "NarrativeText"
        output.append({"type": kind, "text": text, "page_number": page})
    if not output:
        raise RuntimeError(f"Unstructured extracted no usable elements from {pdf.name}")
    return output, PARSER_ID


def load_or_parse(doc_name: str):
    ELEMENT_DIR.mkdir(parents=True, exist_ok=True)
    path = ELEMENT_DIR / f"{doc_name}.json"
    if path.exists():
        cached = json.loads(path.read_text(encoding="utf-8"))
        if cached.get("parser") == PARSER_ID and cached.get("elements"):
            return cached
    pdf = PDF_DIR / f"{doc_name}.pdf"
    if not pdf.exists():
        raise FileNotFoundError(pdf)
    elements, parser_used = parse_pdf(pdf)
    data = {"doc_name": doc_name, "parser": PARSER_ID,
            "extraction_backend": parser_used, "elements": elements}
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    gc.collect()
    return data


def first_two_sentences(text: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(sentences[:2]).strip()


def make_chunks(elements, doc_name: str, max_chars: int = CHUNK_CHARS):
    """Merge whole narrative elements up to target size; tables stay intact."""
    chunks = []
    pending = []
    pending_page = None
    after_table = False
    last_narrative = ""

    def flush():
        nonlocal pending, pending_page
        text = "\n\n".join(x["text"] for x in pending).strip()
        if text:
            chunks.append({"id": f"{doc_name}:c{len(chunks)}", "doc_name": doc_name,
                           "kind": "NarrativeText", "page": pending_page,
                           "text": text, "search_text": f"{first_two_sentences(text)} {text}".strip()})
        pending, pending_page = [], None

    for el in elements:
        kind, text = el["type"], el["text"].strip()
        page = el.get("page_number")
        if kind == "Title":
            flush()
            pending = [{"text": text}]
            pending_page = page
            after_table = False
            last_narrative = ""
            continue
        if kind == "Table":
            flush()
            caption = last_narrative if len(last_narrative) < 300 else ""
            chunks.append({"id": f"{doc_name}:c{len(chunks)}", "doc_name": doc_name,
                           "kind": "Table", "page": page, "text": text,
                           "search_text": (caption + "\n" + text).strip()})
            after_table = True
            last_narrative = ""
            continue
        # Captions are useful as table search descriptions, and are also retained
        # as ordinary source text when not immediately followed by a table.
        if kind == "Caption":
            kind = "NarrativeText"
        if after_table:
            flush()
            after_table = False
        candidate = "\n\n".join([*(x["text"] for x in pending), text]).strip()
        if pending and len(candidate) > max_chars:
            flush()
        if not pending:
            pending_page = page
        pending.append({"text": text})
        last_narrative = text
    flush()
    return chunks


_EMBEDDING_MODEL = None


def embed(texts):
    os.environ.setdefault("HF_HOME", str(MODEL_DIR))
    from sentence_transformers import SentenceTransformer
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError("The paper baseline is configured for CUDA MPNet embeddings.")
    local = (MODEL_DIR / "hub" / "models--sentence-transformers--multi-qa-mpnet-base-dot-v1").exists()
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        _EMBEDDING_MODEL = SentenceTransformer(MODEL_ID, device="cuda:0", local_files_only=local)
        _EMBEDDING_MODEL.half()
    return _EMBEDDING_MODEL.encode(texts, batch_size=64, convert_to_numpy=True,
                                   show_progress_bar=len(texts) > 1, normalize_embeddings=False)


def warm_models():
    embed(["warmup query"])
    payload = {"model": "qwen3.5:4b", "prompt": "Reply OK.", "stream": False,
               "think": False, "keep_alive": "30m",
               "options": {"temperature": 0, "num_predict": 1, "num_ctx": 16384, "num_gpu": 99}}
    request = urllib.request.Request("http://127.0.0.1:11434/api/generate",
        data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=180) as response:
        response.read()


def ingest(doc_name: str):
    import numpy as np
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    stem = INDEX_DIR / doc_name
    if stem.with_suffix(".npy").exists() and stem.with_suffix(".json").exists():
        metadata = json.loads(stem.with_suffix(".json").read_text(encoding="utf-8"))
        if metadata.get("parser") == PARSER_ID and metadata.get("model") == MODEL_ID:
            return False
    source = load_or_parse(doc_name)
    chunks = make_chunks(source["elements"], doc_name)
    if not chunks:
        raise RuntimeError(f"No searchable chunks for {doc_name}")
    vectors = embed([chunk["search_text"] for chunk in chunks])
    np.save(stem.with_suffix(".npy"), np.asarray(vectors, dtype="float32"))
    metadata = {"doc_name": doc_name, "parser": PARSER_ID,
                "extraction_backend": source.get("extraction_backend", PARSER_ID), "model": MODEL_ID,
                "similarity": "unnormalized_dot_product", "chunks": chunks}
    stem.with_suffix(".json").write_text(json.dumps(metadata, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return True


def retrieve(doc_name: str, question: str, top_k: int = 10):
    import numpy as np
    stem = INDEX_DIR / doc_name
    metadata = json.loads(stem.with_suffix(".json").read_text(encoding="utf-8"))
    query_vector = embed([question])[0]
    vectors = np.load(stem.with_suffix(".npy"), mmap_mode="r")
    scores = vectors @ query_vector
    order = np.argsort(scores)[::-1][:top_k]
    return [{**metadata["chunks"][int(i)], "rank": rank, "score": float(scores[int(i)])}
            for rank, i in enumerate(order, 1)]


def generate(question: str, sources, model: str = "qwen3.5:4b"):
    source_text = "\n".join(f"{i} - {source['text']}" for i, source in enumerate(sources, 1))
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
    sources = retrieve(doc_name, question, top_k=10)
    return generate(question, sources), sources
