from app.multilingual.models import LanguageCode, ScriptCode, ScriptValidationResult
from app.multilingual.script_detector import count_scripts, detect_script

EXPECTED_SCRIPT_BY_LANGUAGE: dict[LanguageCode, ScriptCode] = {
    "fr": "latin",
    "en": "latin",
    "ar": "arabic",
    "ary-latin": "latin",
    "ary-arabic": "arabic",
}


def validate_script(text: str, expected_language: LanguageCode) -> ScriptValidationResult:
    expected_script = EXPECTED_SCRIPT_BY_LANGUAGE[expected_language]
    detected_script = detect_script(text)
    latin_count, arabic_count = count_scripts(text)

    if detected_script == expected_script:
        return ScriptValidationResult(
            valid=True,
            expected_script=expected_script,
            detected_script=detected_script,
            reason="script matches expected language",
        )

    if detected_script == "mixed":
        if expected_script == "latin" and latin_count >= arabic_count:
            valid = True
        elif expected_script == "arabic" and arabic_count >= latin_count:
            valid = True
        else:
            valid = False
        return ScriptValidationResult(
            valid=valid,
            expected_script=expected_script,
            detected_script=detected_script,
            reason="mixed script is acceptable only when expected script is dominant",
        )

    return ScriptValidationResult(
        valid=False,
        expected_script=expected_script,
        detected_script=detected_script,
        reason="detected script conflicts with expected language",
    )
