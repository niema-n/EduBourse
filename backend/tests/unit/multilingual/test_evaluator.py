from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_evaluator_module():
    script_path = Path(__file__).resolve().parents[4] / "scripts" / "evaluate_multilingual.py"
    spec = importlib.util.spec_from_file_location("evaluate_multilingual", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_evaluator_displays_external_dataset_path_without_crashing(tmp_path: Path) -> None:
    evaluator = _load_evaluator_module()
    external_dataset = tmp_path / "external_dataset.jsonl"

    assert evaluator.display_path(external_dataset) == str(external_dataset)


def test_evaluator_loads_external_utf8_sig_dataset(tmp_path: Path) -> None:
    evaluator = _load_evaluator_module()
    external_dataset = tmp_path / "external_dataset.jsonl"
    external_dataset.write_text(
        '{"text":"Thanks, that was clear.","expected_language":"en"}\n',
        encoding="utf-8-sig",
    )

    assert evaluator.load_dataset(external_dataset) == [
        {"text": "Thanks, that was clear.", "expected_language": "en"}
    ]


def test_evaluator_thresholds_are_selected_by_explicit_profile() -> None:
    evaluator = _load_evaluator_module()

    assert evaluator.minimums_for("none") == {}
    assert evaluator.minimums_for("golden") == {"overall": 0.95}
    assert evaluator.minimums_for("challenge")["ary-arabic"] == 0.90
