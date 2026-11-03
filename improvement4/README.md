# Improvement 4: Bounded Agentic FinanceBench RAG

Improvement 4 reuses Improvement 3's hierarchical plus hybrid dense/BM25 retrieval, with a bounded agent loop around it:

1. A planner creates up to three targeted searches and lists the facts needed to answer.
2. Both retrieval approaches run for each planned search. Results are rank-fused and deduplicated with page provenance.
3. An evidence grader checks whether the company, period, requested metric, and required facts are present. If not, it can request up to two focused follow-up searches in each of at most two rounds.
4. A synthesis step drafts an answer with evidence IDs; a verifier checks factual support and may provide a correction.

The agent uses the local Ollama `qwen3.5:4b` model and existing Improvement 1/2 indexes. Search planning, grading, verification, retrieval rounds, and failures are recorded per question in `question_replies.json`. No web search is used.

Run one question or the full 50-question subset from the repository root:

```powershell
.\.venv\Scripts\python.exe -m improvement4 ask --doc-name AMD_2022_10K --question "What was AMD's total revenue in FY2022?"
.\.venv\Scripts\python.exe -m improvement4 run-all
```

The resumable full run writes `question_replies.json` and `question_replies_review.md` in this folder.
