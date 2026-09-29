"""Docling PDF normalization; every element is traceable to a source page."""
from __future__ import annotations

import hashlib
from typing import Literal
from pathlib import Path

from finance_rag.models import Element


def parse_pdf(path: Path, parser: Literal["docling", "pdfium_text"],
              *, docling_ocr: bool = False,
              docling_table_structure: bool = True) -> tuple[str, list[Element]]:
    if not path.is_file() or path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected an existing PDF: {path}")
    if parser == "pdfium_text":
        return _parse_pdfium_text(path)
    if parser == "docling":
        return _parse_docling(path, docling_ocr, docling_table_structure)
    raise ValueError(f"Unknown PDF parser: {parser}")


def _parse_pdfium_text(path: Path) -> tuple[str, list[Element]]:
    import pypdfium2 as pdfium

    document_id = hashlib.sha256(path.read_bytes()).hexdigest()
    document = pdfium.PdfDocument(str(path))
    elements: list[Element] = []
    try:
        for index in range(len(document)):
            page = document[index]
            text_page = page.get_textpage()
            try:
                text = text_page.get_text_range().replace("\ufffe", "").strip()
            finally:
                text_page.close()
                page.close()
            if text:
                elements.append(Element(document_id=document_id, page=index + 1,
                                        element_id=f"{document_id}:{index}",
                                        element_type="text", section_path=[], text=text,
                                        order=index))
    finally:
        document.close()
    if not elements:
        raise ValueError(f"No extractable text in {path}; use the Docling parser")
    return document_id, elements


def _parse_docling(path: Path, do_ocr: bool,
                   do_table_structure: bool) -> tuple[str, list[Element]]:
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    document_id = hashlib.sha256(path.read_bytes()).hexdigest()
    pipeline_options = PdfPipelineOptions(do_ocr=do_ocr,
                                          do_table_structure=do_table_structure)
    converter = DocumentConverter(format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
    })
    result = converter.convert(path)
    doc = result.document
    sections: list[str] = []
    elements: list[Element] = []
    for order, (item, level) in enumerate(doc.iterate_items()):
        label = str(getattr(item, "label", "text")).split(".")[-1].lower()
        if label in {"section_header", "title"}:
            title = str(getattr(item, "text", "")).strip()
            if title:
                sections = sections[:max(0, int(level) - 1)] + [title]
        text = str(getattr(item, "text", "") or "").strip()
        if label == "table":
            text = item.export_to_markdown(doc=doc).strip()
        if not text:
            continue
        prov = getattr(item, "prov", None)
        if not prov:
            raise ValueError(f"Docling element {order} lacks page provenance")
        page = int(prov[0].page_no)
        elements.append(Element(document_id=document_id, page=page,
                                element_id=f"{document_id}:{order}", element_type=label,
                                section_path=list(sections), text=text, order=order,
                                label=getattr(item, "self_ref", None)))
    if not elements:
        raise ValueError(f"No page-provenanced elements parsed from {path}")
    return document_id, elements
