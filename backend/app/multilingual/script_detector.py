import unicodedata

from app.multilingual.models import ScriptCode

ARABIC_RANGES = (
    (0x0600, 0x06FF),
    (0x0750, 0x077F),
    (0x08A0, 0x08FF),
    (0xFB50, 0xFDFF),
    (0xFE70, 0xFEFF),
)


def _is_arabic_character(character: str) -> bool:
    codepoint = ord(character)
    return any(start <= codepoint <= end for start, end in ARABIC_RANGES)


def _is_latin_character(character: str) -> bool:
    if not character.isalpha():
        return False
    return "LATIN" in unicodedata.name(character, "")


def count_scripts(text: str) -> tuple[int, int]:
    latin_count = sum(1 for character in text if _is_latin_character(character))
    arabic_count = sum(1 for character in text if _is_arabic_character(character))
    return latin_count, arabic_count


def detect_script(text: str) -> ScriptCode:
    latin_count, arabic_count = count_scripts(text)
    if latin_count > 0 and arabic_count > 0:
        return "mixed"
    if arabic_count > 0:
        return "arabic"
    return "latin"
