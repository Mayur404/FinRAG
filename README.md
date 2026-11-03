# FinanceBench RAG Methods

This project implements and compares a paper-inspired financial-report retrieval-augmented question-answering baseline with four retrieval improvements, including a bounded agentic method.

## Project data

- **Benchmark:** 50 FinanceBench questions from 18 company filings (882 PDF pages).
- **Source documents:** the 18 PDFs used by the subset are included in `financebench/pdfs/`.
- **Paper:** `baselinepaper.pdf` is the source paper, *Financial Report Chunking for Effective Retrieval Augmented Generation* (arXiv:2402.05131).
- **Evaluation:** answer sets, detailed comparisons, and slide content are included. See `COMPARISON_EVALUATION.md` and `evaluation/comparison_results.json`.

This is a subset experiment, not a reproduction of the paper's full 80-report, 141-question evaluation. The baseline also uses a local parser fallback and Qwen instead of the paper's Chipper and GPT-4 setup; see `baseline/README.md` for details.

## Methods

| Folder | Method |
|---|---|
| `baseline/` | Element-based chunks, prefix and table-description search text, MPNet dense retrieval |
| `improvement1/` | Docling extraction and hierarchical child-to-parent retrieval |
| `improvement2/` | Dense and BM25 retrieval with rank fusion and cross-encoder reranking |
| `improvement3/` | Fused evidence from Improvements 1 and 2 |
| `improvement4/` | Bounded query planning, evidence grading, follow-up retrieval, and answer verification |

## Setup (Windows)

1. Install NVIDIA CUDA drivers and [Ollama](https://ollama.com/).
2. Download the local answer model:

   ```powershell
   ollama pull qwen3.5:4b
   ```

3. Create the project virtual environment and install the dependencies:

   ```powershell
   .\setup.ps1
   ```

   The retrieval models are downloaded from Hugging Face on first use and cached under each method folder. A CUDA-capable GPU is required by the current embedding and reranking implementations.

## Run

Run commands from the repository root with Ollama running:

```powershell
# Baseline: answer all 50 questions
.\.venv\Scripts\python.exe -m baseline run-all

# Improvement 1 and 2: answer all questions
.\.venv\Scripts\python.exe -m improvement1.run_all_questions
.\.venv\Scripts\python.exe -m improvement2.run_all_questions

# Combined and agentic methods: one question or all 50
.\.venv\Scripts\python.exe -m improvement3 ask --doc-name AMD_2022_10K --question "What was AMD's total revenue in FY2022?"
.\.venv\Scripts\python.exe -m improvement3 run-all
.\.venv\Scripts\python.exe -m improvement4 ask --doc-name AMD_2022_10K --question "What was AMD's total revenue in FY2022?"
.\.venv\Scripts\python.exe -m improvement4 run-all

# Recompute the comparison report after generating all methods' answers
.\.venv\Scripts\python.exe tools\evaluate_comparison.py
```

Each method writes `question_replies.json` and `question_replies_review.md` in its own folder. Improvement 4 also saves its bounded agent trace per question. The evaluator writes the summary to `COMPARISON_EVALUATION.md` and detailed results to `evaluation/comparison_results.json`.

## Key findings on this subset

- Baseline: 24/50 strict and 37/50 loose answer correctness.
- Combined (Improvement 3): 21/50 strict and 41/50 loose.
- Agentic (Improvement 4): 23/50 strict and 41/50 loose.
- No method wins every metric; the report documents the judge criteria and exact evidence-page matching convention.

Answer correctness is model-judged by a local Qwen 3.5 4B model, not human-audited. Page hit converts FinanceBench's zero-based evidence page index to a one-based PDF page. See the comparison report for full scores and limitations.

## References

- Jimeno Yepes, A., You, Y., Milczek, J., Laverde, S., & Li, L. (2024). *Financial Report Chunking for Effective Retrieval Augmented Generation*. arXiv:2402.05131.
- Islam, P. et al. (2023). *FinanceBench: A New Benchmark for Financial Question Answering*. arXiv:2311.11944.
