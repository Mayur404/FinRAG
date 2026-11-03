"""Improvement 2: Docling chunks with dense/BM25 RRF and cross-encoder reranking."""
from __future__ import annotations

import gc
import json
import math
import re
import urllib.request
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PDF_DIR = ROOT / "financebench" / "pdfs"
ELEMENT_DIR = ROOT / "improvement2" / "elements"
INDEX_DIR = ROOT / "improvement2" / "indexes"
MODEL_DIR = ROOT / "improvement2" / "models" / "huggingface"
CHUNK_VERSION = "flat-500-token-v1"
DOCLED_ELEMENTS = ROOT / "improvement1" / "elements"

_DENSE_MODEL = None
_RERANKER = None
_TOKENIZER = None
_INDEX_CACHE: dict[str, tuple[dict, np.ndarray]] = {}


def docs():
    return [x.strip() for x in (DATA_DIR / "subset.txt").read_text(encoding="utf-8-sig").splitlines() if x.strip()]


def questions():
    return json.loads((DATA_DIR / "questions.json").read_text(encoding="utf-8"))


def _ensure_dense():
    global _DENSE_MODEL, _TOKENIZER
    if _DENSE_MODEL is None:
        import os
        import torch
        from sentence_transformers import SentenceTransformer
        if not torch.cuda.is_available():
            raise RuntimeError("Improvement 2 requires CUDA for dense retrieval.")
        # Reuse the exact BGE checkpoint already downloaded for Improvement 1;
        # model weights are shared artifacts, while code and indexes stay isolated.
        dense_cache = ROOT / "improvement1" / "models" / "huggingface"
        os.environ.setdefault("HF_HOME", str(dense_cache))
        snapshot_root = dense_cache / "hub" / "models--BAAI--bge-base-en-v1.5" / "snapshots"
        snapshots = list(snapshot_root.iterdir()) if snapshot_root.exists() else []
        if not snapshots:
            raise FileNotFoundError("Cached BAAI/bge-base-en-v1.5 weights were not found.")
        _DENSE_MODEL = SentenceTransformer(str(snapshots[0]), device="cuda:0", local_files_only=True)
        _DENSE_MODEL.half()
        _TOKENIZER = _DENSE_MODEL.tokenizer
    return _DENSE_MODEL


def _token_count(text: str) -> int:
    _ensure_dense()
    return len(_TOKENIZER.encode(text, add_special_tokens=False))


def _embed(texts):
    model = _ensure_dense()
    return model.encode(texts, batch_size=64, convert_to_numpy=True,
                        show_progress_bar=len(texts) > 1, normalize_embeddings=True)


def _numeric_tokens(text: str) -> list[str]:
    # Keep common financial values (e.g. $32,502 and 14.76%) as single BM25 terms.
    return re.findall(r"\$?\d[\d,]*(?:\.\d+)?%?|[a-z0-9]+(?:[-'][a-z0-9]+)*", text.lower())


def _flush_text(chunks, parts, pages, section, doc_name):
    if not parts:
        return
    body = " ".join(parts).strip()
    if body:
        text = (section + "\n" + body).strip() if section else body
        chunks.append({"id": f"{doc_name}:c{len(chunks)}", "doc_name": doc_name,
                       "kind": "NarrativeText", "page": pages[0], "pages": sorted(set(pages)),
                       "section": section, "text": text, "search_text": text})
    parts.clear()
    pages.clear()


def make_chunks(doc_name: str, pages):
    """Create flat ~500-token chunks; tables stay intact and retain page provenance."""
    chunks = []
    section = ""
    parts: list[str] = []
    part_pages: list[int] = []
    count = 0
    active_page = None

    def flush():
        nonlocal count
        _flush_text(chunks, parts, part_pages, section, doc_name)
        count = 0

    for page in pages:
        page_no = int(page["page_number"])
        for element in page.get("elements", []):
            text = str(element.get("text", "")).strip()
            if not text:
                continue
            kind = element.get("type", "NarrativeText")
            if kind == "Title":
                flush()
                section = text[:300]
                active_page = page_no
                continue
            if kind == "Table":
                flush()
                # Keep the TableFormer Markdown untouched in the generator source.
                search_text = ((section + "\n") if section else "") + text
                chunks.append({"id": f"{doc_name}:c{len(chunks)}", "doc_name": doc_name,
                               "kind": "Table", "page": page_no, "pages": [page_no],
                               "section": section, "text": text, "search_text": search_text})
                active_page = page_no
                continue
            if active_page is not None and active_page != page_no:
                flush()
            active_page = page_no
            # Split at sentence boundaries, then pack to the target tokenizer length.
            sentences = re.split(r"(?<=[.!?])\s+", text)
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                sentence_tokens = _token_count(sentence)
                if sentence_tokens > 500:
                    flush()
                    token_ids = _TOKENIZER.encode(sentence, add_special_tokens=False)
                    for start in range(0, len(token_ids), 500):
                        fragment = _TOKENIZER.decode(token_ids[start:start + 500], skip_special_tokens=True).strip()
                        parts.append(fragment)
                        part_pages.append(page_no)
                        flush()
                    continue
                current_tokens = _token_count(" ".join(parts + [sentence])) if parts else sentence_tokens
                if parts and current_tokens > 500:
                    flush()
                parts.append(sentence)
                part_pages.append(page_no)
                count = current_tokens
    flush()
    return chunks


