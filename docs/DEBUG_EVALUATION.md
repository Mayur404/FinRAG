# RAG debugging and evaluation report

## Root causes

The `No answer` symptom had several generic causes across the pipeline:

- Router output used an inconsistent field name, so valid decisions could be rejected.
- Website questions were not scoped to the report selected by the planner.
- Large Docling tables were embedded and reranked as single chunks, which displaced or truncated relevant rows.
- Reranking could discard a retrieval path's strongest result, and retry queries could lose useful wording from the original question.
- Stale evidence from failed retries displaced relevant evidence.
- The model could choose a 50-token context budget, producing an empty context.
- One calculator expression could not represent comparisons across several alternatives. Empty proposals were followed by unrestricted LLM arithmetic, while real calculator results could be ignored because of a stale grader decision.
- Calculator citations could omit a real operand source.
- Synthesis and verification could accept contradictory arithmetic or unsupported background claims.
- Evaluation could count an abstention as correct and did not normalize every abstention to `no_answer`.

The API to frontend mapping was checked and was not the cause. The streamed `answer` event supplies the `answer`, `status`, `evidence`, `citations`, and `metadata` fields read by the frontend. Exceptions are emitted as stream `error` events.

## Generic fixes

- Constrained live model output with schemas and retained raw responses in traces.
- Scoped retrieval to a real indexed document chosen from the corpus catalog.
- Split oversized Markdown tables into header preserving row groups and added hybrid dense plus BM25 table retrieval with real same table context expansion.
- Preserved configured top candidates per source, reranked with source and section metadata, removed stale retry evidence, and augmented rewritten queries with the original question and plan subquestions.
- Added configured context budget bounds and reserved a tool call for calculation.
- Replaced the single calculation proposal with a bounded list of labeled, evidence bound expressions. Missing operand citations are completed only by matching literal operands against retrieved evidence.
- Allowed the grader to request calculation, passed calculator results to synthesis, required concise evidence only answers, and used a configured larger local verifier model.
- Normalized evaluation output to `answered`, `no_answer`, or `error`, and made abstentions ineligible for QA correctness.

No evaluation question, expected answer, company specific answer, citation, or question ID is present in production prompts or application control flow.

## Final 14-question run

Input: `data/financebench_two_reports.jsonl`

Result: `runs/evaluation_20260929T131414Z_stage2_element_L_81979e6d.jsonl`

| ID | Question | Produced | Evidence | Supported | Citations | Seconds | Status |
|---|---|---:|---:|---:|---:|---:|---|
| financebench_id_00222 | Does AMD have a reasonably healthy liquidity profile based on its quick ratio for FY22? If the quick ratio is not relevant to measure liquidity, please state that and explain why. | No | 20 | N/A | No | 59.60 | no_answer |
| financebench_id_00995 | What are the major products and services that AMD sells as of FY22? | Yes | 9 | Yes | Yes | 39.41 | answered |
| financebench_id_01198 | What drove revenue change as of the FY22 for AMD? | Yes | 17 | Yes | Yes | 41.52 | answered |
| financebench_id_00917 | What drove operating margin change as of the FY22 for AMD? If operating margin is not a useful metric for a company like this, then please state that and explain why. | Yes | 21 | Yes | Yes | 69.42 | answered |
| financebench_id_01279 | Among operations, investing, and financing activities, which brought in the most (or lost the least) cash flow for AMD in FY22? | Yes | 18 | Yes | Yes | 49.42 | answered |
| financebench_id_00563 | From FY21 to FY22, excluding Embedded, in which AMD reporting segment did sales proportionally increase the most? | No | 18 | N/A | No | 43.01 | no_answer |
| financebench_id_00757 | Did AMD report customer concentration in FY22? | Yes | 23 | Yes | Yes | 60.61 | answered |
| financebench_id_00517 | Are there any product categories / service categories that represent more than 20% of Boeing's revenue for FY2022? | Yes | 18 | Yes | Yes | 57.01 | answered |
| financebench_id_01091 | Has Boeing reported any materially important ongoing legal battles from FY2022? | Yes | 22 | Yes | Yes | 60.10 | answered |
| financebench_id_00678 | Does Boeing have an improving gross margin profile as of FY2022? If gross margin is not a useful metric for a company like this, then state that and explain why. | No | 22 | N/A | No | 59.33 | no_answer |
| financebench_id_01290 | Who are the primary customers of Boeing as of FY2022? | No | 22 | N/A | No | 45.67 | no_answer |
| financebench_id_00464 | Is Boeing's business subject to cyclicality? | No | 15 | N/A | No | 18.63 | no_answer |
| financebench_id_00494 | What production rate changes is Boeing forecasting for FY2023? | No | 11 | N/A | No | 32.02 | no_answer |
| financebench_id_00585 | How does Boeing's effective tax rate in FY2022 compare to FY2021? | Yes | 19 | Yes | Yes | 39.26 | answered |

All 14 runs completed. Eight produced cited answers accepted by the verifier, six returned `No answer`, and none ended with an execution error. The external LLM judge matched seven predictions to the published answers. Its rejection of the supported effective tax rate answer is itself a remaining local model limitation, so this judge is not a substitute for manual review.

## Unanswerable control

Question: `What was AMD's total electricity consumption in megawatt-hours for FY2022?`

Result: `runs/unanswerable_evaluation_result.json`

The workflow retrieved 19 candidate passages, returned `No answer`, returned no citations, and completed in 47.90 seconds. The question exists only in this evaluation artifact.

## Remaining limitations

Six answerable benchmark questions still abstain. Their traces show remaining small local model failures in formula selection, grading, or verification. They remain `No answer` rather than being converted into unsupported responses. Neo4j is disabled for this two report local run, so these measurements cover dense, BM25, and table retrieval rather than graph traversal.
