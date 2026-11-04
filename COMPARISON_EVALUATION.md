# FinanceBench Method Comparison

Manual answer checks and retrieval/text-overlap metrics for the same 50-question subset.

## Summary

| Method | Manual test (reported) | Page accuracy (Hit@6) | ROUGE-L F1 | BLEU-4 |
|---|---:|---:|---:|---:|
| Base paper | 30/50 (60.0%) | 33/50 (66.0%) | 0.0899 | 0.0200 |
| Hierarchical (Improvement 1) | 32/50 (64.0%) | n/a | 0.1009 | 0.0217 |
| Hybrid BM25 + reranker (Improvement 2) | 29/50 (58.0%) | 29/50 (58.0%) | 0.0976 | 0.0172 |
| Combined (Improvement 3) | 35/50 (70.0%) | 29/50 (58.0%) | 0.0996 | 0.0193 |
| Agentic (Improvement 4) | 38/50 (76.0%) | 30/50 (60.0%) | 0.2135 | 0.0517 |

## Metric definitions

- **Manual test (reported):** Counts and percentages supplied by you. I checked the arithmetic, but per-question manual labels were not supplied, so the answer-by-answer counts cannot be independently certified from the saved files.
- **Page accuracy (Hit@6):** At least one of the top six retrieved PDF pages exactly matches the FinanceBench evidence page. The benchmark page index is zero-based; the evaluator converts it to one-based PDF pages. This measures page retrieval, not answer correctness.
- **ROUGE-L F1:** Macro-average across 50 answers using token-level longest common subsequence.
- **BLEU-4:** Corpus BLEU with brevity penalty and add-one n-gram smoothing.
- Manual correctness, page accuracy, ROUGE, and BLEU are separate measurements. ROUGE and BLEU measure text overlap and cannot be derived from the manual scores or used as factual correctness scores.
- A manual answer-correctness rate can exceed Page Hit@6. Page Hit@6 only checks whether one annotated evidence page appears among the top six retrieved pages; a correct answer may be supported by another page or by evidence whose page was not the benchmark's single annotation.
- Improvement 1 page accuracy is unavailable: the saved retrieval record shows its page-retrieval recomputation failed because the Hugging Face model could not be fetched in the offline environment. No estimate is reported.

The exact answer text and the earlier model-assisted strict/loose judgments remain in [`evaluation/comparison_results.json`](evaluation/comparison_results.json). The manual test data is available only as aggregate counts.
