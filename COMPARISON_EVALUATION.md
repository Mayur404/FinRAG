# FinanceBench Method Comparison

Manual answer checks and retrieval/text-overlap metrics for the same 50-question subset.

## Summary

| Method | Manual test (reported) | Page accuracy (all returned pages) | ROUGE-L F1 | BLEU-4 |
|---|---:|---:|---:|---:|
| Base paper | 30/50 (60.0%) | 37/50 (74.0%) | 0.0899 | 0.0200 |
| Hierarchical (Improvement 1) | 32/50 (64.0%) | 34/50 (68.0%) | 0.1009 | 0.0217 |
| Hybrid BM25 + reranker (Improvement 2) | 29/50 (58.0%) | 29/50 (58.0%) | 0.0976 | 0.0172 |
| Combined (Improvement 3) | 35/50 (70.0%) | 38/50 (76.0%) | 0.0996 | 0.0193 |
| Agentic (Improvement 4) | 38/50 (76.0%) | 38/50 (76.0%) | 0.2135 | 0.0517 |

## Metric definitions

- **Manual test (reported):** Counts and percentages supplied by the user. Arithmetic was checked, but per-question manual labels were not supplied, so answer-by-answer counts cannot be independently certified from the saved files.
- **Page accuracy (all returned pages):** A hit means at least one page in that method's complete returned source list exactly matches the FinanceBench evidence page. The benchmark page number is zero-based; it is converted to the one-based PDF page number. Returned list lengths differ: Baseline 10, Improvement 1 up to 10, Improvement 2 6, Improvement 3 10, and Improvement 4 12. This is full-list coverage, not a fixed-depth comparison.
- **ROUGE-L F1:** Macro-average over 50 answers using token-level longest common subsequence.
- **BLEU-4:** Corpus BLEU with brevity penalty and add-one n-gram smoothing.
- These are separate measurements. Page accuracy, ROUGE, and BLEU cannot be derived from manual correctness counts. ROUGE and BLEU measure wording overlap, not factual correctness. Manual answer correctness can exceed page accuracy because the benchmark gives a single annotated evidence page; another page may support the answer.

The page lists and per-question match flags are saved in [`evaluation/comparison_results.json`](evaluation/comparison_results.json). Manual counts remain aggregate reports without per-question labels.
