import unicodedata

from app.multilingual.models import ScriptCode


def _is_linguistic_letter(character: str) -> bool:
    return unicodedata.category(character).startswith("L")


def _is_arabic_letter(character: str) -> bool:
    if character == "ـ":
        return False
    if not _is_linguistic_letter(character):
        return False
    return "ARABIC" in unicodedata.name(character, "")


def _is_latin_letter(character: str) -> bool:
    if not _is_linguistic_letter(character):
        return False
    return "LATIN" in unicodedata.name(character, "")


def count_scripts(text: str) -> tuple[int, int]:
    latin_count = sum(1 for character in text if _is_latin_letter(character))
    arabic_count = sum(1 for character in text if _is_arabic_letter(character))
    return latin_count, arabic_count


def detect_script(text: str) -> ScriptCode:
    latin_count, arabic_count = count_scripts(text)
    if latin_count > 0 and arabic_count > 0:
        return "mixed"
    if arabic_count > 0:
        return "arabic"
    return "latin"
