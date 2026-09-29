# Financial Evidence Lab

Website for source-grounded financial-report research. The backend uses Docling,
Chroma, BM25, Neo4j, LangGraph, LangChain, LlamaIndex nodes, a local cross-encoder,
and Ollama. Stage 1 evaluates fixed 128/256/512 token and element-aware chunks.
Stage 2 runs a bounded planner, retrieval router, reranker, graph expansion,
evidence grader, calculator, and verifier. No benchmark result is bundled.

## Start locally (PowerShell)

1. Ensure Ollama is running and the configured models are available:
   `ollama pull qwen3.5:4b` and `ollama pull qwen3-embedding:0.6b`.
2. Create the local environment if needed: `py -m venv .venv`.
3. Install only there: `.\.venv\Scripts\python.exe -m pip install -e .`.
4. Run `.\.venv\Scripts\python.exe scripts\ingest_corpus.py` to prepare the
   report corpus before asking questions. The script records progress under
   `runs/` and resumes from completed report checkpoints.
5. Start the website: `.\.venv\Scripts\python.exe -m uvicorn finance_rag.api.app:app --host 127.0.0.1 --port 8000`.
6. Put financial-report PDFs in `data/corpus/` (subfolders are supported), then
   open `http://127.0.0.1:8000` and ask a question. The first question indexes
   the files; later questions pick up added, changed, or removed PDFs.

The website has a question form and shows answers with their source passages.
The current two-report setup uses Docling for layout-aware headings, tables,
and page provenance, then indexes element chunks in Chroma. OCR is off because
these PDFs have embedded text; table structure extraction remains on. Neo4j
is disabled, so this setup does not run graph traversal. The configured
cross-encoder may download model weights. The website reports actual failures.

For the Graph-RAG research mode, set `graph.enabled` to `true`,
`ingestion.strategies` to the intended
chunk strategies, and `api.default_profile` to `G`. Start a Neo4j server at the
configured Bolt URI first; `docker-compose --env-file .env up -d` is one option.
Changing these settings makes the corpus reindex under a new configuration.

For FinanceBench evaluation, put the JSONL file at the configured
`paths.benchmark` location. The native public FinanceBench schema is supported,
including all nested evidence entries and conversion from zero-based evidence
pages to one-based PDF pages. Flat rows with `question`, `answer`, `doc_name`
(matching a corpus PDF stem) or `document_id`, plus optional `page_number` and
`evidence_text`, are also supported. The research evaluation API remains available at
`POST /api/evaluate`; it indexes the corpus before a run. Every question,
including failures, is recorded under `runs/`. Profile H requires explicitly
enabling Tavily in `config.yaml` and setting its key; it is a separate condition.

Configuration is in `config.yaml`. Credentials use `.env` substitutions. Tavily
and SEC sources are disabled unless `web.enabled` is set to `true`. Main
FinanceBench runs should remain local-only. Chroma and parsed documents are
stored under `data/`, execution traces under `runs/`.

## Prepared FinanceBench data

The official repository is cloned under `data/financebench-source/`. Its 150
public questions are preserved in `data/financebench.jsonl`. The current corpus
contains two reports, `AMD_2022_10K.pdf` and `BOEING_2022_10K.pdf`, selected
from the three reports tied for the most public questions (seven each) by PDF
length. Their 14 original question rows are copied unchanged to
`data/financebench_two_reports.jsonl`. No questions or answers are coded into
the application. Only the two PDFs are ingested; answers and evidence annotations
are not retrieval inputs.

The pinned source revision, file hashes, and selected reports are recorded in
`data/financebench_preparation.json`. Once Ollama and its embedding model are
running, ingestion can be started or resumed without any QA execution:

```powershell
.\.venv\Scripts\python.exe scripts\ingest_corpus.py
```

Completed reports are checkpointed in `data/corpus_index.json`; ingestion logs
and its actual completion or failure status are written under `runs/`. Wait for
ingestion to finish before asking questions. Restart the website after changes
to application code.

Use [the two-report manual guide](docs/FINANCEBENCH_TWO_REPORT_TESTING.md) for
the 14 questions whose reports are indexed. The
[complete manual question guide](docs/FINANCEBENCH_MANUAL_TESTING.md) retains
all 150 original questions and answers, including reports outside this corpus. The
[complete question catalog](docs/financebench_manual_questions.csv) contains all
150 questions for manual comparison. No QA tests were run during preparation.

## Research boundaries

The source paper is `financepaper.pdf`. This is a methodological adaptation,
because its original GPT-4, Weaviate, Chipper, and specific source corpus are
not present. See [deviations](docs/DEVIATIONS.md). Results must be generated
from the files you provide; none are prefilled.
