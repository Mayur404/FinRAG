"""Shared source-provenance and result models."""
from __future__ import annotations

from pydantic import BaseModel, Field


class Element(BaseModel):
    document_id: str
    page: int = Field(ge=1)
    element_id: str
    element_type: str
    section_path: list[str]
    text: str
    order: int
    label: str | None = None


class Chunk(BaseModel):
    chunk_id: str
    document_id: str
    pages: list[int]
    element_ids: list[str]
    section_path: list[str]
    element_type: str
    text: str
    strategy: str
    parent_id: str | None = None


class Evidence(BaseModel):
    evidence_id: str
    citation_label: str | None = None
    document_id: str
    page: int
    element_id: str
    section_path: list[str]
    element_type: str
    text: str
    score: float | None = None
    sources: list[str] = Field(default_factory=list)
    source_url: str | None = None
    source_title: str | None = None
    traversal_path: list[dict] = Field(default_factory=list)


class Traversal(BaseModel):
    nodes: list[str]
    edges: list[dict]
    paths: list[list[dict]]
    depth: int


class Answer(BaseModel):
    question: str
    answer: str
    citations: list[str]
    evidence: list[Evidence]
    traversal: Traversal | None = None
    calculations: list[dict] = Field(default_factory=list)
    status: str
    metadata: dict = Field(default_factory=dict)
