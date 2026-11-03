# Improvement 3: Combined Hierarchical + Hybrid Retrieval

Each question is run through both existing retrieval methods:

1. Improvement 1 retrieves granular child passages, groups them by parent, and expands relevant sections within a context budget.
2. Improvement 2 retrieves with dense MPNet/BGE-compatible semantic search and BM25, fuses candidates with RRF, and reranks them with a cross-encoder.
3. Improvement 3 rank-fuses and deduplicates both evidence lists, retains page and method provenance, and calls Qwen once with the combined evidence.

The existing Improvement 1 and 2 indexes are reused; their source files and indexes remain independent.

```powershell
.\.venv\Scripts\python.exe -m improvement3 run-all
.\.venv\Scripts\python.exe -m improvement3 ask --doc-name AMD_2022_10K --question "What was AMD's total revenue in FY2022?"
```

The full benchmark run writes `question_replies.json` and `question_replies_review.md` in this directory.