def _load_elements(doc_name: str):
    ELEMENT_DIR.mkdir(parents=True, exist_ok=True)
    target = ELEMENT_DIR / f"{doc_name}.json"
    if target.exists():
        data = json.loads(target.read_text(encoding="utf-8"))
        if data.get("source_parser") == "docling-tableformer-accurate-cuda-textlayer":
            return data
    # The filings have already been extracted with the same Docling/TableFormer
    # settings for Improvement 1. Copy that extraction cache into this method's
    # isolated cache and chunk it independently.
    source = DOCLED_ELEMENTS / f"{doc_name}.json"
    if source.exists():
        data = json.loads(source.read_text(encoding="utf-8"))
        if data.get("parser") == "docling-tableformer-accurate-cuda-textlayer":
            normalized = {"doc_name": doc_name, "source_parser": data["parser"], "pages": data["pages"]}
            target.write_text(json.dumps(normalized, ensure_ascii=False), encoding="utf-8")
            return normalized
    # Parse locally when a compatible cache is missing.
    pdf = PDF_DIR / f"{doc_name}.pdf"
    if not pdf.exists():
        raise FileNotFoundError(pdf)
    data = {"doc_name": doc_name, "source_parser": "docling-tableformer-accurate-cuda-textlayer",
            "pages": parse_docling(pdf)}
    target.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def parse_docling(pdf: Path):
    import os
    import torch
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
    from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from pypdf import PdfReader
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HOME", str(MODEL_DIR))
    options = PdfPipelineOptions(do_ocr=False, do_table_structure=True)
    options.table_structure_options.mode = TableFormerMode.ACCURATE
    options.accelerator_options = AcceleratorOptions(device=AcceleratorDevice.CUDA)
    converter = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)})
    with torch.inference_mode(), torch.autocast(device_type="cuda", dtype=torch.float16):
        document = converter.convert(str(pdf)).document
    by_page = {}
    for item, _level in document.iterate_items():
        label = str(getattr(item, "label", "")).split(".")[-1].lower()
        provenance = getattr(item, "prov", []) or []
        page_no = int(getattr(provenance[0], "page_no", 1) or 1) if provenance else 1
        if "table" in label:
            try:
                text = item.export_to_markdown(doc=document)
            except Exception:
                text = str(getattr(item, "text", "") or "")
            kind = "Table"
        else:
            text = str(getattr(item, "text", "") or "").strip()
            kind = "Title" if label in {"section_header", "title"} else "NarrativeText"
        if text.strip():
            by_page.setdefault(page_no, []).append({"type": kind, "text": text.strip(), "page_number": page_no})
    count = len(PdfReader(str(pdf)).pages)
    return [{"page_number": p, "text": "\n".join(e["text"] for e in by_page.get(p, [])),
             "elements": by_page.get(p, [])} for p in range(1, count + 1)]


