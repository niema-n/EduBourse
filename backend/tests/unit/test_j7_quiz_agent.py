import ast
import inspect
import re
from pathlib import Path

import pytest

from app.api.chat import process_text_message
from app.graph.core import build_graph
from app.graph.state import create_turn_input
from app.learning.profile_service import LearningProfileService
from app.learning.store import InMemoryLearningProfileStore
from app.multilingual.models import LanguageAnalysis
from app.quiz import bank, localized_content
from app.quiz.agent import QuizAgent
from app.quiz.bank import DIAGNOSTIC_BANK, NORMAL_BANK
from app.quiz.localized_content import LOCALIZED_CONTENT, NON_FRENCH_LOCALES
from app.schemas.chat import ChatRequest

ALL_QUIZ_LOCALES = (("fr", "latin"), *NON_FRENCH_LOCALES)


class QuizSupervisor:
    def __init__(self, route="quiz"):
        self.route = route

    def invoke_structured(self, request):
        return {"domain_status": "in_domain", "route": self.route}


def test_unknown_level_starts_six_question_diagnostic():
    service = LearningProfileService(InMemoryLearningProfileStore())
    result = QuizAgent(service)(
        create_turn_input("quiz", language="fr", script="latin", thread_id="a")
    )
    assert result["quiz_session"].phase == "diagnostic"
    assert len(result["quiz_session"].questions) == 6
    assert result["quiz_session"].current_question_index == 0
    assert set(result["workflow_context"].expected_input_values) == {"A", "B", "C", "D"}
    assert "correct_option" not in result["business_answer"]


def test_curated_banks_have_distinct_valid_questions_and_varied_keys():
    all_questions = DIAGNOSTIC_BANK + [
        question for bank in NORMAL_BANK.values() for question in bank
    ]
    assert len(all_questions) == 36
    assert len({question.question_id for question in all_questions}) == 36
    assert len({question.correct_option for question in all_questions}) >= 3
    assert len({tuple(question.options.items()) for question in all_questions}) > 1
    for question in all_questions:
        assert set(question.options) == {"A", "B", "C", "D"}
        assert all(option.strip() for option in question.options.values())
        assert question.explanation.strip()
        assert question.prompt.strip()
        assert question.prompt not in {
            "Which statement best describes this financial concept?",
            "What is a financial concept?",
        }


def test_all_locales_have_question_specific_content():
    questions = DIAGNOSTIC_BANK + [q for bank in NORMAL_BANK.values() for q in bank]
    locales = [
        ("fr", "latin"),
        ("en", "latin"),
        ("ar", "arabic"),
        ("ary", "latin"),
        ("ary", "arabic"),
    ]
    for language, script in locales:
        rendered = [question.render(language, script) for question in questions]
        assert all(prompt and explanation for prompt, _, explanation in rendered)
        assert all(set(options) == {"A", "B", "C", "D"} for _, options, _ in rendered)
        assert all(len(set(options.values())) == 4 for _, options, _ in rendered)
        assert len({prompt for prompt, _, _ in rendered}) == 36
    english = " ".join(
        [
            part
            for question in questions
            for part in (
                question.render("en", "latin")[0],
                *question.render("en", "latin")[1].values(),
                question.render("en", "latin")[2],
            )
        ]
    )
    assert "Une " not in english
    assert "The correct financial meaning of" not in english


def test_key_arabic_diagnostic_answers_keep_canonical_semantics():
    by_id = {question.question_id: question for question in DIAGNOSTIC_BANK}
    assert "رأس مال" in by_id["diag-2"].render("ar", "arabic")[1]["B"]
    assert "السوق الأولي" in by_id["diag-5"].render("ar", "arabic")[1]["C"]
    assert "معلومات" in by_id["diag-6"].render("ar", "arabic")[1]["D"]


def test_darija_latin_has_no_arabic_codepoints_and_arabic_is_distinct():
    questions = DIAGNOSTIC_BANK + [q for bank in NORMAL_BANK.values() for q in bank]
    for question in questions:
        latin = question.render("ary", "latin")
        arabic = question.render("ary", "arabic")
        assert all(ord(char) < 0x600 for char in latin[0] + "".join(latin[1].values()) + latin[2])
        assert any(
            ord(char) >= 0x600 for char in arabic[0] + "".join(arabic[1].values()) + arabic[2]
        )
        assert arabic[0] != latin[0]


