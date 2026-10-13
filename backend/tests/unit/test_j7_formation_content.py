# ruff: noqa: E501
import ast
import re
from collections import Counter
from pathlib import Path

import pytest

from app.formation.content import LOCALES, modules_for, validate_formation_content
from app.formation.localized_content import FORMATION_LOCALIZED_CONTENT


def _all_content():
    return [content for modules in FORMATION_LOCALIZED_CONTENT.values() for module in modules for content in module["locales"].values()]


def _text(content):
    return " ".join([content["title"], content["objective"], content["lesson"], *content["key_points"], content["checkpoint"]])


def test_all_120_representations_are_explicit_and_complete():
    validate_formation_content()
    assert len(FORMATION_LOCALIZED_CONTENT) == 3
    assert sum(len(modules) for modules in FORMATION_LOCALIZED_CONTENT.values()) == 24
    assert sum(len(module["locales"]) for modules in FORMATION_LOCALIZED_CONTENT.values() for module in modules) == 120
    assert all(set(content) == {"title", "objective", "lesson", "key_points", "checkpoint"} for content in _all_content())


@pytest.mark.parametrize("level", ("beginner", "intermediate", "advanced"))
@pytest.mark.parametrize("locale", LOCALES)
def test_each_level_locale_has_distinct_authored_content(level, locale):
    contents = [module["locales"][locale] for module in FORMATION_LOCALIZED_CONTENT[level]]
    for field in ("title", "objective", "lesson", "checkpoint"):
        assert len({content[field] for content in contents}) == 8
    assert len({tuple(content["key_points"]) for content in contents}) == 8


def test_all_locales_have_distinct_level_paths_and_no_aliasing():
    for locale in LOCALES:
        lessons = [FORMATION_LOCALIZED_CONTENT[level][index]["locales"][locale]["lesson"] for level in ("beginner", "intermediate", "advanced") for index in range(8)]
        assert len(set(lessons)) == 24
    assert FORMATION_LOCALIZED_CONTENT["beginner"][0] is not FORMATION_LOCALIZED_CONTENT["intermediate"][0]
    returned = modules_for("beginner")
    returned[0]["locales"]["en/latin"]["title"] = "changed"
    assert FORMATION_LOCALIZED_CONTENT["beginner"][0]["locales"]["en/latin"]["title"] != "changed"


def test_source_and_visible_content_have_no_forbidden_generation_or_artifacts():
    static_source = Path(__file__).parents[2] / "app" / "formation" / "localized_content.py"
    tree = ast.parse(static_source.read_text(encoding="utf-8"))
    assert not any(isinstance(node, ast.JoinedStr) for node in ast.walk(tree))
    assert sum(0x600 <= ord(char) <= 0x6FF for char in str(FORMATION_LOCALIZED_CONTENT)) > 0
    visible = " ".join(_text(content) for content in _all_content())
    assert not any(token in visible for token in ("market_basics", "stocks_bonds", "primary_secondary", "risk_return", "moroccan_market"))
    assert not any(ord(char) in (0xFFFD, 0x00C3, 0x00C2, 0x00D8, 0x00D9) for char in visible)


def test_arabic_registers_are_distinct_and_safe():
    msa = " ".join(_text(module["locales"]["ar/arabic"]) for level in FORMATION_LOCALIZED_CONTENT for module in FORMATION_LOCALIZED_CONTENT[level])
    darija = " ".join(_text(module["locales"]["ary/arabic"]) for level in FORMATION_LOCALIZED_CONTENT for module in FORMATION_LOCALIZED_CONTENT[level])
    assert msa != darija
    assert any(0x600 <= ord(char) <= 0x6FF for char in msa)
    assert any(marker in darija for marker in ("\u0634\u0646\u0648", "\u0643\u064a\u0641\u0627\u0634", "\u062f\u064a\u0627\u0644"))
    assert not any(ord(char) in (0xFFFD, 0x00D8, 0x00D9) for char in msa + darija)


@pytest.mark.parametrize("locale", ("ar/arabic", "ary/arabic"))
def test_intermediate_and_advanced_arabic_have_specific_keypoints(locale):
    for level in ("intermediate", "advanced"):
        for module in FORMATION_LOCALIZED_CONTENT[level]:
            content = module["locales"][locale]
            assert len(content["key_points"]) >= 2
            assert content["lesson"] not in content["key_points"]
            assert content["objective"] != content["lesson"]



