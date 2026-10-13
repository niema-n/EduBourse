import ast
import hashlib
import json
from pathlib import Path

import pytest
from pypdf import PdfWriter

from app.rag.text_extraction import (
    ExtractedPageRecord,
    clean_text,
    extract_corpus,
)


def _pdf(path: Path, pages: int = 1) -> None:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=72, height=72)
    with path.open("wb") as stream:
        writer.write(stream)


def _fixture(tmp_path: Path, entries: list[dict], pages: int = 1) -> tuple[Path, Path]:
    root = tmp_path / "backend"
    source = root / "data/rag/raw/ammc/source.pdf"
    source.parent.mkdir(parents=True)
    _pdf(source, pages=pages)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    for entry in entries:
        entry.update(
            {
                "source_id": entry.get("source_id", "ammc-source"),
                "title": entry.get("title", "Source"),
                "authority": "ammc",
                "source_type": "pdf",
                "language": "fr",
                "category": entry.get("category", ["market_basics"]),
                "file_path": "data/rag/raw/ammc/source.pdf",
                "document_hash": entry.get("document_hash", digest),
                "agents_or_capabilities": [],
                "status": "active",
            }
        )
    manifest = root / "data/rag/manifests/corpus_v1.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps({"schema_version": "j6-corpus-v1", "documents": entries}),
        encoding="utf-8",
    )
    return tmp_path, source


class _Page:
    def __init__(self, text: str = "", error: Exception | None = None) -> None:
        self.text = text
        self.error = error

    def extract_text(self) -> str:
        if self.error:
            raise self.error
        return self.text


class _Reader:
    def __init__(self, pages: list[_Page]) -> None:
        self.pages = pages

    @property
    def is_encrypted(self) -> bool:
        return False


def test_cleaning_is_conservative_and_deterministic() -> None:
    cleaned, warnings = clean_text("Épargne\r\n\r\n  action\u00a0  -\t  marché\r")
    assert cleaned == "Épargne\n\naction - marché"
    assert warnings == []
    assert clean_text("Épargne\r\n\r\n  action\u00a0  -\t  marché\r") == (cleaned, warnings)


def test_cleaning_removes_controls_but_preserves_accents_punctuation_and_hyphens() -> None:
    cleaned, warnings = clean_text("Obligation\x00 à taux fixe\n\n\n- risque maîtrisé !")
    assert cleaned == "Obligation à taux fixe\n\n- risque maîtrisé !"
    assert "control_characters_removed" in warnings


def test_empty_and_low_text_statuses_are_controlled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _ = _fixture(tmp_path, [{}], pages=2)
    monkeypatch.setattr(
        "app.rag.text_extraction.PdfReader",
        lambda *args, **kwargs: _Reader([_Page(""), _Page("court")]),
    )
    records, audit = extract_corpus(root)
    assert [record.extraction_status for record in records] == ["empty", "low_text"]
    assert audit["pages_empty"] == 1
    assert audit["pages_low_text"] == 1


def test_valid_page_record_copies_frozen_manifest_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, source = _fixture(
        tmp_path,
        [{"source_id": "frozen-id", "title": "Frozen title", "category": ["pea"]}],
    )
    monkeypatch.setattr(
        "app.rag.text_extraction.PdfReader",
        lambda *args, **kwargs: _Reader([_Page("Une action est un titre financier.")]),
    )
    records, audit = extract_corpus(root)
    record = records[0]
    assert record.source_id == "frozen-id"
    assert record.title == "Frozen title"
    assert record.categories == ["pea"]
    assert record.authority == "ammc"
    assert record.page_number == 1
    assert record.page_count == 1
    assert record.document_hash == hashlib.sha256(source.read_bytes()).hexdigest()
    assert record.raw_char_count == len("Une action est un titre financier.")
    assert record.clean_char_count == len(record.text)
    assert record.word_count == 6
    assert record.text_sha256 == hashlib.sha256(record.text.encode("utf-8")).hexdigest()
    assert audit["documents_processed"] == 1


def test_source_hash_mismatch_prevents_extraction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _ = _fixture(tmp_path, [{"document_hash": "0" * 64}])
    called = False

    def fail_reader(*args: object, **kwargs: object) -> _Reader:
        nonlocal called
        called = True
        raise AssertionError("PDF must not be opened after hash mismatch")

    monkeypatch.setattr("app.rag.text_extraction.PdfReader", fail_reader)
    records, audit = extract_corpus(root)
    assert records == []
    assert called is False
    assert audit["document_results"][0]["error"] == "SOURCE_HASH_MISMATCH"


def test_one_bad_page_does_not_abort_other_pages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _ = _fixture(tmp_path, [{}], pages=3)
    monkeypatch.setattr(
        "app.rag.text_extraction.PdfReader",
        lambda *args, **kwargs: _Reader(
            [_Page("Une phrase suffisamment longue pour être conservée."),
             _Page(error=RuntimeError("broken")),
             _Page("Une autre phrase suffisamment longue pour être conservée.")]
        ),
    )
    records, audit = extract_corpus(root)
    assert [record.page_number for record in records] == [1, 2, 3]
    assert records[1].extraction_status == "extraction_error"
    assert audit["pages_error"] == 1
    assert audit["pages_ok"] == 2


def test_two_documents_are_sorted_by_source_id_then_page_number(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, source = _fixture(tmp_path, [{"source_id": "z-id"}], pages=2)
    payload = json.loads((root / "backend/data/rag/manifests/corpus_v1.json").read_text())
    second = dict(payload["documents"][0], source_id="a-id", title="Other")
    payload["documents"].append(second)
    (root / "backend/data/rag/manifests/corpus_v1.json").write_text(json.dumps(payload))
    monkeypatch.setattr(
        "app.rag.text_extraction.PdfReader",
        lambda *args, **kwargs: _Reader([_Page("Une phrase de contenu suffisamment longue.")]),
    )
    records, _ = extract_corpus(root)
    assert [(record.source_id, record.page_number) for record in records] == [
        ("a-id", 1),
        ("z-id", 1),
    ]
    assert source.exists()


def test_strict_page_contract_rejects_chunk_id_and_bad_page_number() -> None:
    base = {
        "source_id": "id", "title": "title", "authority": "ammc", "language": "fr",
        "categories": ["pea"], "page_number": 1, "page_count": 1, "document_hash": "a" * 64,
        "text": "text", "text_sha256": hashlib.sha256(b"text").hexdigest(),
        "raw_char_count": 4, "clean_char_count": 4, "word_count": 1,
        "extraction_status": "low_text", "warnings": ["low_text"],
    }
    ExtractedPageRecord(**base)
    with pytest.raises(ValueError):
        ExtractedPageRecord(**{**base, "chunk_id": "forbidden"})
    with pytest.raises(ValueError):
        ExtractedPageRecord(**{**base, "page_number": 2})


def test_extraction_source_has_no_external_or_forbidden_rag_imports() -> None:
    source = Path(__import__("app.rag.text_extraction", fromlist=["__file__"]).__file__)
    tree = ast.parse(source.read_text(encoding="utf-8"))
    forbidden = {
        "requests", "httpx", "urllib", "google", "groq", "openai", "chromadb", "faiss", "ocr"
    }
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    assert imports.isdisjoint(forbidden)
