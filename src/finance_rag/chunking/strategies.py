"""Paper baseline and structure-aware chunks with retained provenance."""
from __future__ import annotations

import hashlib

import tiktoken

from finance_rag.config import ChunkSettings
from finance_rag.models import Chunk, Element


def _chunk(elements: list[Element], strategy: str, text: str, parent: str | None = None) -> Chunk:
    key = f"{strategy}:{','.join(e.element_id for e in elements)}:{text}"
    return Chunk(chunk_id=hashlib.sha256(key.encode()).hexdigest(),
                 document_id=elements[0].document_id,
                 pages=sorted({e.page for e in elements}), element_ids=[e.element_id for e in elements],
                 section_path=elements[0].section_path, element_type=elements[0].element_type,
                 text=text, strategy=strategy, parent_id=parent)


def fixed_chunks(elements: list[Element], size: int, tokenizer: str) -> list[Chunk]:
    if size <= 0:
        raise ValueError("Chunk size must be positive")
    encoding = tiktoken.get_encoding(tokenizer)
    tokens: list[int] = []
    owners: list[Element] = []
    for element in elements:
        encoded = encoding.encode(element.text + "\n")
        tokens.extend(encoded)
        owners.extend([element] * len(encoded))
    result: list[Chunk] = []
    for start in range(0, len(tokens), size):
        seen: set[str] = set()
        source: list[Element] = []
        for owner in owners[start:start + size]:
            if owner.element_id not in seen:
                source.append(owner)
                seen.add(owner.element_id)
        result.append(_chunk(source, f"base_{size}", encoding.decode(tokens[start:start + size])))
    return result


def _table_parts(text: str, target_characters: int) -> list[str]:
    lines = [line for line in text.splitlines() if line.strip()]
    if len(text) <= target_characters or len(lines) <= 2:
        return [text]
    header = lines[:2]
    parts: list[str] = []
    rows: list[str] = []
    for row in lines[2:]:
        candidate = "\n".join([*header, *rows, row])
        if rows and len(candidate) > target_characters:
            parts.append("\n".join([*header, *rows]))
            rows = []
        rows.append(row)
    if rows:
        parts.append("\n".join([*header, *rows]))
    return parts or [text]


def element_chunks(elements: list[Element], target_characters: int,
                   table_target_characters: int | None = None) -> list[Chunk]:
    output: list[Chunk] = []
    pending: list[Element] = []

    def flush() -> None:
        if pending:
            output.append(_chunk(pending[:], "element", "\n\n".join(e.text for e in pending)))
            pending.clear()

    for element in elements:
        if element.element_type in {"title", "section_header", "table"}:
            flush()
            if element.element_type == "table":
                for part in _table_parts(element.text,
                                         table_target_characters or target_characters):
                    output.append(_chunk([element], "element", part))
            else:
                pending.append(element)
            continue
        if pending and len("\n\n".join(e.text for e in pending)) >= target_characters:
            flush()
        pending.append(element)
    flush()
    return output


def hierarchical_chunks(elements: list[Element], target_characters: int,
                        table_target_characters: int | None = None) -> list[Chunk]:
    children = element_chunks(elements, target_characters, table_target_characters)
    parents: list[Chunk] = []
    group: list[Chunk] = []
    for child in children:
        if group and (child.section_path != group[0].section_path or
                      sum(len(c.text) for c in group) + len(child.text) > target_characters):
            parents.append(_parent(group))
            group = []
        group.append(child)
    if group:
        parents.append(_parent(group))
    for parent in parents:
        for child in children:
            if child.parent_id is None and set(child.element_ids).issubset(parent.element_ids):
                child.parent_id = parent.chunk_id
    return parents + children


def _parent(children: list[Chunk]) -> Chunk:
    pseudo = [Element(document_id=c.document_id, page=c.pages[0], element_id=eid,
                      element_type=c.element_type, section_path=c.section_path,
                      text=c.text, order=i)
              for i, c in enumerate(children) for eid in c.element_ids]
    return _chunk(pseudo, "hierarchical_parent", "\n\n".join(c.text for c in children))


def all_chunks(elements: list[Element], config: ChunkSettings) -> dict[str, list[Chunk]]:
    return selected_chunks(elements, config, [f"base_{size}" for size in config.base_sizes]
                           + ["element", "hierarchical"])


def selected_chunks(elements: list[Element], config: ChunkSettings,
                    strategies: list[str]) -> dict[str, list[Chunk]]:
    result: dict[str, list[Chunk]] = {}
    for strategy in strategies:
        if strategy == "element":
            result[strategy] = element_chunks(elements, config.element_target_characters,
                                              config.table_target_characters)
        elif strategy == "hierarchical":
            result[strategy] = hierarchical_chunks(elements, config.hierarchical_parent_characters,
                                                   config.table_target_characters)
        elif strategy.startswith("base_") and strategy[5:].isdigit() and int(strategy[5:]) in config.base_sizes:
            result[strategy] = fixed_chunks(elements, int(strategy[5:]), config.tokenizer)
        else:
            raise ValueError(f"Unknown chunk strategy: {strategy}")
    return result
