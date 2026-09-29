# Deviations from the supplied paper

The supplied paper, *Financial Report Chunking for Effective Retrieval Augmented
Generation*, used 80 recovered FinanceBench reports and 141 questions. This
project preserves the official public FinanceBench release at revision
`cc39aeb4afdf33909ee1412188bf89035950c2eb`: 150 questions and 368 upstream
PDFs. The current testing corpus contains only AMD's and Boeing's 2022 10-Ks,
with 14 public questions between them. The two PDFs were selected from three
reports tied at seven questions each by shortest PDF length. This is a small
manual test subset, not the paper's 80-report/141-question setup or the full
84-report/150-question public set. No reproduction metrics are reported.

The paper used Weaviate, `multi-qa-mpnet-base-dot-v1` embeddings, GPT-4,
Unstructured Chipper parsing, and GPT-4 generated keyword and summary
representations. This project defaults to Chroma, Ollama
`qwen3-embedding:0.6b`, Ollama `qwen3.5:4b`, a separately configured
`qwen2.5:7b` verifier, and Docling. Element-aware chunks
follow the paper's title/table boundaries and 2,048-character merge target,
but do not use Chipper or generated keyword/summary variants. These choices
are configured and must not be described as an exact reproduction.

The generation prompt is a source-restricted citation prompt rather than the
paper's exact GPT-4 prompt, and the element representation is original parsed
text rather than the three Chipper keyword/summary/prefix representations.

The paper's page-level retrieval, maximum evidence ROUGE/BLEU, no-answer rate,
and QA judging are implemented against supplied ground truth. The automatic
judge defaults to the configured local LLM rather than GPT-4. Manual judging
is not automated or claimed. Stage 2 adds Neo4j navigation, hybrid retrieval,
and bounded agent steps that were not in the paper.

A two-report, 14-question Stage 2 evaluation was run on September 29, 2026.
Eight questions produced cited answers accepted by the evidence verifier and six
abstained. This diagnostic run is recorded in
`runs/evaluation_20260929T131414Z_stage2_element_L_81979e6d.jsonl`; it is not a
paper reproduction and no improvement over the paper is claimed.

The current default ingestion mode uses Docling heading and table extraction
on two reports, with OCR disabled for speed and table structure extraction
enabled. Only element chunks are embedded; fixed-size and hierarchical
strategies require a separate run with those strategies enabled. Neo4j indexing
and graph navigation are disabled. The configured local LangGraph profile still
performs live planning, routing among dense, BM25, and table retrieval, evidence grading,
bounded retry, calculation, synthesis, and verification. These answers must
not be presented as the paper reproduction or as Graph-RAG results. Re-enable
Neo4j before evaluating the graph architecture.

The native FinanceBench evidence list is retained for evaluation. Its zero-based
PDF page indices are converted to Docling's one-based PDF pages. For questions
with multiple gold passages, page hit means any annotated document/page is
retrieved, and maximum evidence ROUGE/BLEU is taken across the real annotated
passages. Manual website questions search the selected corpus; the evaluation
runner scopes retrieval to the question's annotated report. These conditions
must be distinguished in reported results. The dataset does not supply graph
hop-depth labels, so it cannot establish multi-hop recovery accuracy by itself.
