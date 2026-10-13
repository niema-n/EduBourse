import pytest

from app.graph.language_adapter import normalize_business_language
from app.graph.state import create_turn_input


@pytest.mark.parametrize(
    ("technical", "expected"),
    [
        ("fr", ("fr", "latin")),
        ("en", ("en", "latin")),
        ("ar", ("ar", "arabic")),
        ("ary-latin", ("ary", "latin")),
        ("ary-arabic", ("ary", "arabic")),
    ],
)
def test_normalize_business_language(technical, expected):
    assert normalize_business_language(technical) == expected


@pytest.mark.parametrize("script", ["latin", "arabic"])
def test_darija_script_persists_in_turn_state(script):
    state = create_turn_input("Demande", language="ary", script=script)
    assert state["language"] == "ary"
    assert state["script"] == script


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        ("ar", ("ar", "arabic")),
        ("fr", ("fr", "latin")),
        ("en", ("en", "latin")),
    ],
)
def test_mixed_j2_script_uses_canonical_non_darija_script(language, expected):
    assert normalize_business_language(language, "mixed") == expected


def test_invalid_business_language_is_rejected():
    with pytest.raises(ValueError):
        normalize_business_language("ary", "mixed")
