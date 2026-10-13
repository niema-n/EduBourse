from types import SimpleNamespace

import pytest

from app.voice.providers.gemini import GeminiVoiceProvider, _get_tts_profile


class RecordingInteractions:
    def __init__(self) -> None:
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            output_audio=SimpleNamespace(
                type="audio",
                data=b"pcm",
                mime_type="audio/pcm",
                sample_rate=24000,
                channels=1,
            )
        )


@pytest.mark.parametrize(
    ("language", "script", "speech_language"),
    [
        ("fr", "latin", "French"),
        ("en", "latin", "English"),
        ("ar", "arabic", "Arabic"),
        ("ary", "arabic", "Arabic"),
        ("ary", "latin", "Arabic"),
    ],
)
def test_tts_profile_is_explicit_for_each_supported_variant(
    language: str, script: str, speech_language: str
) -> None:
    profile = _get_tts_profile(language, script)

    assert profile.speech_language == speech_language
    assert profile.instruction


def test_tts_profiles_separate_french_english_msa_and_darija() -> None:
    fr = _get_tts_profile("fr", "latin").instruction
    en = _get_tts_profile("en", "latin").instruction
    ar = _get_tts_profile("ar", "arabic").instruction
    ary_arabic = _get_tts_profile("ary", "arabic").instruction
    ary_latin = _get_tts_profile("ary", "latin").instruction

    assert "French" in fr and "Moroccan" not in fr
    assert "English" in en and "Arabic" not in en and "Moroccan" not in en
    assert "Modern Standard Arabic" in ar and "Moroccan Darija" in ar
    assert "Moroccan Darija" in ary_arabic
    assert "Do not pronounce it as Modern Standard Arabic" in ary_arabic
    assert "Latin/Arabizi" in ary_latin
    assert "Do not read them as literal numbers" in ary_latin


@pytest.mark.parametrize(
    ("language", "script"),
    [("fr", "latin"), ("en", "latin"), ("ar", "arabic"), ("ary", "arabic"), ("ary", "latin")],
)
def test_tts_preserves_transcript_and_passes_profile_and_voice(
    language: str, script: str
) -> None:
    interactions = RecordingInteractions()
    provider = GeminiVoiceProvider(
        api_key="test",
        tts_model="gemini-3.1-flash-tts-preview",
        tts_voice="Kore",
        client_factory=lambda key: SimpleNamespace(interactions=interactions),
    )
    transcript = (
        "N9der nshra7 lik safe answer"
        if script == "latin" and language == "ary"
        else "exact localized answer"
    )

    result = provider.synthesize(transcript, language=language, script=script)

    assert result.audio == b"pcm"
    # Gemini TTS rejects system_instruction: the profile travels as director's
    # notes and the localized transcript is passed through unchanged at the end.
    assert "system_instruction" not in interactions.kwargs
    assert interactions.kwargs["input"] == (
        f"### DIRECTOR'S NOTES\n{_get_tts_profile(language, script).instruction}"
        f"\n\n#### TRANSCRIPT\n{transcript}"
    )
    assert interactions.kwargs["input"].endswith(f"#### TRANSCRIPT\n{transcript}")
    assert interactions.kwargs["generation_config"] == {
        "speech_config": [
            {"language": _get_tts_profile(language, script).speech_language, "voice": "Kore"}
        ]
    }
    assert result.sample_rate == 24000
    assert result.channels == 1
    assert result.sample_width_bytes == 2
