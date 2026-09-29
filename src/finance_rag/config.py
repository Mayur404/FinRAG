"""Validated, environment-aware research configuration."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Literal

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, model_validator


class Paths(BaseModel):
    data: Path
    runs: Path
    chroma: Path
    documents: Path
    corpus: Path
    benchmark: Path


class LLMSettings(BaseModel):
    provider: Literal["ollama", "groq"]
    model: str
    verifier_model: str | None = None
    base_url: str
    temperature: float = Field(ge=0, le=2)
    reasoning: bool
    timeout_seconds: int = Field(gt=0)
    num_ctx: int = Field(gt=0)


class EmbeddingSettings(BaseModel):
    provider: Literal["ollama", "sentence_transformers"]
    model: str
    base_url: str
    batch_size: int = Field(gt=0)
    timeout_seconds: int = Field(gt=0)


class ChunkSettings(BaseModel):
    base_sizes: list[int]
    element_target_characters: int = Field(gt=0)
    table_target_characters: int = Field(gt=0)
    hierarchical_parent_characters: int = Field(gt=0)
    tokenizer: str


class IngestionSettings(BaseModel):
    parser: Literal["docling", "pdfium_text"]
    strategies: list[str] = Field(min_length=1)
    docling_ocr: bool = False
    docling_table_structure: bool = True


class RetrievalSettings(BaseModel):
    stage1_top_k: int = Field(gt=0)
    top_k: int = Field(gt=0)
    per_source_k: int = Field(gt=0)
    fusion_k: int = Field(gt=0)
    reranker_model: str
    reranker_local_files_only: bool = False
    rerank_top_k: int = Field(gt=0)
    source_context_k: int = Field(ge=0)
    parent_context_seeds: int = Field(ge=0)
    parent_context_neighbors: int = Field(ge=0)
    context_tokens: int = Field(gt=0)
    collection_prefix: str


class GraphSettings(BaseModel):
    enabled: bool
    uri: str
    user: str
    password: str
    max_traversal_depth: int = Field(ge=0)
    max_nodes_per_query: int = Field(gt=0)
    max_edges_per_query: int = Field(gt=0)
    max_reference_resolution_calls: int = Field(ge=0)
    write_batch_size: int = Field(gt=0)


class AgentSettings(BaseModel):
    max_iterations: int = Field(gt=0)
    max_tool_calls: int = Field(gt=0)
    max_retries: int = Field(ge=0)
    max_web_calls: int = Field(ge=0)
    context_tokens: int = Field(gt=0)
    min_context_tokens: int = Field(gt=0)
    numeric_tolerance: float = Field(ge=0)


class WebSettings(BaseModel):
    enabled: bool
    provider: Literal["tavily"]
    tavily_api_key: str
    sec_user_agent: str
    timeout_seconds: int = Field(gt=0)


class APISettings(BaseModel):
    host: str
    port: int = Field(gt=0, lt=65536)
    default_profile: str


class Prompts(BaseModel):
    planner: str
    router: str
    reference_resolver: str
    grader: str
    synthesis: str
    calculator: str
    verifier: str
    judge: str


class ExperimentProfile(BaseModel):
    paths: list[Literal["dense", "bm25", "graph", "table"]]
    rerank: bool
    router: bool
    planner: bool
    grader: bool
    calculator: bool
    verifier: bool
    web: bool


class EvaluationSettings(BaseModel):
    profiles: dict[str, ExperimentProfile]


class Settings(BaseModel):
    paths: Paths
    ingestion: IngestionSettings
    llm: LLMSettings
    embeddings: EmbeddingSettings
    chunking: ChunkSettings
    retrieval: RetrievalSettings
    graph: GraphSettings
    agent: AgentSettings
    web: WebSettings
    api: APISettings
    prompts: Prompts
    evaluation: EvaluationSettings

    @model_validator(mode="after")
    def validate_budgets(self) -> "Settings":
        if self.agent.context_tokens > self.retrieval.context_tokens:
            raise ValueError("Agent context budget exceeds retrieval context budget")
        if self.agent.min_context_tokens > self.agent.context_tokens:
            raise ValueError("Minimum agent context budget exceeds its maximum")
        allowed_strategies = {"element", "hierarchical"} | {
            f"base_{size}" for size in self.chunking.base_sizes}
        if len(set(self.ingestion.strategies)) != len(self.ingestion.strategies) or not set(
                self.ingestion.strategies).issubset(allowed_strategies):
            raise ValueError("Ingestion strategies must be distinct configured chunk strategies")
        if self.api.default_profile not in self.evaluation.profiles:
            raise ValueError("API default profile is not configured")
        if "element" not in self.ingestion.strategies:
            raise ValueError("The question API requires the element retrieval strategy")
        if self.graph.enabled and self.ingestion.parser != "docling":
            raise ValueError("Graph mode requires the Docling parser for document structure")
        return self


def load_settings(config_path: Path | str = "config.yaml") -> Settings:
    path = Path(config_path).resolve()
    load_dotenv(path.parent / ".env")
    if not path.is_file():
        raise FileNotFoundError(f"Configuration not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Configuration must be a mapping")

    def expand(value: object) -> object:
        if isinstance(value, dict):
            return {k: expand(v) for k, v in value.items()}
        if isinstance(value, list):
            return [expand(v) for v in value]
        if isinstance(value, str):
            return re.sub(r"\$\{([A-Z0-9_]+)\}", lambda m: os.getenv(m[1], ""), value)
        return value

    raw = expand(raw)
    for key, value in raw["paths"].items():
        raw["paths"][key] = (path.parent / value).resolve()
    return Settings.model_validate(raw)
