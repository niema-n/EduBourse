"""J3 adapter from technical J2 language labels to business metadata."""

from typing import Literal

BusinessLanguage = Literal["fr", "en", "ar", "ary"]
BusinessScript = Literal["latin", "arabic"]


def normalize_business_language(
    language: str,
    script: str | None = None,
) -> tuple[BusinessLanguage, BusinessScript]:
    """Map J2 labels without performing language detection."""
    mapping = {
        "fr": ("fr", "latin"),
        "en": ("en", "latin"),
        "ar": ("ar", "arabic"),
        "ary-latin": ("ary", "latin"),
        "ary-arabic": ("ary", "arabic"),
    }
    if language == "ary" and script in {"latin", "arabic"}:
        return "ary", script
    result = mapping.get(language)
    if result is None:
        raise ValueError(f"Unsupported J2 language label: {language}")
    if script == "mixed":
        return result
    if script is not None and script != result[1]:
        raise ValueError(f"Invalid script {script!r} for language {language!r}")
    return result
