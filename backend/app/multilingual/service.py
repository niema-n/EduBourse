from app.multilingual.detector import detect_language
from app.multilingual.models import (
    LanguageAnalysis,
    LanguageCode,
    ScriptCode,
    ScriptValidationResult,
)
from app.multilingual.normalizer import normalize_text
from app.multilingual.script_detector import detect_script
from app.multilingual.script_validator import validate_script


class MultilingualService:
    def analyze(self, text: str) -> LanguageAnalysis:
        return detect_language(text)

    def normalize(self, text: str) -> str:
        return normalize_text(text)

    def detect_script(self, text: str) -> ScriptCode:
        return detect_script(text)

    def validate_response_script(
        self,
        text: str,
        expected_language: LanguageCode,
    ) -> ScriptValidationResult:
        return validate_script(text, expected_language)
