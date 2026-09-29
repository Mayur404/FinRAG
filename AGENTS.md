# AGENTS.md — Research + Engineering Rules

## Absolute rules

### 1. Never fabricate
Never invent or hardcode:
- answers
- evidence/citations/pages
- graph entities/edges
- retrieval results
- benchmark metrics
- latency/cost/token counts
- Tavily/SEC results
- agent decisions
- experiment outputs

Only actual source data or execution is valid.

`NOT RUN` > fake result.  
`UNAVAILABLE` > fake fallback.

### 2. No fake agents/tools
Planner, retrieval, Neo4j traversal, reranker, calculator, Tavily, grader, and verifier must do real work.

Never use fixed planner outputs, fake tool responses, fake citations, or fake traces.

### 3. No hardcoded research configuration
LLM/embedding provider and model, prompts, paths, chunk sizes, top-k, thresholds, retries, budgets, graph depth, Chroma collections, and feature flags must come from config.

### 4. Real provenance
Evidence preserves:
`document_id, page, element_id, section_path, element_type, text`

Graph traversal preserves real nodes/edges/path.
External evidence preserves real URL/title/source metadata.

### 5. Clean architecture

```text
ingestion → parsing/normalization
chunking  → chunk creation
graph     → Neo4j relationships
retrieval → Chroma/BM25/graph/hybrid/reranking
tools     → callable operations
agent     → LangGraph planning/routing/retries
generation→ synthesis
evaluation→ metrics/benchmarks
web       → Tavily/SEC
api       → FastAPI/streaming
frontend  → DESIGN.md
```

Framework roles:
`LangGraph=orchestration`
`LangChain=LLM/tools`
`LlamaIndex=RAG/indexing`
`Docling=parsing`
`Chroma=vector store`
`Neo4j=graph navigation`

### 6. Graph integrity
Create graph entities/edges only from actual parsed structure, deterministic relations, or actually resolved references.

Never invent a cross-reference target.

Enforce:
`max_traversal_depth, max_nodes_per_query, visited_nodes, visited_edges`

### 7. Tavily
Tavily is the supported optional web provider:
- off by default;
- never silently used in local-only experiments;
- every call logged with real source metadata;
- failures remain failures;
- never substitute an unconfigured provider;
- never fabricate results.

### 8. Bounded agents
Hard-limit graph iterations, tool calls, retries, web calls, graph depth, and context tokens.

### 9. Financial arithmetic
Use the calculator for arithmetic and verify it against evidence.
Never use unrestricted `eval()`.

### 10. Error handling
Never silently swallow errors or turn failures into success.
Do not silently change models, datasets, parsers, retrievers, vector stores, graph DBs, or providers.

### 11. Reproducibility
Log:
`config, model, dataset/question subset, timestamp, tools, evidence, traversal path, answer, metrics, latency, usage`

Use configuration-aware cache keys.

### 12. Evaluation integrity
Metrics must come from:
`actual predictions + actual ground truth`

Never manually enter benchmark numbers.
Do not overclaim improvement.
Keep failed runs for analysis.

### 13. Website only
Final product = website.
Do not make a CLI the primary interface.
Frontend must follow `DESIGN.md` when present.

### 14. UI integrity
Display only actual execution state/results.
Never fake progress, tool calls, graph traversal, citations, retrieved documents, or metrics.
Never expose private chain-of-thought.

### 15. Virtual environment
Use a project-local `.venv`. Do not install dependencies globally.
Keep secrets in `.env`, never commit secrets.

### 16. Code quality
Use type hints, focused functions, meaningful names, reusable modules, explicit errors, minimal global state, and no duplicated/dead/decorative code.

### 17. Research deviations
Record differences from the original paper in `docs/DEVIATIONS.md`.
Never call a modified setup an exact reproduction.

## Final rule

**Real code. Real data. Real graph edges. Real tool calls. Real measurements. No fabricated outputs, no hardcoded research results, no fake agent behavior, and clean modular code.**