def test_quiz_contract_is_explicitly_consumed():
    agent = QuizAgent(LearningProfileService(InMemoryLearningProfileStore()))
    assert agent.contract.specialization_id == "QUIZ_EXPERT_V1"
    assert agent.policy.policy_id == "SENIOR_FINANCIAL_AGENT_POLICY_V1"


def test_diagnostic_scoring_uses_exact_six_answer_boundaries():
    service = LearningProfileService(InMemoryLearningProfileStore())
    agent = QuizAgent(service)
    state = create_turn_input("quiz", language="en", script="latin", thread_id="score")
    result = agent(state)
    for answer in ("A", "B", "C", "D", "A", "B"):
        state = create_turn_input(answer, language="en", script="latin", thread_id="score") | result
        result = agent(state)
    assert service.get_profile("score").learning_level == "beginner"
    assert result["quiz_session"].phase == "quiz"
    assert len(result["quiz_session"].questions) == 10


def test_known_level_skips_diagnostic():
    service = LearningProfileService(InMemoryLearningProfileStore())
    service.set_level("known", "advanced", "manual")
    result = QuizAgent(service)(
        create_turn_input("quiz", language="en", script="latin", thread_id="known")
    )
    assert result["quiz_session"].phase == "quiz"
    assert result["quiz_session"].level == "advanced"
    assert len(result["quiz_session"].questions) == 10


def test_each_answer_returns_explanation_and_next_question():
    agent = QuizAgent(LearningProfileService(InMemoryLearningProfileStore()))
    first = agent(create_turn_input("quiz", language="fr", script="latin", thread_id="turn"))
    second = agent(create_turn_input("A", language="fr", script="latin", thread_id="turn") | first)
    assert "Bonne réponse." in second["business_answer"]
    assert second["quiz_session"].current_question_index == 1
    assert second["workflow_context"].status == "waiting_user"


def test_real_graph_carries_quiz_session_through_checkpoint():
    graph = build_graph(supervisor_provider=QuizSupervisor())
    first = graph.invoke(
        create_turn_input("Fais-moi un quiz", language="fr", script="latin", thread_id="thread"),
        config={"configurable": {"thread_id": "thread"}},
    )
    second = graph.invoke(
        create_turn_input("a", language="fr", script="latin", thread_id="thread"),
        config={"configurable": {"thread_id": "thread"}},
    )
    assert first["workflow_context"].active_agent == "quiz"
    assert second["selected_route"] == "quiz"
    assert second["quiz_session"].current_question_index == 1


def test_paused_quiz_does_not_consume_bare_choice():
    service = LearningProfileService(InMemoryLearningProfileStore())
    agent = QuizAgent(service)
    first = agent(create_turn_input("quiz", language="en", script="latin", thread_id="pause"))
    paused = first["quiz_session"].model_copy(update={"phase": "paused"})
    result = agent(
        create_turn_input("B", language="en", script="latin", thread_id="pause")
        | {"quiz_session": paused}
    )
    assert result["quiz_session"].phase == "paused"
    assert result["quiz_session"].current_question_index == 0


def test_normal_quiz_does_not_change_known_level():
    service = LearningProfileService(InMemoryLearningProfileStore())
    service.set_level("stable", "beginner", "diagnostic")
    agent = QuizAgent(service)
    result = agent(create_turn_input("quiz", language="fr", script="latin", thread_id="stable"))
    for question in result["quiz_session"].questions:
        result = agent(
            create_turn_input(
                question.correct_option, language="fr", script="latin", thread_id="stable"
            )
            | result
        )
    assert service.get_profile("stable").learning_level == "beginner"
    assert service.get_profile("stable").last_quiz_score == 100
    assert len(service.get_profile("stable").quiz_history) == 1


