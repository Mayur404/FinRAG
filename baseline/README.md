# Base Paper Baseline: Prefix & Table Description (Chipper)

This separate implementation follows the paper's winning flat-chunk method: Unstructured `hi_res` element parsing, whole tables isolated as chunks, narrative elements merged up to 2,048 characters, first-two-sentence search prefixes for narrative chunks, preceding caption prefixes for table search text, MPNet embeddings with unnormalized dot-product retrieval, and top 10 raw chunks sent to the local Ollama generator. Search enrichment is not included in the text sent to the generator.

Parser caches, MPNet weights, and dense indexes are stored under `baseline/`.

**Parser environment note:** this Windows environment does not have the Tesseract executable required by Unstructured `hi_res`. To complete the benchmark, the ingestion command uses the existing per-page Docling extraction cache as an explicit fallback and records `docling-cached-fallback-tesseract-unavailable` in each index. The chunking, search representation, MPNet scoring, and top-10 retrieval are the baseline implementation; parser output is therefore a local proxy rather than a strict Unstructured parser reproduction until Tesseract is available.

```powershell
# Extract and index all 18 filings
.\.venv\Scripts\python.exe -m baseline ingest

# Ask one question (prints answer and the retrieved raw source chunks)
.\.venv\Scripts\python.exe -m baseline ask --doc-name AMD_2022_10K --question "What was AMD's total revenue in FY2022?"

# Answer all 50 benchmark questions and create JSON plus side-by-side Markdown
.\.venv\Scripts\python.exe -m baseline run-all
```

CUDA-enabled PyTorch, Unstructured PDF extras, SentenceTransformers, and a running Ollama server with `qwen3.5:4b` are required. The runner keeps generation uncapped (`num_predict=-1`) per the project's current answer-generation preference.
