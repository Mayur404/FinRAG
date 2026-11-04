# Final Project Presentation — 7-Slide Content

**Group number:** [Add group number]  
**Presenters:** [Add names]

## Slide 1 — Financial Question Answering from Long Reports

**Title:** Evidence-Grounded Question Answering for Financial Reports

- **Application:** Answer questions using company filings such as 10-Ks, 10-Qs, 8-Ks, and earnings releases.
- **Problem:** Financial facts are spread across long narrative sections, tables, and footnotes. A language model can miss a relevant row or give an incorrect number or period.
- **Example:** “Did Verizon’s total debt rise in 2022?” requires finding and comparing the two year-end debt figures in its filing.
- **Why it matters:** Analysts need answers that are accurate, traceable to the filing, and quick to review.
- **Research paper:** *Financial Report Chunking for Effective Retrieval Augmented Generation* (Jimeno Yepes et al., 2024; arXiv:2402.05131).

**Visual:** Long filing → search for relevant evidence → concise, cited answer.

## Slide 2 — Dataset and Original Method

**Dataset: FinanceBench**

- Open-book financial question-answering benchmark; each question includes a reference answer and supporting evidence from a company report.
- The paper evaluated **80 reports and 141 questions** from the available FinanceBench documents.
- Our project used a reproducible subset of **18 filings, 882 PDF pages, and 50 questions**. This is a subset experiment, not the paper’s full dataset.
- The questions cover annual and quarterly filings, current reports, and earnings releases.
- No model training was performed: the benchmark questions were used to evaluate retrieval and answer generation.

**Original paper method — draw as a block diagram:**

```text
Financial report PDF
        ↓
Chipper layout extraction (titles, narrative text, tables)
        ↓
Element-based chunks; keep tables intact
        ↓
Add search context: text prefix or table description
        ↓
Dense embedding retrieval → top evidence chunks
        ↓
GPT-4 generates an answer from the retrieved evidence
```

The paper compares this structural approach with fixed-size chunking and reports retrieval and question-answering results.

## Slide 3 — Results Reported in the Original Paper

**Insert a direct screenshot from `baselinepaper.pdf`, PDF page 11:** crop **Table 5, “Q&A results”**. Keep the table title and the “Prefix & Table Description Chipper” row readable. Optionally include Table 4 beside it if the slide has room.

**Explain the key Table 5 result:**

- Prefix & Table Description Chipper: **41.13% GPT-4 evaluation accuracy** and **53.19% manual accuracy**.
- The paper evaluated **141 questions**, using GPT-4 comparisons and a separate manual evaluation.
- Table 4 also reports retrieval results for this variant: **67.38 page accuracy**, **0.514 ROUGE**, and **0.400 BLEU**.
- The paper’s evaluation setup and dataset differ from our local subset experiment, so its scores are context, not a direct benchmark comparison.

**Metric explanation:** Page accuracy checks whether retrieval reaches the evidence page. ROUGE and BLEU measure text overlap with reference evidence or answers. GPT-4 and manual evaluation judge answer correctness.

## Slide 4 — Stage 1: Baseline Implementation and Results

**What we implemented:**

- Extract document elements and preserve tables as individual chunks.
- Merge narrative elements up to about **2,048 characters**.
- Add the first two sentences as a text search prefix; use preceding context for tables.
- Embed with `multi-qa-mpnet-base-dot-v1`; retrieve by dense dot-product similarity.
- Use local `qwen3.5:4b` to generate an answer from the retrieved chunks.

**Implementation note:** The paper used Chipper and GPT-4. Our local baseline used a Chipper-style extraction pipeline with a cached Docling fallback where the Unstructured/Tesseract parser was unavailable, and local Qwen for generation. This is a paper-inspired implementation, not an exact reproduction.

**Our manual check:** **30/50 answers correct (60%)**. Page Hit@6 was **33/50 (66%)**. The manual count is reported separately from retrieval accuracy.

