# IMPLEMENTATION.md — Agentic Hybrid Graph-RAG for Financial Reports

## 1. Goal

Build a **website-only agentic financial research system**.

### Stage 1 — Reproduction
Reproduce the selected paper's financial-report RAG methodology on FinanceBench:
- fixed 128 / 256 / 512 token chunking
- element-aware chunking
- embeddings + retrieval
- top-k evidence
- LLM generation
- paper-aligned evaluation

### Stage 2 — Improvement
Extend the paper into an **agentic hybrid Graph-RAG** system:

```text
Question
  ↓
Planner
  ↓
Hybrid Retrieval Router
  ├── Chroma
  ├── BM25
  ├── Neo4j Graph
  └── Table Retrieval
  ↓
Fusion
  ↓
Reranker
  ↓
Relation / Cross-reference Expansion
  ↓
Context Budget Packing
  ↓
Evidence Grader
  ├── bounded retry / rewrite
  └── Synthesis
        ↓
    Calculator
        ↓
    Verification
        ↓
Answer + Citations
```

The paper's structure-aware chunking focuses on titles/text/tables and identifies element relationships and RAG configuration as future work. Use this as the motivation for Stage 2.

## 2. Technology Stack

- **LangGraph** — agent state, planner, router, loops, retries
- **LangChain** — LLM/tool integration, structured outputs
- **LlamaIndex** — local nodes, indexing, retrievers, hierarchical context
- **Docling** — local PDF parsing, tables, headings, provenance
- **Neo4j Community Edition** — local graph DB
- **Chroma** — local persistent vector DB
- **BM25** — lexical retrieval
- **SentenceTransformers / Ollama embeddings** — local embeddings
- **Local cross-encoder** — reranking
- **Ollama** — default local LLM
- **Groq** — optional LLM provider; must not be required
- **Tavily** — optional web search, off by default
- **SEC EDGAR** — optional financial-source tool
- **FastAPI + WebSocket/SSE** — backend/streaming
- **Frontend** — strictly follow `DESIGN.md`
- **JSONL** — traces

Core RAG components should run locally.

## 3. Local Models

Default development configuration:

```yaml
llm:
  provider: ollama
  model: qwen3.5:4b

embeddings:
  provider: ollama
  model: qwen3-embedding:0.6b
```

Implement a provider abstraction so Groq can be enabled later without changing the research logic.

## 4. Document Representation

Docling extracts:

```text
Document
 └─ Section
     ├─ Heading
     ├─ Paragraph
     ├─ Table
     ├─ Caption
     └─ List
```

Each element retains:

`document_id, page, element_id, element_type, section_path, text`

Tables should preserve headers, units, periods, and structure where possible.

## 5. Neo4j Document Graph

Create real graph entities/relations:

```text
CONTAINS
PARENT_OF
PRECEDES
SAME_SECTION
TABLE_CONTEXT
REFERENCES
REFERENCED_BY
```

Use Neo4j for **document navigation and multi-hop evidence**, not decorative storage.

## 6. Multi-Hop Cross-Reference Navigation

Must handle chains such as:

```text
A
 ↓
Note 7
 ↓
Note 12
 ↓
Item 8
 ↓
Exhibit B
 ↓
Schedule 3
```

Configuration:

```yaml
graph:
  max_traversal_depth: 6
  max_nodes_per_query: 30
```

Maintain:
`visited_nodes, visited_edges, traversal_depth, traversal_path`

to prevent cycles/unbounded traversal.

Resolve references with:
1. deterministic rules for note/item/exhibit/section identifiers;
2. LLM assistance only for ambiguous references.

Never invent a reference target.

## 7. Chunking

Implement:

```text
Base-128
Base-256
Base-512
Paper-style element-aware
Hierarchical parent-child
Optional semantic chunking
```

Keep provenance through every representation.

## 8. Hybrid Retrieval Router

This is a dedicated LangGraph node between planning and retrieval.

The router chooses retrieval paths based on the actual question:

```text
direct lookup      → Chroma + BM25
exact term/entity  → BM25-heavy
semantic/narrative → Chroma-heavy
numeric/table      → table + Chroma + BM25
comparison         → parallel retrieval
multi-hop          → Neo4j + Chroma
cross-reference    → Neo4j first
uncertain          → hybrid all
external/current   → local first → Tavily/SEC if required
```

Do not always call every retriever.

## 9. Retrieval Pipeline

