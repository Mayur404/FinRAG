# FinanceBench Method Comparison

Evaluation of the saved 50-question answer sets for the base-paper baseline and Improvements 1–4.

## Summary

| Method | Strict correctness | Loose correctness | Page Hit@1 | Page Hit@3 | Page Hit@6 | ROUGE-L F1 (macro) | BLEU-4 (corpus) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Base paper | 24/50 (48.0%) | 37/50 (74.0%) | 18/50 (36.0%) | 26/50 (52.0%) | 33/50 (66.0%) | 0.0899 | 0.0200 |
| Hierarchical (Improvement 1) | 17/50 (34.0%) | 40/50 (80.0%) | n/a | n/a | n/a | 0.1009 | 0.0217 |
| Hybrid BM25 + reranker (Improvement 2) | 17/50 (34.0%) | 37/50 (74.0%) | 14/50 (28.0%) | 24/50 (48.0%) | 29/50 (58.0%) | 0.0976 | 0.0172 |
| Combined (Improvement 3) | 21/50 (42.0%) | 41/50 (82.0%) | 3/50 (6.0%) | 22/50 (44.0%) | 29/50 (58.0%) | 0.0996 | 0.0193 |
| Agentic (Improvement 4) | 23/50 (46.0%) | 41/50 (82.0%) | 15/50 (30.0%) | 25/50 (50.0%) | 30/50 (60.0%) | 0.2135 | 0.0517 |

## Metric definitions

- **Strict correctness:** Qwen 3.5 4B judged that the answer covered all core reference facts, including material values, entity, direction, and period where relevant, with no material contradiction. Score is out of 50.
- **Loose correctness:** The judge found the central answer correct, allowing omission of secondary details but not a central contradiction. Score is out of 50.
- **Page Hit@k:** At least one of the top k retrieved physical pages matches the question's FinanceBench `evidence_page_num` after converting its zero-based index to a one-based PDF page. Missing gold pages are excluded (eligible denominator: 50/50). Prior computed page lists are reused for Baseline and Improvements 1–3; Improvement 4 uses its saved selected source list.
- **ROUGE-L F1:** Macro-average over 50 answers using token-level longest common subsequence; reported as 0–1.
- **BLEU-4:** Corpus BLEU with brevity penalty and add-one n-gram smoothing; reported as 0–1. Similarity metrics reward lexical overlap and do not establish factual correctness.
- The same local Qwen judge evaluated all five answers for a question in one call, using identical strict/loose rules. This is model-assisted evaluation, not a human audit.

## Per-question semantic judgments and page hits

`S` = strict pass, `L` = loose pass. Page fields show exact evidence-page hit at ranks 1 and 6 after converting FinanceBench's zero-based gold page to a one-based PDF page (`—` means the gold page was unavailable).

