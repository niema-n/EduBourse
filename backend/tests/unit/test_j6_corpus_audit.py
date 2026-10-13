import ast
import hashlib
import unicodedata
from pathlib import Path

import pytest
from pypdf import PdfWriter

from app.rag import corpus_audit
from app.rag.corpus_audit import audit_corpus
from app.rag.domain_policy import CorpusDocumentManifest


def _pdf(path: Path, pages: int = 1, title: str | None = None, password: str | None = None) -> None:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=72, height=72)
    if title is not None:
        writer.add_metadata({"/Title": title})
    if password is not None:
        writer.encrypt(password)
    with path.open("wb") as stream:
        writer.write(stream)


def _audit_root(tmp_path: Path, authority: str = "ammc") -> Path:
    root = tmp_path / "backend/data/rag/raw" / authority
    root.mkdir(parents=True)
    return root


def _one_record(tmp_path: Path, filename: str, **kwargs: object) -> dict:
    root = _audit_root(tmp_path)
    _pdf(root / filename, **kwargs)
    return audit_corpus(tmp_path)[0]["documents"][0]


def test_sha256_is_exactly_the_file_bytes_and_deterministic(tmp_path: Path) -> None:
    root = _audit_root(tmp_path)
    path = root / "Guide-PEA.pdf"
    _pdf(path, pages=2)
    expected = hashlib.sha256(path.read_bytes()).hexdigest()

    _, first = audit_corpus(tmp_path)
    _, second = audit_corpus(tmp_path)

    assert first["files"][0]["sha256"] == expected
    assert first["files"][0]["sha256"] == second["files"][0]["sha256"]
    assert first["files"][0]["page_count"] == 2


def test_only_approved_pdf_directories_are_discovered(tmp_path: Path) -> None:
    root = _audit_root(tmp_path)
    _pdf(root / "inside.pdf")
    outside = tmp_path / "backend/data/rag/raw/not_approved"
    outside.mkdir(parents=True)
    _pdf(outside / "ignored.pdf")
    (root / "notes.txt").write_text("not a PDF", encoding="utf-8")

    _, report = audit_corpus(tmp_path)

    assert report["total_files"] == 1


def test_duplicate_is_hash_based_and_excluded_from_canonical_manifest(tmp_path: Path) -> None:
    first = _audit_root(tmp_path, "ammc")
    second = _audit_root(tmp_path, "ecole_bourse")
    _pdf(first / "Guide-PEA.pdf")
    (second / "same-bytes.pdf").write_bytes((first / "Guide-PEA.pdf").read_bytes())

    manifest, report = audit_corpus(tmp_path)

    assert report["unique_documents"] == 1
    assert report["duplicate_files"] == 1
    assert len(manifest["documents"]) == 1
    assert report["files"][1]["duplicate_of"] == manifest["documents"][0]["source_id"]
    assert report["files"][1]["source_id"] != report["files"][0]["source_id"]


def test_source_ids_are_ascii_authority_prefixed_and_stable(tmp_path: Path) -> None:
    record_a = _one_record(tmp_path, "Guide-de-linvestisseur-Comprendre-les-IPO.pdf")
    record_b = _one_record(tmp_path / "other", "Guide-de-linvestisseur-Comprendre-les-IPO.pdf")

    assert record_a["source_id"] == "ammc-comprendre-les-ipo"
    assert record_a["source_id"] == record_b["source_id"]
    assert record_a["source_id"].isascii()
    assert record_a["source_id"].islower()


def test_same_title_different_bytes_get_collision_safe_ids(tmp_path: Path) -> None:
    root = _audit_root(tmp_path)
    _pdf(root / "a.pdf", pages=1, title="Same title")
    _pdf(root / "b.pdf", pages=2, title="Same title")
    manifest, report = audit_corpus(tmp_path)

    ids = [item["source_id"] for item in manifest["documents"]]
    assert len(ids) == len(set(ids)) == 2
    assert all(item["source_id"].startswith("ammc-same-title-") for item in report["files"])


