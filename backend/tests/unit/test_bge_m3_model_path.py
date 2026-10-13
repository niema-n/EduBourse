from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.rag import chroma_index


def test_configured_snapshot_path_is_used(monkeypatch, tmp_path: Path):
    configured = tmp_path / "configured-snapshot"
    seen: list[Path] = []
    monkeypatch.setattr(
        chroma_index,
        "get_settings",
        lambda: SimpleNamespace(bge_m3_model_path=str(configured)),
    )
    monkeypatch.setattr(
        chroma_index,
        "verify_sentence_transformer_snapshot",
        lambda path: seen.append(path),
    )

    resolved = chroma_index.resolve_bge_m3_snapshot_path()

    assert resolved == configured
    assert seen == [configured]


def test_empty_configuration_uses_historical_default(monkeypatch, tmp_path: Path):
    home = tmp_path / "home"
    monkeypatch.setattr(chroma_index.Path, "home", lambda: home)
    monkeypatch.setattr(
        chroma_index,
        "get_settings",
        lambda: SimpleNamespace(bge_m3_model_path=""),
    )
    seen: list[Path] = []
    monkeypatch.setattr(
        chroma_index,
        "verify_sentence_transformer_snapshot",
        lambda path: seen.append(path),
    )

    resolved = chroma_index.resolve_bge_m3_snapshot_path()

    expected = (
        home
        / ".cache/huggingface/hub/models--BAAI--bge-m3/snapshots"
        / chroma_index.MODEL_REVISION
    )
    assert resolved == expected
    assert seen == [expected]


def test_nonexistent_snapshot_fails_without_loading(tmp_path: Path):
    with pytest.raises(ValueError, match="snapshot is missing modules.json"):
        chroma_index.resolve_bge_m3_snapshot_path(tmp_path / "missing")


def test_snapshot_missing_modules_fails_explicitly(tmp_path: Path):
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()

    with pytest.raises(ValueError, match="snapshot is missing modules.json"):
        chroma_index.resolve_bge_m3_snapshot_path(snapshot)


def test_invalid_snapshot_does_not_instantiate_embedding_provider(monkeypatch, tmp_path: Path):
    called = False

    def fail_if_loaded(*args, **kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(chroma_index, "SentenceTransformerEmbeddingProvider", fail_if_loaded)

    with pytest.raises(ValueError, match="snapshot is missing modules.json"):
        chroma_index.resolve_bge_m3_snapshot_path(tmp_path / "invalid")

    assert called is False