def test_target_arabic_has_no_mixed_hex_tokens_or_historical_artifacts():
    for level in ("intermediate", "advanced"):
        for index in range(8):
            for locale in ("ar/arabic", "ary/arabic"):
                visible = _text(FORMATION_LOCALIZED_CONTENT[level][index]["locales"][locale])
                assert "2a46484a39" not in visible
                assert "46384a45" not in visible
                assert "4a2744" not in visible
                for token in re.findall(r"\S+", visible):
                    has_arabic = any("\u0600" <= char <= "\u06ff" for char in token)
                    has_hex_run = re.search(r"[0-9a-fA-F]{2,}", token)
                    assert not (has_arabic and has_hex_run), token


def test_cross_level_arabic_checkpoints_and_keypoints_are_distinct():
    for locale in ("ar/arabic", "ary/arabic"):
        checkpoints = [FORMATION_LOCALIZED_CONTENT[level][index]["locales"][locale]["checkpoint"] for level in ("beginner", "intermediate", "advanced") for index in range(8)]
        keypoint_sets = [tuple(FORMATION_LOCALIZED_CONTENT[level][index]["locales"][locale]["key_points"]) for level in ("beginner", "intermediate", "advanced") for index in range(8)]
        assert len(set(checkpoints)) == 24
        assert len(set(keypoint_sets)) == 24


def test_arabic_objectives_do_not_collapse_to_level_suffixes():
    for locale in ("ar/arabic", "ary/arabic"):
        objectives = [FORMATION_LOCALIZED_CONTENT[level][index]["locales"][locale]["objective"] for level in ("intermediate", "advanced") for index in range(8)]
        assert len(set(objectives)) == 16



def _arabic_words(value):
    return re.findall(r"[\u0600-\u06ff]+", value)


def test_repaired_lessons_have_minimum_substance():
    for level in ("intermediate", "advanced"):
        minimum = 12 if level == "intermediate" else 16
        for index in range(8):
            for locale in ("ar/arabic", "ary/arabic"):
                lesson = FORMATION_LOCALIZED_CONTENT[level][index]["locales"][locale]["lesson"]
                assert len(_arabic_words(lesson)) >= minimum


def test_repaired_lessons_are_not_generic_market_templates():
    lessons = []
    for level in ("intermediate", "advanced"):
        for index in range(8):
            for locale in ("ar/arabic", "ary/arabic"):
                content = FORMATION_LOCALIZED_CONTENT[level][index]["locales"][locale]
                lesson = content["lesson"]
                assert lesson not in ("\u062f\u0641\u062a\u0631 \u0641\u064a \u0627\u0644\u0633\u0648\u0642 \u0627\u0644\u0645\u0627\u0644\u064a.", "\u062f\u0641\u062a\u0631 \u0641\u0627\u0644\u0633\u0648\u0642 \u0627\u0644\u0645\u0627\u0644\u064a.")
                lessons.append(lesson)
    assert len(set(lessons)) == 32


def test_repaired_keypoints_are_module_specific():
    points = []
    for level in ("intermediate", "advanced"):
        for index in range(8):
            for locale in ("ar/arabic", "ary/arabic"):
                content = FORMATION_LOCALIZED_CONTENT[level][index]["locales"][locale]
                assert not content["key_points"][0].endswith("\u0645\u0648\u0636\u0648\u0639 \u0645\u0647\u0645.")
                points.extend(content["key_points"])
    counts = Counter(points)
    assert not any(count >= 12 for count in counts.values())
    assert "التنويع ماكيلغيش الخطر." not in points


def test_msa_register_and_arabic_typo_regressions():
    visible = " ".join(_text(FORMATION_LOCALIZED_CONTENT[level][index]["locales"]["ar/arabic"]) for level in FORMATION_LOCALIZED_CONTENT for index in range(8))
    assert not any(marker in visible for marker in ("\u0645\u0627\u06a9\u064a", "\u0634\u0646\u0648", "\u0643\u064a\u0641\u0627\u0634", "\u062f\u064a\u0627\u0644", "\u0628\u0627\u0634", "\u0643\u0627\u064a\u0646", "\u0643\u064a\u062e\u062f\u0645"))
    assert "الإصباح" not in visible
    assert "الارتبباط" not in visible


def test_every_darija_representation_has_a_darija_construction():
    markers = ("شنو", "كيفاش", "ديال", "باش", "كاين", "كي", "كيت", "كت")
    for level in ("intermediate", "advanced"):
        for index in range(8):
            content = FORMATION_LOCALIZED_CONTENT[level][index]["locales"]["ary/arabic"]
            visible = " ".join([content["objective"], content["lesson"], *content["key_points"], content["checkpoint"]])
            assert any(marker in visible for marker in markers)