def test_authority_is_derived_from_approved_directory(tmp_path: Path) -> None:
    record = _one_record(tmp_path, "pea.pdf")
    assert record["authority"] == "ammc"


def test_good_metadata_title_is_accepted(tmp_path: Path) -> None:
    record = _one_record(tmp_path, "fallback-name.pdf", title="Plan d'épargne en actions")
    assert record["title"] == "Plan d'épargne en actions"


@pytest.mark.parametrize(
    "metadata",
    ["guide des instruments 2.indd", "Guide IPO V 16 juillet 2021.indd", "Microsoft Word"],
)
def test_production_or_generic_metadata_title_is_rejected(tmp_path: Path, metadata: str) -> None:
    record = _one_record(
        tmp_path, "Guide-de-linvestisseur-Comprendre-les-IPO.pdf", title=metadata
    )
    assert record["title"] == "Comprendre les IPO"
    assert ".indd" not in record["title"].casefold()


def test_filename_fallback_is_clean_and_nfc_normalized(tmp_path: Path) -> None:
    record = _one_record(
        tmp_path,
        "Guide-de-linvestisseur-les-assemble" + "\u0301" + "es-generales-FR-web.pdf",
    )
    assert "assembl" in record["title"].casefold()
    assert unicodedata.is_normalized("NFC", record["title"])


def test_french_contractions_are_restored_without_malformed_accents(tmp_path: Path) -> None:
    record = _one_record(
        tmp_path,
        "Brochure-sur-le-budget-lepargne-et-linvestissement.pdf",
    )
    assert record["title"] == "Sur le budget l'épargne et l'investissement"
    assert "lépargne" not in record["title"]


def test_financing_edition_suffix_is_removed_only_in_its_known_pattern(tmp_path: Path) -> None:
    record = _one_record(
        tmp_path,
        "Guide-de-linvestisseur-Comprendre-le-financement-collaboratif-24-FR-web.pdf",
    )
    assert record["title"] == "Comprendre le financement collaboratif"
    assert record["source_id"] == "ammc-comprendre-le-financement-collaboratif"


def test_meaningful_numbers_are_preserved_elsewhere(tmp_path: Path) -> None:
    record = _one_record(tmp_path, "Guide-de-linvestisseur-Comprendre-les-IPO-2024.pdf")
    assert record["title"] == "Comprendre les IPO 2024"


def test_source_ids_for_the_two_normalized_titles_are_stable(tmp_path: Path) -> None:
    budget = _one_record(
        tmp_path / "budget",
        "Brochure-sur-le-budget-lepargne-et-linvestissement.pdf",
    )
    financing = _one_record(
        tmp_path / "financing",
        "Guide-de-linvestisseur-Comprendre-le-financement-collaboratif-24-FR-web.pdf",
    )
    assert budget["source_id"] == "ammc-sur-le-budget-l-epargne-et-l-investissement"
    assert financing["source_id"] == "ammc-comprendre-le-financement-collaboratif"


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        (
            "Guide-de-linvestisseur-Comprendre-les-instruments-financiers-et-leurs-mecanismes-FR-web.pdf",
            "financial_instruments",
        ),
        ("Guide-de-linvestisseur-Comprendre-les-IPO.pdf", "ipo"),
        ("Guide-de-linvestisseur-les-OPCVM-FR-web.pdf", "opcvm"),
        (
            "Guide-de-linvestisseur-renforcer-la-protection-de-vos-placements.pdf",
            "investor_protection",
        ),
        (
            "Guide-de-linvestisseur-Comprendre-les-circuits-et-adopter-les-bonnes-pratiques-FR-web.pdf",
            "investor_protection",
        ),
    ],
)
def test_categories_use_subject_evidence_not_series_brand(
    tmp_path: Path, filename: str, expected: str
) -> None:
    record = _one_record(tmp_path, filename)
    assert expected in record["category"]


