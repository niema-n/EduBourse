import pytest

from app.multilingual.detector import detect_language


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("C'est quoi une action ?", "fr"),
        ("Comment fonctionne une obligation ?", "fr"),
        ("C'est quoi une société cotée ?", "fr"),
        ("Quelle est la différence entre une obligation et une action ?", "fr"),
    ],
)
def test_detects_french(text: str, expected: str) -> None:
    assert detect_language(text).language == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("What is a stock?", "en"),
        ("How does a bond work?", "en"),
        ("What are the risks of investing in stocks?", "en"),
        ("I want to learn about the stock market.", "en"),
    ],
)
def test_detects_english(text: str, expected: str) -> None:
    assert detect_language(text).language == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("ما هو السهم؟", "ar"),
        ("ما هي البورصة؟", "ar"),
        ("ما هي مخاطر الاستثمار؟", "ar"),
        ("كيف يعمل سوق رأس المال؟", "ar"),
    ],
)
def test_detects_standard_arabic(text: str, expected: str) -> None:
    assert detect_language(text).language == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("chno hiya lborsa?", "ary-latin"),
        ("achno howa sou9 lborsa?", "ary-latin"),
        ("bghit nt3ellem lborsa", "ary-latin"),
        ("wach OPCVM fih risk?", "ary-latin"),
        ("kifach n9der nt3ellem lborsa?", "ary-latin"),
        ("fin n9der nla9a formation?", "ary-latin"),
        ("ch7al kayn mn naw3 dyal actions?", "ary-latin"),
        ("3lach taman dyal action kaytbedel?", "ary-latin"),
    ],
)
def test_detects_darija_latin(text: str, expected: str) -> None:
    assert detect_language(text).language == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("شنو هي البورصة؟", "ary-arabic"),
        ("بغيت نتعلم البورصة", "ary-arabic"),
        ("واش الاستثمار فيه المخاطر؟", "ary-arabic"),
        ("كيفاش نقدر نتعلم البورصة؟", "ary-arabic"),
        ("فين نقدر نلقى تكوين؟", "ary-arabic"),
        ("علاش ثمن السهم كيتبدل؟", "ary-arabic"),
    ],
)
def test_detects_darija_arabic(text: str, expected: str) -> None:
    assert detect_language(text).language == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("wach OPCVM fih risk?", "ary-latin"),
        ("شنو هو MASI؟", "ary-arabic"),
        ("C'est quoi le MASI ?", "fr"),
        ("What is the MASI?", "en"),
    ],
)
def test_financial_terms_do_not_override_surrounding_language(text: str, expected: str) -> None:
    assert detect_language(text).language == expected


def test_ambiguous_short_phrase_has_low_confidence() -> None:
    result = detect_language("MASI")

    assert result.language in {"fr", "en"}
    assert result.confidence is not None
    assert result.confidence <= 0.40
