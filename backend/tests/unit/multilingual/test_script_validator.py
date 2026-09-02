from app.multilingual.script_validator import validate_script


def test_validates_expected_latin_script() -> None:
    assert validate_script("chno hiya lborsa?", "ary-latin").valid is True


def test_rejects_arabic_when_darija_latin_expected() -> None:
    result = validate_script("شنو هي البورصة؟", "ary-latin")

    assert result.valid is False


def test_rejects_latin_when_darija_arabic_expected() -> None:
    result = validate_script("chno hiya lborsa?", "ary-arabic")

    assert result.valid is False


def test_accepts_mixed_when_expected_script_is_dominant() -> None:
    result = validate_script("شنو هو MASI؟", "ary-arabic")

    assert result.valid is True