@pytest.mark.parametrize(
    "filename",
    [
        "Guide-de-linvestisseur-Comprendre-les-IPO.pdf",
        "Guide-de-linvestisseur-les-OPCVM-FR-web.pdf",
    ],
)
def test_series_brand_does_not_add_investor_protection(tmp_path: Path, filename: str) -> None:
    assert "investor_protection" not in _one_record(tmp_path, filename)["category"]


def test_generic_placements_does_not_add_two_unrelated_categories(tmp_path: Path) -> None:
    record = _one_record(tmp_path, "Guide-de-linvestisseur-placements.pdf")
    assert record["category"] == ["market_basics"]


def test_category_counts_come_from_unique_records(tmp_path: Path) -> None:
    root = _audit_root(tmp_path)
    _pdf(root / "Guide-de-linvestisseur-Comprendre-les-IPO.pdf")
    _pdf(root / "Guide-de-linvestisseur-les-OPCVM-FR-web.pdf", pages=2)
    _, report = audit_corpus(tmp_path)
    assert report["category_counts"] == {"ipo": 1, "opcvm": 1}


def test_corrupt_and_zero_byte_files_are_safe(tmp_path: Path) -> None:
    root = _audit_root(tmp_path)
    (root / "empty.pdf").touch()
    (root / "broken.pdf").write_bytes(b"%PDF-not-valid")
    manifest, report = audit_corpus(tmp_path)
    assert manifest["documents"] == []
    assert report["review_required"] == 2
    assert report["invalid_pdfs"] == 1


def test_encrypted_pdf_is_review_required_without_credentials(tmp_path: Path) -> None:
    root = _audit_root(tmp_path)
    _pdf(root / "locked.pdf", password="secret")
    _, report = audit_corpus(tmp_path)
    assert report["review_required"] == 1
    assert report["files"][0]["error"] == "encrypted_pdf"


def test_manifest_entries_validate_through_source_manifest(tmp_path: Path) -> None:
    record = _one_record(tmp_path, "Guide-de-linvestisseur-Comprendre-les-IPO.pdf")
    CorpusDocumentManifest(**record)


def test_paths_are_repository_relative_and_never_absolute(tmp_path: Path) -> None:
    record = _one_record(tmp_path, "pea.pdf")
    assert not Path(record["file_path"]).is_absolute()
    assert "backend" not in Path(record["file_path"]).parts
    assert ".." not in Path(record["file_path"]).parts


def test_manifest_and_report_ordering_and_bytes_are_idempotent(tmp_path: Path) -> None:
    root = _audit_root(tmp_path)
    _pdf(root / "z.pdf")
    _pdf(root / "a.pdf")
    first, first_report = audit_corpus(tmp_path)
    second, second_report = audit_corpus(tmp_path)
    assert first == second
    assert first_report == second_report
    assert first["documents"] == sorted(first["documents"], key=lambda item: item["source_id"])


def test_audit_never_calls_full_text_extraction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _audit_root(tmp_path)
    _pdf(root / "metadata-only.pdf", title="A valid title")

    def fail_if_called(*args: object, **kwargs: object) -> str:
        raise AssertionError("full text extraction was called")

    monkeypatch.setattr("pypdf._page.PageObject.extract_text", fail_if_called)
    manifest, report = audit_corpus(tmp_path)
    assert len(manifest["documents"]) == 1
    assert report["total_pages_unique"] == 1


def test_audit_source_has_no_network_or_external_provider_imports() -> None:
    tree = ast.parse(Path(corpus_audit.__file__).read_text(encoding="utf-8"))
    forbidden = {"requests", "httpx", "urllib", "google", "groq", "openai"}
    imports = {
        node.names[0].name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
    }
    imports.update(
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    assert imports.isdisjoint(forbidden)
