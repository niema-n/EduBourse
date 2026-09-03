import pytest

from app.multilingual.script_detector import detect_script


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("C'est quoi une action ?", "latin"),
        ("chno hiya lborsa?", "latin"),
        ("ما هو السهم؟", "arabic"),
        ("شنو هو MASI؟", "mixed"),
    ],
)
def test_detect_script(text: str, expected: str) -> None:
    assert detect_script(text) == expected


@pytest.mark.parametrize("text", ["\ufeff", "؟", "،", "ـ", "١٢٣"])
def test_detect_script_ignores_non_letter_arabic_codepoints(text: str) -> None:
    assert detect_script(text) == "latin"
