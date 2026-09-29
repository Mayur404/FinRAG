"""Atomic local JSON storage for parsed documents, chunks, and metadata."""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from finance_rag.models import Chunk, Element


class DocumentStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, document_id: str, name: str, elements: list[Element], chunks: dict[str, list[Chunk]]) -> None:
        folder = self.root / document_id
        folder.mkdir(parents=True, exist_ok=True)
        self._write(folder / "meta.json", {"document_id": document_id, "name": name,
                                           "pages": max(e.page for e in elements)})
        self._write(folder / "elements.json", [e.model_dump() for e in elements])
        for strategy, entries in chunks.items():
            self._write(folder / f"{strategy}.json", [c.model_dump() for c in entries])

    @staticmethod
    def _write(path: Path, value: object) -> None:
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        temp.replace(path)

    def documents(self) -> list[dict]:
        return [json.loads(path.read_text(encoding="utf-8"))
                for path in self.root.glob("*/meta.json")]

    def delete(self, document_id: str) -> None:
        if not re.fullmatch(r"[0-9a-f]{64}", document_id):
            raise ValueError("Invalid document ID")
        folder = (self.root / document_id).resolve()
        if not folder.is_relative_to(self.root.resolve()):
            raise ValueError("Document path escapes storage root")
        if folder.exists():
            shutil.rmtree(folder)

    def elements(self, document_id: str) -> list[Element]:
        path = self.root / document_id / "elements.json"
        return [Element.model_validate(x) for x in json.loads(path.read_text(encoding="utf-8"))]

    def chunks(self, strategy: str, document_id: str | None = None) -> list[Chunk]:
        paths = ([self.root / document_id / f"{strategy}.json"] if document_id
                 else self.root.glob(f"*/{strategy}.json"))
        result: list[Chunk] = []
        for path in paths:
            if path.exists():
                result.extend(Chunk.model_validate(x) for x in json.loads(path.read_text(encoding="utf-8")))
        return result

    def element(self, element_id: str) -> Element:
        document_id = element_id.split(":", 1)[0]
        for element in self.elements(document_id):
            if element.element_id == element_id:
                return element
        raise KeyError(element_id)