def test_fix4_rejects_answer_self_markers_and_duplicate_choices():
    questions = DIAGNOSTIC_BANK + [q for bank in NORMAL_BANK.values() for q in bank]
    forbidden = ("financially accurate statement", "correct financial meaning", "lma3na s7i7")
    for question in questions:
        for language, script in (
            ("en", "latin"),
            ("ar", "arabic"),
            ("ary", "latin"),
            ("ary", "arabic"),
        ):
            options = question.render(language, script)[1]
            assert len(set(options.values())) == 4
            assert not any(
                token in value.lower() for value in options.values() for token in forbidden
            )


def test_fix4_has_distinct_prompt_and_option_sets_per_locale():
    questions = DIAGNOSTIC_BANK + [q for bank in NORMAL_BANK.values() for q in bank]
    for language, script in (
        ("fr", "latin"),
        ("en", "latin"),
        ("ar", "arabic"),
        ("ary", "latin"),
        ("ary", "arabic"),
    ):
        rendered = [question.render(language, script) for question in questions]
        assert len({prompt for prompt, _, _ in rendered}) == 36
        assert len({tuple(options.items()) for _, options, _ in rendered}) == 36


def test_fix4_diagnostic_correct_answers_preserve_financial_anchors():
    by_id = {question.question_id: question for question in DIAGNOSTIC_BANK}
    assert "capital" in by_id["diag-2"].render("en", "latin")[1]["B"].lower()
    assert "\u0631\u0623\u0633 \u0645\u0627\u0644" in by_id["diag-2"].render("ar", "arabic")[1]["B"]
    assert (
        "\u0627\u0644\u0633\u0648\u0642 \u0627\u0644\u0623\u0648\u0644\u064a"
        in by_id["diag-5"].render("ar", "arabic")[1]["C"]
    )
    assert "information" in by_id["diag-6"].render("en", "latin")[1]["D"].lower()


def test_fix4_darija_script_boundaries_are_clean():
    questions = DIAGNOSTIC_BANK + [q for bank in NORMAL_BANK.values() for q in bank]
    for question in questions:
        latin = question.render("ary", "latin")
        arabic = question.render("ary", "arabic")
        assert all(ord(char) < 0x600 for char in latin[0] + "".join(latin[1].values()) + latin[2])
        assert any(
            ord(char) >= 0x600 for char in arabic[0] + "".join(arabic[1].values()) + arabic[2]
        )


def test_fix5_localized_content_is_static_source_data_not_generated():
    """The localized semantics must be authored strings, not runtime templates."""
    source = Path(inspect.getsourcefile(localized_content)).read_text(encoding="utf-8")
    tree = ast.parse(source)

    assignment = next(
        node
        for node in tree.body
        if isinstance(node, ast.AnnAssign)
        and getattr(node.target, "id", "") == "LOCALIZED_CONTENT"
    )

    # No interpolation of any kind may appear inside the data mapping: an
    # authored variant is a literal string, never a computed one.
    literals = 0
    for node in ast.walk(assignment):
        assert not isinstance(node, ast.JoinedStr), "localized content must not use f-strings"
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
            raise AssertionError("localized content must not use %-formatting")
        if isinstance(node, ast.Call):
            attr = getattr(node.func, "attr", "")
            assert attr not in {
                "format",
                "format_map",
                "join",
            }, "localized content must not build text at import time"
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            literals += 1
    # 36 questions x 4 locales x (1 prompt + 4 options + 1 explanation), plus the
    # dict keys; the count only has to prove the data is literal, not exact shape.
    assert literals >= 36 * 4 * 6

    # The bank must not rebuild localized semantics from topic/level/index.
    bank_source = Path(inspect.getsourcefile(bank)).read_text(encoding="utf-8")
    for banned in (
        "topic.replace",
        "_CONTENT_BY_TOPIC",
        "_AR_LABELS",
        "Lma3na lmali s7i7",
        "financially accurate statement about",
        "correct financial meaning of",
    ):
        assert banned not in bank_source, f"bank.py still contains templating: {banned}"