```text
Planner
  ↓
Hybrid Retrieval Router
  ↓
selected:
  Chroma dense
  BM25 lexical
  Neo4j graph
  table search
  ↓
deduplicate
  ↓
rank fusion
  ↓
cross-encoder reranker
  ↓
graph/relation expansion
  ↓
token-budget packing
```

Record retriever and reranker scores.

## 10. Agentic Search Pattern

### Scan
Cheaply inspect candidate reports/sections.

### Deep Dive
Retrieve relevant pages/elements.

### Backtrack
Follow references/graph relations until:
- evidence is sufficient, or
- configured budget is exhausted.

The agent must make actual routing decisions.

## 11. Tools

```text
scan_corpus
preview_report
list_sections
read_page
read_section

search_dense
search_bm25
search_graph
search_table
get_parent_context
find_reference
follow_reference

calculate

web_search_tavily
fetch_web_result
search_edgar
get_sec_company_facts
```

All tools must be real, typed, validated, logged, and backed by actual data.

## 12. Planner / Grader / Verification

### Planner
Structured output:
`question_type, subquestions, retrieval_strategy, preferred_sources, needs_calculator, needs_tavily, context_budget`

### Evidence Grader
Checks:
- relevance
- completeness
- document/period correctness
- evidence coverage

May trigger only bounded query rewriting/retrieval retry.

### Calculator
LLM identifies operands/formula; calculator performs arithmetic.

### Verification
Checks:
- claims against evidence
- numbers
- units
- periods
- calculations
- citations

## 13. Tavily / External Search

```yaml
web:
  enabled: true
  default: false
  provider: tavily
```

Rules:
- local reports first;
- Tavily only when enabled/selected or external/current information is required;
- main FinanceBench headline experiments are local-only;
- web results are a separate condition;
- preserve actual URL/title/source metadata;
- failed Tavily calls must remain failures; never fabricate or silently switch providers.

## 14. Context Selection

Never blindly send top-k results.

```text
candidates
 → deduplicate
 → rerank
 → relation expansion
 → token-budget packing
 → final evidence
```

Use the same context budget for comparable experiments.

## 15. Stage 1 Evaluation

Reproduce:

```text
Base-128
Base-256
Base-512
Element-aware
```

Measure actual:
- chunk count
- page/evidence retrieval
- ROUGE/BLEU where applicable
- no-answer rate
- QA accuracy

Document differences in `docs/DEVIATIONS.md`.

## 16. Stage 2 Ablation

```text
A  Element-aware baseline
B  + graph/hierarchical context
C  + Chroma + BM25 + reranker
D  + hybrid retrieval router
E  + planning agent
F  + evidence grading/retry
G  + calculator + verification
H  + Tavily (separate condition)
```

Also evaluate cross-reference depth:

```text
0-hop
1-hop
2-hop
3-hop
4-hop
5-hop+
```

Measure:
`retrieval hit, QA accuracy, abstention, hops recovered, context tokens, latency, LLM/tool calls`

Only report experimentally measured results.

## 17. Website Only

The final product is a **website**, not a CLI.

Backend:

`FastAPI + LangGraph + LangChain + LlamaIndex + Neo4j + Chroma + Ollama`

Frontend:

`DESIGN.md`

Do not invent a competing UI when `DESIGN.md` exists.

Show only real:
- agent/tool status
- retrieved evidence
- graph traversal
- calculations
- Tavily usage
- citations
- final answer
- concise execution metadata

Never expose private chain-of-thought.

## 18. Project Structure

```text
src/finance_rag/
  ingestion/
  chunking/
  graph/
  retrieval/
  tools/
  agent/
  generation/
  evaluation/
  web/
  api/
  config.py
  models.py
  tracing.py

frontend/
data/
runs/
docs/
config.yaml
AGENTS.md
IMPLEMENTATION.md
```

## 19. Local Environment

Create a project-local environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

Never install project dependencies globally.

Check configured Ollama models before running.

Keep secrets in `.env`; commit only `.env.example`.

## 20. Build Order

1. `.venv` + configuration + secrets + tracing
2. Ollama/provider abstraction
3. Docling ingestion + provenance
4. Stage 1 reproduction
5. Neo4j graph + references
6. Chroma + BM25 + graph/table retrieval
7. Hybrid Retrieval Router
8. Reranking + relation expansion + context packing
9. LangGraph planner/grader/retry
10. Calculator + verification
11. Optional Tavily/SEC
12. FastAPI streaming
13. Frontend from `DESIGN.md`
14. Ablations + error analysis + paper results

Manual testing is performed by the project owner.