## Slide 5 — Stage 2: Proposed Modifications

**Why modify the baseline?** A single dense search can miss exact figures in tables, lose surrounding section context, or retrieve an irrelevant passage. Agentic follow-up searches may help when the first evidence set is incomplete.

**Modified pipeline — draw as two retrieval paths joining an agent loop:**

```text
PDF → Docling / TableFormer extraction
                  ↓
        ┌─────────┴─────────┐
        ↓                   ↓
Hierarchical search     Dense + BM25 search
leaf → parent context   RRF → BGE reranker
        └─────────┬─────────┘
                  ↓
        Fuse and deduplicate evidence
                  ↓
Agent plans searches → grades evidence → bounded follow-up search
                  ↓
        Draft answer → verify against evidence → cited response
```

- **Improvement 1:** Docling extraction with hierarchical child-to-parent context.
- **Improvement 2:** Dense retrieval plus number-preserving BM25, reciprocal-rank fusion, and cross-encoder reranking.
- **Improvement 3:** Combines the hierarchical and hybrid retrieval evidence.
- **Improvement 4:** Adds an agent that plans targeted queries, checks evidence coverage, retries within a two-round limit, and verifies the final response.

All four methods use local `qwen3.5:4b` for generation; Improvement 4 also uses it for planning, evidence grading, and verification.

## Slide 6: Evaluation Results

Manual answer counts were supplied for all five methods. Page accuracy is Page Hit@6: an exact match to a FinanceBench evidence page among the top six retrieved pages. ROUGE-L and BLEU-4 are computed against the reference answers and measure wording overlap.

| Method | Manual test (reported) | Page accuracy (Hit@6) | ROUGE-L F1 | BLEU-4 |
|---|---:|---:|---:|---:|
| Baseline | 30/50 (60%) | 33/50 (66%) | 0.0899 | 0.0200 |
| Hierarchical (Improvement 1) | 32/50 (64%) | n/a* | 0.1009 | 0.0217 |
| Hybrid BM25 (Improvement 2) | 29/50 (58%) | 29/50 (58%) | 0.0976 | 0.0172 |
| Combined (Improvement 3) | 35/50 (70%) | 29/50 (58%) | 0.0996 | 0.0193 |
| Agentic (Improvement 4) | 38/50 (76%) | 30/50 (60%) | 0.2135 | 0.0517 |

* Improvement 1 page accuracy is unavailable because the saved page-retrieval run failed to load its Hugging Face model offline. Manual counts were supplied as aggregate totals; no per-question labels are saved to independently verify them. Page Hit@6 checks one annotated evidence page, so it does not cap answer correctness. ROUGE/BLEU are wording-overlap scores, not correctness scores. See `COMPARISON_EVALUATION.md` for details.

## Slide 7: Conclusions and Key Learning

- Financial QA benefits from document structure: a useful number may appear in a table even when nearby narrative text does not state it.
- On the manual check, Improvement 4 scored highest at **38/50 (76%)**; the baseline had the highest available Page Hit@6 at **33/50 (66%)**.
- Results differ by metric: agentic scored highest on manual checks and text overlap, while the baseline led page retrieval. ROUGE and BLEU measure wording overlap, not factual correctness.
- **Limitations:** 50-question subset; paper parser/model differ from the local implementation; manual results are aggregate counts without per-question labels; Improvement 1 page-hit data is unavailable.
- **Next step:** record per-question human labels, restore Improvement 1 retrieval provenance, and evaluate on a larger FinanceBench sample.

**References**

1. Jimeno Yepes, A., You, Y., Milczek, J., Laverde, S., & Li, L. (2024). *Financial Report Chunking for Effective Retrieval Augmented Generation*. arXiv:2402.05131.
2. Islam, P. et al. (2023). *FinanceBench: A New Benchmark for Financial Question Answering*. arXiv:2311.11944.