def test_fix5_explicit_variant_counts_are_complete():
    questions = DIAGNOSTIC_BANK + [q for bank_ in NORMAL_BANK.values() for q in bank_]
    assert len(questions) == 36

    per_locale = {locale: 0 for locale in NON_FRENCH_LOCALES}
    for question in questions:
        authored = LOCALIZED_CONTENT[question.question_id]
        for locale in NON_FRENCH_LOCALES:
            entry = authored[locale]
            assert entry["prompt"].strip()
            assert entry["explanation"].strip()
            assert set(entry["options"]) == {"A", "B", "C", "D"}
            assert all(text.strip() for text in entry["options"].values())
            per_locale[locale] += 1

    assert per_locale[("en", "latin")] == 36
    assert per_locale[("ar", "arabic")] == 36
    assert per_locale[("ary", "latin")] == 36
    assert per_locale[("ary", "arabic")] == 36
    assert sum(per_locale.values()) == 144
    # 144 authored non-French variants + the 36 canonical French rows.
    assert sum(per_locale.values()) + len(questions) == 180


def test_fix5_no_option_announces_itself_as_the_answer():
    questions = DIAGNOSTIC_BANK + [q for bank_ in NORMAL_BANK.values() for q in bank_]
    forbidden = (
        "financially accurate statement",
        "correct financial meaning",
        "correct meaning",
        "right answer",
        "المعنى الصحيح",
        "المعنى المالي الصحيح",
        "الإجابة الصحيحة",
        "lma3na s7i7",
        "lm3na s7i7",
        "lma3na lmali s7i7",
        "jawab s7i7",
    )
    for question in questions:
        for language, script in ALL_QUIZ_LOCALES:
            options = question.render(language, script)[1]
            for token in forbidden:
                assert not any(token in value.lower() for value in options.values()), (
                    f"{question.question_id} {language}/{script} option announces the answer"
                )


def test_fix5_prompts_are_not_made_unique_by_a_counter():
    questions = DIAGNOSTIC_BANK + [q for bank_ in NORMAL_BANK.values() for q in bank_]
    counters = (
        re.compile(r"Question\s*\d+", re.IGNORECASE),
        re.compile(r"Soual\s*\d+", re.IGNORECASE),
        re.compile("السؤال\\s*\\d+"),
    )
    for question in questions:
        for language, script in ALL_QUIZ_LOCALES:
            prompt = question.render(language, script)[0]
            for pattern in counters:
                assert not pattern.search(prompt), (
                    f"{question.question_id} {language}/{script} uses a counter for uniqueness"
                )


def test_fix5_full_localized_bank_quality():
    questions = DIAGNOSTIC_BANK + [q for bank_ in NORMAL_BANK.values() for q in bank_]
    for language, script in ALL_QUIZ_LOCALES:
        rendered = [question.render(language, script) for question in questions]
        assert len({prompt for prompt, _, _ in rendered}) == 36
        assert len({tuple(sorted(options.values())) for _, options, _ in rendered}) == 36
        assert len({explanation for _, _, explanation in rendered}) == 36
        for prompt, options, explanation in rendered:
            assert prompt.strip()
            assert explanation.strip()
            assert len({value.strip() for value in options.values()}) == 4


def test_fix5_diagnostic_semantic_anchors_hold_in_every_locale():
    by_id = {question.question_id: question for question in DIAGNOSTIC_BANK}
    anchors = {
        "diag-1": {
            ("fr", "latin"): "changes de titres",
            ("en", "latin"): "trading of securities",
            ("ar", "arabic"): "تبادل الأوراق المالية",
            ("ary", "latin"): "tbadol dyal l awra9 lmaliya",
            ("ary", "arabic"): "تبادل الأوراق المالية",
        },
        "diag-2": {
            ("fr", "latin"): "capital",
            ("en", "latin"): "capital",
            ("ar", "arabic"): "رأس مال",
            ("ary", "latin"): "ras lmal",
            ("ary", "arabic"): "رأس المال",
        },
        "diag-3": {
            ("fr", "latin"): "plus de risque",
            ("en", "latin"): "more risk",
            ("ar", "arabic"): "مخاطر أكبر",
            ("ary", "latin"): "mkhatir kter",
            ("ary", "arabic"): "مخاطر كثر",
        },
        "diag-4": {
            ("fr", "latin"): "exposition",
            ("en", "latin"): "spreading exposure",
            ("ar", "arabic"): "توزيع الانكشاف",
            ("ary", "latin"): "twzi3",
            ("ary", "arabic"): "توزيع",
        },
        "diag-5": {
            ("fr", "latin"): "marché primaire",
            ("en", "latin"): "primary market",
            ("ar", "arabic"): "السوق الأولي",
            ("ary", "latin"): "Sou9 l2awwali",
            ("ary", "arabic"): "السوق الأولي",
        },
        "diag-6": {
            ("fr", "latin"): "informations utiles",
            ("en", "latin"): "information needed to evaluate",
            ("ar", "arabic"): "المعلومات اللازمة لتقييم",
            ("ary", "latin"): "lma3loumat",
            ("ary", "arabic"): "المعلومات",
        },
    }
    for question_id, per_locale in anchors.items():
        question = by_id[question_id]
        for (language, script), anchor in per_locale.items():
            correct_text = question.render(language, script)[1][question.correct_option]
            assert anchor.lower() in correct_text.lower(), (
                f"{question_id} {language}/{script} lost its financial anchor: {correct_text}"
            )


