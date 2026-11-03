# Improvement 1: Docling + Hierarchical Chunking

Uses Docling with accurate TableFormer on CUDA, 180-word leaf chunks with company/form/year/section breadcrumbs, section/table parents, dense BGE retrieval, parent grouping, and a 3,000-token context budget.

The complete Improvement 1 implementation, CLI, and local Web UI are in this folder. Extraction cache, Hugging Face weights, and NumPy indexes are isolated here too.

```powershell
.\.venv\Scripts\python.exe -m finpaper ingest
.\.venv\Scripts\python.exe -m finpaper ask --doc-name AMD_2022_10K --question "What was AMD's total revenue in FY2022?"
.\.venv\Scripts\python.exe -m finpaper serve --port 8765
```
