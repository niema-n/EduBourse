import re
import unicodedata

SPACE_RE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    return SPACE_RE.sub(" ", normalized.strip())