def test_fix5_english_stock_index_states_the_real_concept():
    question = next(q for q in NORMAL_BANK["beginner"] if q.question_id == "beginner-4")
    prompt, options, explanation = question.render("en", "latin")
    assert question.correct_option == "D"
    assert "The financially accurate statement about index" not in options.values()
    correct = options["D"].lower()
    assert "performance" in correct
    assert "securities" in correct
    assert "index" in prompt.lower()
    assert "securities" in explanation.lower()


def test_fix5_darija_scripts_stay_separated_from_each_other_and_from_msa():
    questions = DIAGNOSTIC_BANK + [q for bank_ in NORMAL_BANK.values() for q in bank_]
    for question in questions:
        latin_prompt, latin_options, latin_explanation = question.render("ary", "latin")
        arabic_prompt, arabic_options, arabic_explanation = question.render("ary", "arabic")
        msa_prompt, msa_options, msa_explanation = question.render("ar", "arabic")

        latin_blob = latin_prompt + "".join(latin_options.values()) + latin_explanation
        assert all(ord(char) < 0x600 for char in latin_blob)

        arabic_blob = arabic_prompt + "".join(arabic_options.values()) + arabic_explanation
        assert any(ord(char) >= 0x600 for char in arabic_blob)

        assert arabic_prompt != latin_prompt
        assert arabic_prompt != msa_prompt
        assert arabic_options != msa_options
        assert arabic_explanation != msa_explanation


def test_fix7_r1_process_text_message_uses_clean_ary_arabic_dynamic_labels(monkeypatch):
    import app.api.chat as chat_api

    service = LearningProfileService(InMemoryLearningProfileStore())
    agent = QuizAgent(service)
    monkeypatch.setattr(
        chat_api.multilingual,
        "analyze",
        lambda text: LanguageAnalysis(
            language="ary-arabic", script="arabic", normalized_text=text, confidence=1.0
        ),
    )
    first = agent(create_turn_input("quiz", language="ary", script="arabic", thread_id="r1"))
    answer = first["quiz_session"].questions[0].correct_option
    second = agent(
        create_turn_input(answer, language="ary", script="arabic", thread_id="r1") | first
    )
    text = second["business_answer"]
    assert "جواب صحيح." in text
    assert "السؤال" in text
    assert "Jawab" not in text
    assert "Soual" not in text
    assert "\u0689" not in text
    assert ".:" not in text

    class QuizGraph:
        def invoke(self, state, config):
            return second | {"selected_route": "quiz", "security_status": "safe"}

    response = process_text_message(
        ChatRequest(message="quiz", thread_id="r1"), QuizGraph()
    )
    assert response.language == "ary"
    assert response.script == "arabic"
    assert "جواب صحيح." in response.answer


def test_fix7_r1_ary_arabic_wrong_feedback_is_clean():
    service = LearningProfileService(InMemoryLearningProfileStore())
    agent = QuizAgent(service)
    first = agent(create_turn_input("quiz", language="ary", script="arabic", thread_id="wrong"))
    question = first["quiz_session"].questions[0]
    wrong = next(choice for choice in ("A", "B", "C", "D") if choice != question.correct_option)
    result = agent(
        create_turn_input(wrong, language="ary", script="arabic", thread_id="wrong") | first
    )
    assert "هاد الجواب ماشي صحيح." in result["business_answer"]
    assert "Jawab" not in result["business_answer"]
    assert "\u0689" not in result["business_answer"]


