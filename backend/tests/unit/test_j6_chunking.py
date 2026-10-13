import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.rag.chunking import MAX_CHARS, ChunkRecord, chunk_pages
from app.rag.text_extraction import ExtractedPageRecord


def _page(
    source_id: str = "ammc-source",
    page_number: int = 1,
    text: str = "Une phrase financière suffisamment longue pour être conservée dans un chunk.",
    status: str = "ok",
) -> ExtractedPageRecord:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return ExtractedPageRecord(
        source_id=source_id,
        title="Titre",
        authority="ammc",
        language="fr",
        categories=["market_basics"],
        page_number=page_number,
        page_count=page_number,
        document_hash="a" * 64,
        text=text,
        text_sha256=digest,
        raw_char_count=len(text),
        clean_char_count=len(text),
        word_count=len(text.split()),
        extraction_status=status,
        warnings=["low_text"] if status == "low_text" else [],
    )


def test_short_page_is_one_cited_chunk_with_source_hash() -> None:
    chunks, audit = chunk_pages([_page()])
    chunk = chunks[0]
    assert len(chunks) == 1
    assert chunk.page_start == chunk.page_end == 1
    assert chunk.page_numbers == [1]
    assert chunk.source_page_text_sha256 == _page().text_sha256
    assert chunk.text_sha256 == hashlib.sha256(chunk.text.encode("utf-8")).hexdigest()
    assert audit["chunks_total"] == 1


def test_empty_and_extraction_error_pages_create_no_chunks() -> None:
    pages = [
        _page(page_number=1, text="", status="empty"),
        _page(page_number=2, text="", status="extraction_error"),
    ]
    chunks, audit = chunk_pages(pages)
    assert chunks == []
    assert audit["pages_empty_skipped"] == 1
    assert audit["pages_error_skipped"] == 1


def test_low_text_heading_propagates_once_to_next_substantive_page() -> None:
    pages = [
        _page(page_number=1, text="Qu'est-ce qu'un OPCVM ?", status="low_text"),
        _page(
            page_number=2, text="Une explication substantielle de l'OPCVM et de son fonctionnement."
        ),
        _page(page_number=3, text="Une autre page substantielle sans nouveau titre."),
    ]
    chunks, audit = chunk_pages(pages)
    assert chunks[0].section_heading == "Qu'est-ce qu'un OPCVM ?"
    assert chunks[0].section_heading_page == 1
    assert chunks[1].section_heading is None
    assert audit["pages_low_text_as_heading"] == 1
    assert audit["section_headings_propagated"] == 1


def test_repeated_edge_boilerplate_is_removed_but_content_is_kept() -> None:
    pages = [
        _page(
            page_number=index,
            text=f"GUIDE DE L'INVESTISSEUR\n\nContenu financier de la page {index}.",
        )
        for index in range(1, 4)
    ]
    chunks, audit = chunk_pages(pages)
    assert all("GUIDE DE L'INVESTISSEUR" not in chunk.text for chunk in chunks)
    assert all("Contenu financier" in chunk.text for chunk in chunks)
    assert audit["boilerplate_lines_detected"] >= 1
    assert audit["boilerplate_occurrences_removed"] == 3


def test_repeated_non_edge_financial_phrase_is_not_removed() -> None:
    phrase = "Risque et rendement doivent être analysés ensemble."
    pages = [
        _page(
            page_number=index,
            text=f"En-tête.\n\nSous-titre.\n\n{phrase}\n\nFin.\n\nPied.",
        )
        for index in range(1, 4)
    ]
    chunks, audit = chunk_pages(pages)
    assert all(phrase in chunk.text for chunk in chunks)
    assert audit["boilerplate_lines_detected"] == 4


def test_long_page_splits_without_exceeding_hard_limit_or_cutting_words() -> None:
    paragraphs = [
        "La diversification réduit le risque spécifique d'un portefeuille." * 12 for _ in range(4)
    ]
    chunks, _ = chunk_pages([_page(text="\n\n".join(paragraphs))])
    assert len(chunks) > 1
    assert all(chunk.char_count <= MAX_CHARS for chunk in chunks)
    assert all(not chunk.text.endswith("diversificatio") for chunk in chunks)


def test_chunk_ids_are_source_prefixed_unique_and_document_global() -> None:
    text = "Paragraphe financier suffisamment long pour être conservé. " * 80
    chunks, _ = chunk_pages([_page(text=text)])
    assert len({chunk.chunk_id for chunk in chunks}) == len(chunks)
    assert all(chunk.chunk_id.startswith("ammc-source-") for chunk in chunks)
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))


def test_duplicate_pages_are_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        chunk_pages([_page(page_number=1), _page(page_number=1)])


def test_chunks_strictly_reject_extra_fields_and_empty_text() -> None:
    chunks, _ = chunk_pages([_page()])
    payload = chunks[0].model_dump()
    with pytest.raises(ValidationError):
        ChunkRecord(**{**payload, "chunk_id": payload["chunk_id"], "extra": True})
    with pytest.raises(ValidationError):
        ChunkRecord(**{**payload, "text": "", "char_count": 0, "word_count": 0})


def test_output_shape_has_no_paths_or_chunk_cross_page_metadata() -> None:
    chunks, _ = chunk_pages([_page()])
    data = json.loads(chunks[0].model_dump_json())
    assert "file_path" not in data
    assert "chunk_id" in data
    assert data["page_start"] == data["page_end"] == 1


def test_source_module_has_no_embedding_retrieval_or_provider_imports() -> None:
    source = Path(__import__("app.rag.chunking", fromlist=["__file__"]).__file__)
    text = source.read_text(encoding="utf-8").lower()
    for forbidden in (
        "sentence_transformers",
        "chromadb",
        "faiss",
        "requests",
        "httpx",
        "gemini",
        "groq",
        "openai",
    ):
        assert forbidden not in text