| # | FinanceBench ID | Baseline S/L | I1 S/L | I2 S/L | I3 S/L | I4 S/L | Page @1 (B / I1 / I2 / I3 / I4) | Page @6 (B / I1 / I2 / I3 / I4) |
|---:|---|---|---|---|---|---|---|
| 1 | financebench_id_00807 | ✗/✓ | ✗/✓ | ✗/✓ | ✗/✓ | ✗/✓ | ✗ / — / ✗ / ✗ / ✗ | ✗ / — / ✗ / ✗ / ✗ |
| 2 | financebench_id_00941 | ✗/✗ | ✓/✓ | ✗/✗ | ✓/✓ | ✗/✗ | ✗ / — / ✗ / ✗ / ✗ | ✗ / — / ✗ / ✓ / ✗ |
| 3 | financebench_id_01858 | ✓/✓ | ✗/✗ | ✓/✓ | ✓/✓ | ✓/✓ | ✓ / — / ✗ / ✗ / ✗ | ✓ / — / ✓ / ✓ / ✓ |
| 4 | financebench_id_01935 | ✗/✗ | ✓/✓ | ✓/✓ | ✓/✓ | ✓/✓ | ✗ / — / ✗ / ✗ / ✗ | ✓ / — / ✓ / ✗ / ✓ |
| 5 | financebench_id_01928 | ✗/✗ | ✓/✓ | ✓/✓ | ✓/✓ | ✗/✓ | ✗ / — / ✗ / ✗ / ✗ | ✗ / — / ✗ / ✗ / ✗ |
| 6 | financebench_id_01930 | ✗/✓ | ✗/✗ | ✗/✓ | ✗/✗ | ✗/✓ | ✗ / — / ✗ / ✗ / ✗ | ✗ / — / ✗ / ✗ / ✗ |
| 7 | financebench_id_00222 | ✗/✗ | ✗/✓ | ✗/✓ | ✗/✓ | ✓/✓ | ✗ / — / ✗ / ✗ / ✗ | ✗ / — / ✗ / ✗ / ✗ |
| 8 | financebench_id_00995 | ✓/✓ | ✓/✓ | ✓/✓ | ✓/✓ | ✓/✓ | ✗ / — / ✗ / ✗ / ✗ | ✗ / — / ✗ / ✓ / ✗ |
| 9 | financebench_id_01198 | ✗/✓ | ✓/✓ | ✓/✓ | ✓/✓ | ✗/✓ | ✓ / — / ✗ / ✗ / ✓ | ✓ / — / ✓ / ✓ / ✓ |
| 10 | financebench_id_00917 | ✓/✓ | ✗/✗ | ✗/✓ | ✗/✓ | ✗/✓ | ✗ / — / ✗ / ✗ / ✓ | ✓ / — / ✓ / ✓ / ✓ |
| 11 | financebench_id_01279 | ✓/✓ | ✗/✓ | ✓/✓ | ✗/✓ | ✓/✓ | ✗ / — / ✗ / ✗ / ✗ | ✗ / — / ✓ / ✗ / ✗ |
| 12 | financebench_id_00563 | ✓/✓ | ✓/✓ | ✗/✓ | ✓/✓ | ✓/✓ | ✗ / — / ✗ / ✗ / ✗ | ✓ / — / ✗ / ✓ / ✓ |
| 13 | financebench_id_00757 | ✗/✓ | ✗/✓ | ✗/✗ | ✗/✓ | ✓/✓ | ✗ / — / ✗ / ✗ / ✗ | ✗ / — / ✗ / ✓ / ✓ |
| 14 | financebench_id_00685 | ✗/✗ | ✗/✓ | ✗/✗ | ✗/✓ | ✗/✗ | ✗ / — / ✗ / ✗ / ✗ | ✗ / — / ✗ / ✗ / ✗ |
| 15 | financebench_id_01077 | ✗/✗ | ✗/✓ | ✗/✓ | ✗/✓ | ✗/✓ | ✓ / — / ✗ / ✗ / ✗ | ✓ / — / ✗ / ✗ / ✗ |
| 16 | financebench_id_01275 | ✓/✓ | ✗/✗ | ✓/✓ | ✓/✓ | ✓/✓ | ✗ / — / ✗ / ✗ / ✗ | ✓ / — / ✓ / ✓ / ✓ |
| 17 | financebench_id_00288 | ✓/✓ | ✓/✓ | ✗/✗ | ✓/✓ | ✓/✓ | ✓ / — / ✗ / ✗ / ✗ | ✓ / — / ✓ / ✓ / ✓ |
| 18 | financebench_id_00460 | ✗/✗ | ✗/✓ | ✗/✓ | ✗/✓ | ✗/✓ | ✗ / — / ✗ / ✓ / ✗ | ✓ / — / ✓ / ✓ / ✓ |
| 19 | financebench_id_01902 | ✗/✗ | ✗/✓ | ✗/✓ | ✗/✓ | ✗/✓ | ✗ / — / ✓ / ✗ / ✓ | ✓ / — / ✓ / ✓ / ✓ |
| 20 | financebench_id_00517 | ✓/✓ | ✓/✓ | ✓/✓ | ✗/✗ | ✗/✓ | ✗ / — / ✓ / ✗ / ✓ | ✓ / — / ✓ / ✓ / ✓ |
| 21 | financebench_id_01091 | ✓/✓ | ✓/✓ | ✗/✗ | ✓/✓ | ✓/✓ | ✗ / — / ✗ / ✗ / ✗ | ✗ / — / ✗ / ✗ / ✗ |
| 22 | financebench_id_00678 | ✗/✗ | ✗/✗ | ✗/✗ | ✗/✗ | ✓/✓ | ✗ / — / ✗ / ✗ / ✗ | ✗ / — / ✗ / ✗ / ✓ |
| 23 | financebench_id_01290 | ✗/✓ | ✗/✓ | ✗/✓ | ✗/✓ | ✗/✓ | ✗ / — / ✗ / ✗ / ✗ | ✗ / — / ✗ / ✗ / ✗ |
| 24 | financebench_id_00464 | ✓/✓ | ✓/✓ | ✓/✓ | ✓/✓ | ✗/✓ | ✓ / — / ✓ / ✗ / ✓ | ✓ / — / ✓ / ✓ / ✓ |
| 25 | financebench_id_00494 | ✓/✓ | ✗/✓ | ✓/✓ | ✓/✓ | ✗/✓ | ✓ / — / ✗ / ✗ / ✗ | ✓ / — / ✓ / ✓ / ✓ |
| 26 | financebench_id_00585 | ✗/✓ | ✗/✗ | ✗/✓ | ✗/✓ | ✓/✓ | ✗ / — / ✗ / ✗ / ✗ | ✓ / — / ✓ / ✗ / ✓ |
| 27 | financebench_id_00839 | ✓/✓ | ✓/✓ | ✓/✓ | ✓/✓ | ✗/✗ | ✗ / — / ✗ / ✗ / ✓ | ✓ / — / ✓ / ✗ / ✓ |
| 28 | financebench_id_00822 | ✓/✓ | ✓/✓ | ✓/✓ | ✓/✓ | ✓/✓ | ✓ / — / ✓ / ✗ / ✗ | ✓ / — / ✓ / ✓ / ✓ |
| 29 | financebench_id_00651 | ✗/✓ | ✗/✓ | ✗/✓ | ✗/✓ | ✗/✓ | ✓ / — / ✓ / ✗ / ✓ | ✓ / — / ✓ / ✓ / ✓ |
| 30 | financebench_id_01484 | ✗/✓ | ✗/✓ | ✗/✓ | ✗/✓ | ✓/✓ | ✗ / — / ✗ / ✗ / ✗ | ✓ / — / ✗ / ✗ / ✗ |
| 31 | financebench_id_01488 | ✓/✓ | ✓/✓ | ✓/✓ | ✓/✓ | ✓/✓ | ✓ / — / ✓ / ✓ / ✓ | ✓ / — / ✓ / ✓ / ✓ |
| 32 | financebench_id_01490 | ✓/✓ | ✓/✓ | ✓/✓ | ✓/✓ | ✓/✓ | ✓ / — / ✓ / ✓ / ✓ | ✓ / — / ✓ / ✓ / ✓ |
| 33 | financebench_id_01491 | ✓/✓ | ✓/✓ | ✓/✓ | ✓/✓ | ✓/✓ | ✓ / — / ✓ / ✗ / ✗ | ✓ / — / ✓ / ✓ / ✓ |
| 34 | financebench_id_01487 | ✗/✓ | ✗/✓ | ✗/✓ | ✓/✓ | ✗/✗ | ✗ / — / ✗ / ✗ / ✗ | ✓ / — / ✓ / ✓ / ✗ |
| 35 | financebench_id_00382 | ✓/✓ | ✗/✗ | ✗/✗ | ✗/✗ | ✓/✓ | ✗ / — / ✗ / ✗ / ✗ | ✓ / — / ✗ / ✗ / ✗ |
| 36 | financebench_id_01911 | ✗/✓ | ✗/✓ | ✗/✓ | ✗/✓ | ✗/✓ | ✓ / — / ✗ / ✗ / ✓ | ✓ / — / ✓ / ✗ / ✓ |
| 37 | financebench_id_01912 | ✓/✓ | ✗/✗ | ✗/✗ | ✗/✗ | ✗/✗ | ✗ / — / ✗ / ✗ / ✗ | ✓ / — / ✓ / ✓ / ✗ |
| 38 | financebench_id_01482 | ✓/✓ | ✗/✓ | ✗/✓ | ✗/✓ | ✗/✓ | ✓ / — / ✓ / ✗ / ✗ | ✓ / — / ✓ / ✓ / ✗ |
| 39 | financebench_id_01474 | ✓/✓ | ✓/✓ | ✓/✓ | ✓/✓ | ✓/✓ | ✓ / — / ✓ / ✗ / ✓ | ✓ / — / ✓ / ✓ / ✓ |
| 40 | financebench_id_01476 | ✓/✓ | ✓/✓ | ✓/✓ | ✓/✓ | ✓/✓ | ✓ / — / ✓ / ✗ / ✗ | ✓ / — / ✓ / ✓ / ✓ |
| 41 | financebench_id_00283 | ✗/✗ | ✗/✓ | ✗/✓ | ✗/✗ | ✗/✓ | ✓ / — / ✓ / ✗ / ✗ | ✓ / — / ✓ / ✓ / ✓ |
| 42 | financebench_id_00724 | ✓/✓ | ✗/✓ | ✗/✗ | ✓/✓ | ✗/✗ | ✗ / — / ✗ / ✗ / ✗ | ✗ / — / ✗ / ✗ / ✗ |
| 43 | financebench_id_02419 | ✗/✓ | ✗/✓ | ✗/✗ | ✗/✗ | ✗/✗ | ✓ / — / ✗ / ✗ / ✓ | ✓ / — / ✓ / ✓ / ✓ |
| 44 | financebench_id_00601 | ✓/✓ | ✗/✗ | ✗/✗ | ✗/✗ | ✓/✓ | ✓ / — / ✓ / ✗ / ✓ | ✓ / — / ✓ / ✓ / ✓ |
| 45 | financebench_id_00603 | ✗/✗ | ✗/✓ | ✗/✗ | ✗/✓ | ✗/✗ | ✗ / — / ✗ / ✗ / ✗ | ✓ / — / ✗ / ✗ / ✗ |
| 46 | financebench_id_00605 | ✗/✓ | ✗/✗ | ✗/✗ | ✗/✗ | ✗/✗ | ✗ / — / ✓ / ✗ / ✗ | ✗ / — / ✓ / ✓ / ✓ |
| 47 | financebench_id_00606 | ✗/✗ | ✗/✓ | ✗/✓ | ✗/✓ | ✗/✓ | ✗ / — / ✗ / ✗ / ✓ | ✓ / — / ✗ / ✓ / ✓ |
| 48 | financebench_id_00216 | ✗/✗ | ✗/✓ | ✗/✓ | ✗/✓ | ✓/✓ | ✗ / — / ✗ / ✗ / ✗ | ✗ / — / ✗ / ✗ / ✗ |
| 49 | financebench_id_00215 | ✓/✓ | ✗/✓ | ✗/✓ | ✗/✓ | ✗/✓ | ✗ / — / ✗ / ✗ / ✗ | ✗ / — / ✗ / ✗ / ✗ |
| 50 | financebench_id_00566 | ✗/✓ | ✗/✓ | ✗/✓ | ✗/✓ | ✓/✓ | ✗ / — / ✗ / ✗ / ✓ | ✗ / — / ✗ / ✗ / ✓ |

Detailed per-question labels, source pages, and text metrics are in [`evaluation/comparison_results.json`](evaluation/comparison_results.json).