def test_fix7_r1_ary_arabic_final_summary_has_clean_labels():
    service = LearningProfileService(InMemoryLearningProfileStore())
    service.set_level("summary", "beginner", "manual")
    agent = QuizAgent(service)
    result = agent(create_turn_input("quiz", language="ary", script="arabic", thread_id="summary"))
    for question in result["quiz_session"].questions:
        result = agent(
            create_turn_input(
                question.correct_option, language="ary", script="arabic", thread_id="summary"
            )
            | result
        )
    text = result["business_answer"]
    assert result["quiz_session"].phase == "completed"
    labels = (
        "النتيجة",
        "المستوى ديال المعرفة",
        "نقاط القوة",
        "المواضيع اللي خاصها المراجعة",
        "توصية تعليمية",
    )
    for label in labels:
        assert label in text
    assert ".:" not in text
    assert "\u0689" not in text


def test_fix7_r1_ary_latin_dynamic_labels_contain_no_arabic():
    service = LearningProfileService(InMemoryLearningProfileStore())
    agent = QuizAgent(service)
    first = agent(create_turn_input("quiz", language="ary", script="latin", thread_id="latin"))
    result = agent(
        create_turn_input("A", language="ary", script="latin", thread_id="latin") | first
    )
    dynamic = result["business_answer"]
    assert all(ord(char) < 0x600 for char in dynamic)
    assert "tkÙ" not in dynamic


@pytest.mark.parametrize(
    ("language", "script", "expected"),
    [
        ("fr", "latin", "Quiz annulé."),
        ("en", "latin", "Quiz cancelled."),
        ("ar", "arabic", "تم إلغاء الاختبار."),
        ("ary", "latin", "Telgha lquiz."),
        ("ary", "arabic", "تلغى الكويز."),
    ],
)
def test_fix8_cancel_is_localized_for_all_presentation_locales(language, script, expected):
    service = LearningProfileService(InMemoryLearningProfileStore())
    agent = QuizAgent(service)
    thread_id = f"cancel-{language}-{script}"
    first = agent(create_turn_input("quiz", language=language, script=script, thread_id=thread_id))
    paused = first["quiz_session"].model_copy(update={"phase": "paused"})
    result = agent(
        create_turn_input("cancel quiz", language=language, script=script, thread_id=thread_id)
        | {"quiz_session": paused}
    )
    assert result["quiz_session"].phase == "cancelled"
    assert result["business_answer"] == expected
    assert result["workflow_context"].active_agent is None
    assert service.get_profile(thread_id).quiz_history == []
    assert service.get_profile(thread_id).last_quiz_score is None
    assert result["quiz_session"].current_question_index == 0
    if script == "latin":
        assert all(ord(char) < 0x600 for char in result["business_answer"])
    else:
        assert any(ord(char) >= 0x600 for char in result["business_answer"])
    assert "Quiz cancelled." not in result["business_answer"] or language == "en"


def test_fix8_ar_cancel_is_localized_through_process_text_message(monkeypatch):
    import app.api.chat as chat_api

    monkeypatch.setattr(
        chat_api.multilingual,
        "analyze",
        lambda text: LanguageAnalysis(
            language="ar", script="arabic", normalized_text=text, confidence=1.0
        ),
    )
    service = LearningProfileService(InMemoryLearningProfileStore())
    agent = QuizAgent(service)
    first = agent(create_turn_input("quiz", language="ar", script="arabic", thread_id="ar-cancel"))
    paused = first["quiz_session"].model_copy(update={"phase": "paused"})
    cancelled = agent(
        create_turn_input("cancel quiz", language="ar", script="arabic", thread_id="ar-cancel")
        | {"quiz_session": paused}
    )

    class CancelGraph:
        def invoke(self, state, config):
            return cancelled | {"selected_route": "quiz", "security_status": "safe"}

    response = process_text_message(
        ChatRequest(message="cancel quiz", thread_id="ar-cancel"), CancelGraph()
    )
    assert response.language == "ar"
    assert response.script == "arabic"
    assert response.answer == "تم إلغاء الاختبار."
    assert "ما فهمتش" not in response.answer
