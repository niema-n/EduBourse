"""Checkpoint-friendly multi-turn quiz agent."""
# ruff: noqa: E501
from datetime import UTC, datetime
from uuid import uuid4

from app.agents.contracts import AGENT_CONTRACTS, SHARED_POLICY
from app.graph.workflow_context import ConversationWorkflowContext, WorkflowContextService
from app.learning.models import LearningLevel
from app.learning.profile_service import LearningProfileService
from app.learning.store import InMemoryLearningProfileStore
from app.quiz.bank import DIAGNOSTIC_BANK, NORMAL_BANK
from app.quiz.models import QuizQuestion, QuizSession

CHOICES = {"A", "B", "C", "D"}

_QUIZ_MESSAGES = {
    "fr/latin": (
        "Bonne réponse.", "Cette réponse n'est pas correcte.", "Score",
        "Niveau de connaissance", "Points forts", "Points à revoir",
        "Recommandation pédagogique",
    ),
    "en/latin": (
        "Correct.", "That answer is not correct.", "Score", "Knowledge level",
        "Strengths", "Topics to review", "Learning recommendation",
    ),
    "ar/arabic": (
        "إجابة صحيحة.", "هذه الإجابة غير صحيحة.", "النتيجة",
        "مستوى المعرفة", "نقاط القوة", "مواضيع للمراجعة", "توصية تعليمية",
    ),
    "ary/latin": (
        "Jawab s7i7.", "Had ljawab machi s7i7.", "Ntiija",
        "Mostawa dyal lma3rifa", "N9at l9owa",
        "Mawadi3 khas-ha lmoraaja3a", "Tawsiya ta3limiya",
    ),
    "ary/arabic": (
        "جواب صحيح.", "هاد الجواب ماشي صحيح.", "النتيجة", "المستوى ديال المعرفة",
        "نقاط القوة", "المواضيع اللي خاصها المراجعة", "توصية تعليمية",
    ),
}
_LEVEL_LABELS = {
    "fr/latin": {"beginner": "Débutant", "intermediate": "Intermédiaire", "advanced": "Avancé"},
    "en/latin": {"beginner": "Beginner", "intermediate": "Intermediate", "advanced": "Advanced"},
    "ar/arabic": {"beginner": "مبتدئ", "intermediate": "متوسط", "advanced": "متقدم"},
    "ary/latin": {"beginner": "Moubtadi", "intermediate": "Moutawassit", "advanced": "Mouta9addem"},
    "ary/arabic": {"beginner": "مبتدئ", "intermediate": "متوسط", "advanced": "متقدم"},
}
_CANCEL_MESSAGES = {
    "fr/latin": "Quiz annulé.",
    "en/latin": "Quiz cancelled.",
    "ar/arabic": "تم إلغاء الاختبار.",
    "ary/latin": "Telgha lquiz.",
    "ary/arabic": "تلغى الكويز.",
}


def _locale_key(language: str, script: str) -> str:
    if language == "fr" and script == "latin":
        return "fr/latin"
    if language == "en" and script == "latin":
        return "en/latin"
    if language == "ar" and script == "arabic":
        return "ar/arabic"
    if language == "ary" and script == "arabic":
        return "ary/arabic"
    if language == "ary" and script == "latin":
        return "ary/latin"
    return f"{language}/{script}"


def _new_session(profile_key, phase, questions, level=None, locale=None):
    if locale is None:
        language, script = "fr", "latin"
    elif isinstance(locale, QuizSession):
        language, script = locale.language, locale.script
    else:
        language = locale.get("language", "fr")
        script = locale.get("script", "latin")
    return QuizSession(
        quiz_id=f"quiz-{uuid4().hex}",
        profile_key=profile_key,
        phase=phase,
        level=level,
        topic="financial_education",
        questions=questions,
        started_at=datetime.now(UTC).isoformat(),
        language=language,
        script=script,
    )