def ingest(doc_name: str):
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    stem = INDEX_DIR / doc_name
    meta_path, vector_path = stem.with_suffix(".json"), stem.with_suffix(".npy")
    if meta_path.exists() and vector_path.exists():
        cached = json.loads(meta_path.read_text(encoding="utf-8"))
        if cached.get("chunk_version") == CHUNK_VERSION:
            return False
    data = _load_elements(doc_name)
    chunks = make_chunks(doc_name, data["pages"])
    if not chunks:
        raise RuntimeError(f"No searchable chunks for {doc_name}")
    vectors = _embed([c["search_text"] for c in chunks])
    for chunk in chunks:
        chunk["bm25_tokens"] = _numeric_tokens(chunk["search_text"])
    metadata = {"doc_name": doc_name, "chunk_version": CHUNK_VERSION,
                "dense_model": "BAAI/bge-base-en-v1.5", "chunks": chunks}
    np.save(vector_path, np.asarray(vectors, dtype=np.float32))
    meta_path.write_text(json.dumps(metadata, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    _INDEX_CACHE.pop(doc_name, None)
    return True


def _load_index(doc_name: str):
    if doc_name not in _INDEX_CACHE:
        meta = json.loads((INDEX_DIR / f"{doc_name}.json").read_text(encoding="utf-8"))
        vectors = np.load(INDEX_DIR / f"{doc_name}.npy", mmap_mode="r")
        _INDEX_CACHE[doc_name] = meta, vectors
    return _INDEX_CACHE[doc_name]


def _ensure_reranker():
    global _RERANKER
    if _RERANKER is None:
        import torch
        from sentence_transformers import CrossEncoder
        snapshot_root = MODEL_DIR / "hub" / "models--BAAI--bge-reranker-base" / "snapshots"
        snapshots = list(snapshot_root.iterdir()) if snapshot_root.exists() else []
        if not snapshots:
            raise FileNotFoundError("BGE reranker checkpoint is not present in improvement2/models.")
        _RERANKER = CrossEncoder(str(snapshots[0]), device="cuda:0", local_files_only=True,
            model_kwargs={"torch_dtype": torch.float16}, max_length=512)
    return _RERANKER


def retrieve(doc_name: str, question: str, top_k=6):
    from rank_bm25 import BM25Okapi
    metadata, matrix = _load_index(doc_name)
    chunks = metadata["chunks"]
    query = "Represent this sentence for searching relevant passages: " + question
    vector = _embed([query])[0]
    dense_scores = np.asarray(matrix @ vector)
    dense_ids = np.argsort(-dense_scores)[:50].tolist()
    tokenized = [c["bm25_tokens"] for c in chunks]
    bm25_scores = BM25Okapi(tokenized).get_scores(_numeric_tokens(question))
    lexical_ids = np.argsort(-bm25_scores)[:50].tolist()
    fused = {}
    for rank, idx in enumerate(dense_ids, 1):
        fused[idx] = fused.get(idx, 0.0) + 1.0 / (60 + rank)
    for rank, idx in enumerate(lexical_ids, 1):
        fused[idx] = fused.get(idx, 0.0) + 1.0 / (60 + rank)
    candidates = sorted(fused, key=fused.get, reverse=True)[:30]
    reranker = _ensure_reranker()
    pairs = [(question, chunks[i]["text"]) for i in candidates]
    scores = reranker.predict(pairs, batch_size=16, show_progress_bar=False,
                              convert_to_numpy=True, apply_softmax=False)
    reranked = sorted(zip(candidates, scores), key=lambda x: float(x[1]), reverse=True)[:top_k]
    hits = []
    for rank, (idx, score) in enumerate(reranked, 1):
        hits.append({**chunks[idx], "rank": rank, "score": float(score), "rrf_score": float(fused[idx])})
    return hits, metadata


def generate(question: str, hits, model="qwen3.5:4b"):
    source_text = "\n".join(f"{i} - {h['text']}" for i, h in enumerate(hits, 1))
    prompt = ("please answer the question below using the sources provided after the question. "
              "If the sources do not contain enough information, use your general knowledge to give the best answer you can, and be clear when you are uncertain. The sources are listed after \"Sources:\".\n"
              f"Question: {question}\nSources:\n{source_text}")
    body = json.dumps({"model": model, "prompt": prompt, "stream": False, "think": False,
        "keep_alive": "30m", "options": {"temperature": 0, "seed": 0, "num_ctx": 16384,
        "num_gpu": 99, "num_predict": -1}}).encode()
    request = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=body,
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=300) as response:
        answer = json.loads(response.read()).get("response", "")
    return re.sub(r"<think>.*?</think>", "", answer, flags=re.S).strip()


def answer(doc_name: str, question: str):
    hits, _metadata = retrieve(doc_name, question)
    return generate(question, hits), hits


def warm_models():
    _ensure_dense()
    _ensure_reranker()
    request = urllib.request.Request("http://127.0.0.1:11434/api/generate",
        data=json.dumps({"model": "qwen3.5:4b", "prompt": "Reply OK.", "think": False,
            "stream": False, "keep_alive": "30m", "options": {"num_predict": 1,
            "num_ctx": 16384, "num_gpu": 99}}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=180) as response:
        response.read()
