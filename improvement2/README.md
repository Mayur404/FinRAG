# Improvement 2 — Hybrid Rerank

This folder contains an independent implementation of Docling/TableFormer extraction, flat ~500-token chunks, BGE dense retrieval, number-preserving BM25, RRF (`k=60`), BGE cross-encoder reranking, and Qwen answer generation. The already generated compatible Docling element cache is copied into this folder on first ingest; missing extractions are parsed locally with the same Docling settings.

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m improvement2.run_all_questions
```

The runner ingests all filings and writes `question_replies.json` and `question_replies_review.md`. The JSON is flushed after each answer so partial progress is retained.