def _question_text(question: QuizQuestion, language: str, script: str, index: int, total: int) -> str:
    locale = _locale_key(language, script)
    labels = {
        "fr/latin": "Question",
        "en/latin": "Question",
        "ar/arabic": "السؤال",
        "ary/latin": "Soual",
        "ary/arabic": "السؤال",
    }
    label = labels.get(locale, "Question")
    prompt, options, _ = question.render(language, script)
    choices = "\n".join(f"{key}. {value}" for key, value in options.items())
    return f"{label} {index + 1}/{total}\n{prompt}\n{choices}"


class QuizAgent:
    def __init__(self, profile_service: LearningProfileService | None = None):
        self.contract = AGENT_CONTRACTS["quiz"]
        self.policy = SHARED_POLICY
        self.profile_service = profile_service or LearningProfileService(
            InMemoryLearningProfileStore()
        )

    def __call__(self, state):
        profile_key = state.get("thread_id") or state.get("session_id") or "anonymous"
        profile = self.profile_service.get_profile(profile_key)
        session = state.get("quiz_session")
        if isinstance(session, dict):
            session = QuizSession.model_validate(session)
        text = state.get("user_input", "").strip().casefold()
        legacy_context = state.get("workflow_context")
        if (
            session is None
            and isinstance(legacy_context, ConversationWorkflowContext)
            and legacy_context.active_agent == "quiz"
            and text.upper() in CHOICES
        ):
            return {
                "workflow_context": legacy_context,
                "business_answer": "Quiz continuation received.",
                "response_key": "quiz",
                "status": "completed",
            }
        if session is None and state.get("assessment_answers"):
            from app.graph.workflows import assessment_node, learner_profile_node

            assessed = assessment_node(state)
            return {
                **assessed,
                **learner_profile_node(state | assessed),
                "business_answer": "The educational assessment has been recorded.",
                "response_key": "quiz",
                "status": "completed",
            }
        if session is not None and session.phase == "paused":
            if text in {"cancel quiz", "annuler le quiz", "annuler quiz"}:
                return self._cancel(session)
            if len(state.get("user_input", "").strip()) == 1 and text.upper() in CHOICES:
                return self._ask(
                    session, state, "Please explicitly resume the quiz before answering."
                )
            session = session.model_copy(
                update={"phase": "diagnostic" if session.level is None else "quiz"}
            )
        from app.learning.level_resolution import requests_diagnostic

        if requests_diagnostic(state.get("normalized_message") or text):
            return self._ask(
                _new_session(profile_key, "diagnostic", DIAGNOSTIC_BANK, locale=state), state
            )
        if session is None or session.phase in {"completed", "cancelled"}:
            if profile.learning_level is None:
                return self._ask(
                    _new_session(profile_key, "diagnostic", DIAGNOSTIC_BANK, locale=state), state
                )
            return self._ask(
                _new_session(
                    profile_key,
                    "quiz",
                    NORMAL_BANK[profile.learning_level],
                    profile.learning_level,
                    locale=state,
                ),
                state,
            )
        if session.current_question_index >= len(session.questions):
            return self._finish(session, state)
        raw = state.get("user_input", "").strip()
        if len(raw) != 1 or raw.upper() not in CHOICES:
            return self._ask(session, state)
        question = session.questions[session.current_question_index]
        _, _, explanation = question.render(session.language, session.script)
        choice = raw.upper()
        is_correct = choice == question.correct_option
        session = session.model_copy(
            update={
                "answers": [*session.answers, choice],
                "correct_answers": [*session.correct_answers, is_correct],
                "correct_count": session.correct_count + int(is_correct),
                "current_question_index": session.current_question_index + 1,
            }
        )
        locale = _locale_key(session.language, session.script)
        messages = _QUIZ_MESSAGES.get(locale, _QUIZ_MESSAGES["fr/latin"])
        prefix = messages[0] if is_correct else messages[1]
        if session.complete and session.phase == "diagnostic":
            level: LearningLevel = (
                "beginner"
                if session.correct_count <= 2
                else "intermediate"
                if session.correct_count <= 4
                else "advanced"
            )
            self.profile_service.set_level(profile_key, level, "diagnostic")
            self.profile_service.mark_diagnostic_completed(profile_key)
            normal = _new_session(profile_key, "quiz", NORMAL_BANK[level], level, locale=session)
            level_label = _LEVEL_LABELS[locale][level]
            diagnostic_labels = {
                "fr/latin": "Niveau diagnostiqué",
                "en/latin": "Diagnosed level",
                "ar/arabic": "المستوى المشخص",
                "ary/latin": "Lmostawa li tchekhlas",
                "ary/arabic": "المستوى اللي تشخص",
            }
            prefix = f"{prefix} {diagnostic_labels[locale]}:"
            return self._ask(normal, state, f"{prefix} {level_label}.")
        if session.complete:
            return self._finish(session, state, f"{prefix} {explanation}")
        return self._ask(session, state, f"{prefix} {explanation}")

    def _ask(self, session, state, prefix=""):
        question = session.questions[session.current_question_index]
        context = ConversationWorkflowContext(
            active_agent="quiz",
            active_workflow="quiz_diagnostic" if session.phase == "diagnostic" else "quiz_session",
            workflow_step=f"question_{session.current_question_index + 1}",
            status="waiting_user",
            expected_input_kind="choice",
            expected_input_values=["A", "B", "C", "D"],
        )
        question_text = _question_text(
            question,
            session.language,
            session.script,
            session.current_question_index,
            len(session.questions),
        )
        return {
            "quiz_session": session,
            "workflow_context": context,
            "business_answer": f"{prefix}\n{question_text}".strip(),
            "response_key": "quiz",
            "status": "completed",
        }

    def _finish(self, session, state, prefix=""):
        total = len(session.questions)
        score = round(session.correct_count / total * 100, 2)
        self.profile_service.record_quiz_attempt(
            session.profile_key,
            quiz_id=session.quiz_id,
            topic=session.topic,
            level=session.level or "beginner",
            score_percent=score,
            correct_count=session.correct_count,
            total_questions=total,
            completed_at=datetime.now(UTC).isoformat(),
        )
        locale = _locale_key(session.language, session.script)
        messages = _QUIZ_MESSAGES.get(locale, _QUIZ_MESSAGES["fr/latin"])
        topic_results: dict[str, list[bool]] = {}
        for question, result in zip(session.questions, session.correct_answers, strict=False):
            topic_results.setdefault(question.topic, []).append(result)
        strengths = sorted(topic for topic, values in topic_results.items() if all(values))
        review = sorted(topic for topic, values in topic_results.items() if not all(values))
        for topic in review:
            self.profile_service.mark_topic_to_review(session.profile_key, topic)
        strengths_text = ", ".join(strengths) or "None"
        review_text = ", ".join(review) or "None"
        result_text = (
            f"{prefix}\n{messages[2]}: {session.correct_count}/{total}\n"
            f"{messages[3]}: {_LEVEL_LABELS[locale][session.level or 'beginner']}\n"
            f"{messages[4]}: {strengths_text}\n{messages[5]}: {review_text}\n"
            f"{messages[6]}: {self._recommendation(locale)}"
        )
        return {
            "quiz_session": session.model_copy(update={"phase": "completed"}),
            "workflow_context": WorkflowContextService().complete_workflow(
                state.get("workflow_context", ConversationWorkflowContext())
            ),
            "business_answer": result_text,
            "response_key": "quiz",
            "status": "completed",
        }

    def _cancel(self, session):
        message = _CANCEL_MESSAGES.get(_locale_key(session.language, session.script), "Quiz cancelled.")
        return {
            "quiz_session": session.model_copy(update={"phase": "cancelled"}),
            "workflow_context": WorkflowContextService().clear_workflow(),
            "business_answer": message,
            "response_key": "quiz",
            "status": "completed",
        }

    @staticmethod
    def _recommendation(language):
        if language == "ary/arabic":
            return "راجع المواضيع اللي خاصها المراجعة قبل ما تكمل."
        if language == "ary/latin":
            return "Raje3 lmawadi3 li khas-ha lmoraaja3a 9bel ma tkmmel."
        return {
            "fr/latin": "Révisez les thèmes à revoir avant de continuer.",
            "en/latin": "Review the listed topics before continuing.",
            "ar/arabic": "راجع المواضيع المحددة قبل المتابعة.",
        }.get(language, "Review the listed topics before continuing.")


def run_quiz_agent(state, profile_service=None):
    return QuizAgent(profile_service)(state)
