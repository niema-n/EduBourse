"""Shared-profile Formation learning-path agent."""
# ruff: noqa: E501
from uuid import uuid4

from app.agents.contracts import AGENT_CONTRACTS, SHARED_POLICY
from app.formation.content import modules_for
from app.formation.models import FormationSession
from app.graph.workflow_context import ConversationWorkflowContext, WorkflowContextService
from app.learning.level_resolution import clarify_level, resolve_level
from app.learning.profile_service import LearningProfileService

_CONTINUE_WORDS = {
    "continue", "next", "suivant", "continuer ma formation", "continuer", "kmel",
    "\u0643\u0645\u0644",
    "nkml", "nkemlo", "kmel formation", "\u0627\u0644\u062a\u0627\u0644\u064a", "\u0645\u062a\u0627\u0628\u0639\u0629", "\u0648\u0627\u0635\u0644", "\u0623\u0643\u0645\u0644", "\u062a\u0627\u0628\u0639",
}
_PAUSE_WORDS = {"pause", "pauser", "mettre en pause"}
_CANCEL_WORDS = {
    "cancel formation", "cancel training", "cancel", "annuler la formation", "annuler formation", "annuler",
    "lghi formation", "bghit nlghi formation", "telgha formation", "\u0625\u0644\u063a\u0627\u0621 \u0627\u0644\u062a\u0643\u0648\u064a\u0646", "\u0625\u0644\u063a\u0627\u0621 \u0627\u0644\u0645\u0633\u0627\u0631", "\u0623\u0644\u063a\u0650 \u0627\u0644\u062a\u0643\u0648\u064a\u0646", "\u0644\u063a\u064a \u0627\u0644\u062a\u0643\u0648\u064a\u0646", "\u0644\u063a\u064a \u0627\u0644\u0645\u0633\u0627\u0631",
}
_MESSAGES = {
    "fr/latin": {"assessment": "Avant de commencer votre formation, je dois d'abord déterminer votre niveau de connaissance. Un quiz diagnostique de six questions va commencer.", "progress": "Parcours {level}, module {index}/{total}: {title}", "objective": "Objectif: {value}", "lesson": "Leçon: {value}", "points": "Points clés: {value}", "checkpoint": "Question de vérification: {value}", "next": "Répondez à la question ou dites suivant pour passer au module suivant.", "paused": "La formation est en pause. Dites continuer ma formation pour reprendre.", "cancelled": "Formation annulée.", "completed": "Parcours terminé. Vous pouvez revoir les notions ou faire un quiz pour réévaluer vos connaissances."},
    "en/latin": {"assessment": "Before starting your learning path, I first need to determine your knowledge level. A six-question diagnostic quiz will now begin.", "progress": "Path {level}, module {index}/{total}: {title}", "objective": "Objective: {value}", "lesson": "Lesson: {value}", "points": "Key points: {value}", "checkpoint": "Checkpoint question: {value}", "next": "Answer the question or say next to move to the next module.", "paused": "The learning path is paused. Say continue to resume.", "cancelled": "Learning path cancelled.", "completed": "Path completed. You can review the concepts or take a quiz to reassess your knowledge."},
    "ar/arabic": {"assessment": "\u0642\u0628\u0644 \u0645\u0627 \u062a\u0628\u062f\u0627 \u0627\u0644\u0645\u0633\u0627\u0631 \u0627\u0644\u062a\u0639\u0644\u064a\u0645\u064a\u060c \u062e\u0627\u0635\u0646\u064a \u0646\u062d\u062f\u062f \u0645\u0633\u062a\u0648\u0649 \u0627\u0644\u0645\u0639\u0631\u0641\u0629 \u062f\u064a\u0627\u0644\u0643. \u063a\u0627\u062f\u064a \u064a\u0628\u062f\u0627 \u062f\u0627\u0628\u0627 \u0627\u062e\u062a\u0628\u0627\u0631 \u062a\u0634\u062e\u064a\u0635\u064a \u0641\u064a\u0647 \u0633\u062a\u0629 \u062f\u064a\u0627\u0644 \u0627\u0644\u0623\u0633\u0626\u0644\u0629.", "progress": "\u0627\u0644\u0645\u0633\u0627\u0631 {level}\u060c \u0627\u0644\u0648\u062d\u062f\u0629 {index}/{total}: {title}", "objective": "\u0627\u0644\u0647\u062f\u0641: {value}", "lesson": "\u0627\u0644\u062f\u0631\u0633: {value}", "points": "\u0627\u0644\u0646\u0642\u0627\u0637 \u0627\u0644\u0623\u0633\u0627\u0633\u064a\u0629: {value}", "checkpoint": "\u0633\u0624\u0627\u0644 \u0627\u0644\u062a\u062d\u0642\u0642: {value}", "next": "\u062c\u0627\u0648\u0628 \u0639\u0644\u0649 \u0627\u0644\u0633\u0624\u0627\u0644 \u0623\u0648 \u0642\u0644 \u0627\u0644\u062a\u0627\u0644\u064a \u0628\u0627\u0634 \u062a\u062f\u0648\u0632 \u0644\u0644\u0648\u062d\u062f\u0629 \u0627\u0644\u0645\u0648\u0627\u0644\u064a\u0629.", "paused": "\u0627\u0644\u0645\u0633\u0627\u0631 \u0627\u0644\u062a\u0639\u0644\u064a\u0645\u064a \u0645\u0648\u0642\u0641. \u0642\u0644 \u062a\u0627\u0628\u0639 \u0627\u0644\u0645\u0633\u0627\u0631 \u0628\u0627\u0634 \u062a\u0643\u0645\u0644.", "cancelled": "\u062a\u0645 \u0625\u0644\u063a\u0627\u0621 \u0627\u0644\u0645\u0633\u0627\u0631 \u0627\u0644\u062a\u0639\u0644\u064a\u0645\u064a.", "completed": "\u0643\u0645\u0644\u062a\u064a \u0627\u0644\u0645\u0633\u0627\u0631. \u062a\u0642\u062f\u0631 \u062a\u0631\u0627\u062c\u0639 \u0627\u0644\u0645\u0641\u0627\u0647\u064a\u0645 \u0623\u0648 \u062a\u062f\u064a\u0631 \u0627\u062e\u062a\u0628\u0627\u0631 \u0628\u0627\u0634 \u062a\u0639\u0627\u0648\u062f \u062a\u0642\u064a\u0633 \u0627\u0644\u0645\u0639\u0631\u0641\u0629 \u062f\u064a\u0627\u0644\u0643."},
    "ary/latin": {"assessment": "9bel ma tebda lmassar ta3limi, khasni n3ref mostawa dyal lma3rifa dyalk. Ghadi ybda daba quiz tashkhisi fih 6 dyal l2as2ila.", "progress": "Massar {level}, module {index}/{total}: {title}", "objective": "Lhadaf: {value}", "lesson": "Dars: {value}", "points": "N9at l2assasiya: {value}", "checkpoint": "Soual dyal tta2akod: {value}", "next": "Jawb 3la soual wla gol suivant bach tdouz lmodule jay.", "paused": "Lmassar mwe9ef. Gol continuer ma formation bach tkmmel.", "cancelled": "Telgha lmassar ta3limi.", "completed": "Sali lmassar. T9der traje3 lmafahim wla tdir quiz bach t3awed t9iss lma3rifa."},
    "ary/arabic": {"assessment": "\u0642\u0628\u0644 \u0645\u0627 \u062a\u0628\u062f\u0627 \u0627\u0644\u0645\u0633\u0627\u0631 \u0627\u0644\u062a\u0639\u0644\u064a\u0645\u064a\u060c \u062e\u0627\u0635\u0646\u064a \u0646\u062d\u062f\u062f \u0627\u0644\u0645\u0633\u062a\u0648\u0649 \u062f\u064a\u0627\u0644 \u0627\u0644\u0645\u0639\u0631\u0641\u0629 \u062f\u064a\u0627\u0644\u0643. \u063a\u0627\u062f\u064a \u064a\u0628\u062f\u0627 \u062f\u0627\u0628\u0627 \u0627\u062e\u062a\u0628\u0627\u0631 \u062a\u0634\u062e\u064a\u0635\u064a \u0641\u064a\u0647 \u0633\u062a\u0629 \u062f\u064a\u0627\u0644 \u0627\u0644\u0623\u0633\u0626\u0644\u0629.", "progress": "\u0627\u0644\u0645\u0633\u0627\u0631 {level}\u060c \u0627\u0644\u0648\u062d\u062f\u0629 {index}/{total}: {title}", "objective": "\u0627\u0644\u0647\u062f\u0641: {value}", "lesson": "\u0627\u0644\u062f\u0631\u0633: {value}", "points": "\u0627\u0644\u0646\u0642\u0627\u0637 \u0627\u0644\u0623\u0633\u0627\u0633\u064a\u0629: {value}", "checkpoint": "\u0633\u0624\u0627\u0644 \u0627\u0644\u062a\u062d\u0642\u0642: {value}", "next": "\u062c\u0627\u0648\u0628 \u0639\u0644\u0649 \u0627\u0644\u0633\u0624\u0627\u0644 \u0623\u0648 \u0642\u0644 \u0627\u0644\u062a\u0627\u0644\u064a \u0628\u0627\u0634 \u062a\u062f\u0648\u0632 \u0644\u0644\u0648\u062d\u062f\u0629 \u0627\u0644\u0645\u0648\u0627\u0644\u064a\u0629.", "paused": "\u0627\u0644\u0645\u0633\u0627\u0631 \u0627\u0644\u062a\u0639\u0644\u064a\u0645\u064a \u0645\u0648\u0642\u0641. \u0642\u0644 \u062a\u0627\u0628\u0639 \u0627\u0644\u0645\u0633\u0627\u0631 \u0628\u0627\u0634 \u062a\u0643\u0645\u0644.", "cancelled": "\u062a\u0644\u063a\u0649 \u0627\u0644\u0645\u0633\u0627\u0631 \u0627\u0644\u062a\u0639\u0644\u064a\u0645\u064a.", "completed": "\u0643\u0645\u0644\u062a\u064a \u0627\u0644\u0645\u0633\u0627\u0631. \u062a\u0642\u062f\u0631 \u062a\u0631\u0627\u062c\u0639 \u0627\u0644\u0645\u0641\u0627\u0647\u064a\u0645 \u0623\u0648 \u062a\u062f\u064a\u0631 \u0627\u062e\u062a\u0628\u0627\u0631 \u0628\u0627\u0634 \u062a\u0639\u0627\u0648\u062f \u062a\u0642\u064a\u0633 \u0627\u0644\u0645\u0639\u0631\u0641\u0629 \u062f\u064a\u0627\u0644\u0643."},
}
_LEVEL_NAMES = {
    "fr/latin": {"beginner": "débutant", "intermediate": "intermédiaire", "advanced": "avancé"},
    "en/latin": {"beginner": "beginner", "intermediate": "intermediate", "advanced": "advanced"},
    "ar/arabic": {"beginner": "\u0645\u0628\u062a\u062f\u0626", "intermediate": "\u0645\u062a\u0648\u0633\u0637", "advanced": "\u0645\u062a\u0642\u062f\u0645"},
    "ary/latin": {"beginner": "moubtadi", "intermediate": "moutawassit", "advanced": "mouta9addem"},
    "ary/arabic": {"beginner": "\u0645\u0628\u062a\u062f\u0626", "intermediate": "\u0645\u062a\u0648\u0633\u0637", "advanced": "\u0645\u062a\u0642\u062f\u0645"},
}

def _locale(value) -> str:
    return "ary/arabic" if value.language == "ary" and value.script == "arabic" else f"{value.language}/{value.script}"


_SOURCE_LABELS = {
    "fr/latin": "Contenu pédagogique interne EduBourse",
    "en/latin": "Internal EduBourse learning content",
    "ar/arabic": "محتوى تعليمي داخلي من EduBourse",
    "ary/arabic": "محتوى تعليمي داخلي ديال EduBourse",
    "ary/latin": "Mo7tawa ta3limi dakhili dyal EduBourse",
}


def _module_source(session, modules, content):
    locale = _locale(session)
    return {
        "label": _SOURCE_LABELS[locale],
        "description": _MESSAGES[locale]["progress"].format(
            level=_LEVEL_NAMES[locale][session.level],
            index=session.current_module_index + 1, total=len(modules), title=content["title"],
        ),
        "level": session.level,
        "path_id": session.path_id,
        "module_id": modules[session.current_module_index]["module_id"],
        "module_title": content["title"],
        "module_number": session.current_module_index + 1,
        "module_count": len(modules),
    }

def _context(status="waiting_user"):
    return WorkflowContextService().start_workflow(active_agent="formation_elearning", active_workflow="formation_learning_path", workflow_step="module", expected_input_kind="confirmation", expected_input_values=tuple(sorted(_CONTINUE_WORDS))).model_copy(update={"status": status})

class FormationAgent:
    def __init__(self, profile_service: LearningProfileService):
        self.contract = AGENT_CONTRACTS["formation_elearning"]
        self.policy = SHARED_POLICY
        self.profile_service = profile_service

    def __call__(self, state):
        profile_key = state.get("thread_id") or state.get("session_id") or "anonymous"
        profile, explicit_level, diagnostic = resolve_level(state, self.profile_service)
        language, script = state.get("language", "fr"), state.get("script", "latin")
        locale = f"{language}/{script}" if not (language == "ary" and script == "arabic") else "ary/arabic"
        session = state.get("formation_session")
        if isinstance(session, dict):
            session = FormationSession.model_validate(session)
        if explicit_level and (session is None or session.level != explicit_level):
            session = None
        if diagnostic:
            formation = FormationSession(formation_id=f"formation-{uuid4().hex}", path_id="pending_diagnostic", status="waiting_for_diagnostic", language=language, script=script)
            return {"formation_session": formation, "assessment_required": True, "business_answer": _MESSAGES[locale]["assessment"], "response_key": "formation_elearning", "status": "completed"}
        if profile.learning_level is None:
            return clarify_level(state, "formation_elearning") | {"formation_session": None}
        text = state.get("user_input", "").strip().casefold()
        if session is not None and session.status == "paused":
            if text in _CANCEL_WORDS:
                return self._cancel(session)
            if text not in _CONTINUE_WORDS:
                return self._paused(session)
            session = session.model_copy(update={"status": "active"})
        if text in _CANCEL_WORDS and session is not None:
            return self._cancel(session)
        if session is not None and session.status == "completed":
            return {
                "formation_session": session,
                "workflow_context": WorkflowContextService().complete_workflow(
                    state.get("workflow_context", ConversationWorkflowContext())
                ),
                "business_answer": _MESSAGES[locale]["completed"],
                "response_key": "formation_elearning",
                "status": "completed",
            }
        level = profile.learning_level
        if session is None or session.status in {"completed", "cancelled", "waiting_for_diagnostic"}:
            session = FormationSession(formation_id=session.formation_id if session and session.status == "waiting_for_diagnostic" else f"formation-{uuid4().hex}", level=level, path_id=f"{level}_financial_learning", status="active", language=language, script=script)
            self.profile_service.set_learning_path(profile_key, session.path_id)
        elif session.language != language or session.script != script:
            language, script, locale = session.language, session.script, _locale(session)
        modules = modules_for(session.level)
        if text in _PAUSE_WORDS:
            return self._paused(session)
        if text in _CONTINUE_WORDS and state.get("formation_session") is not None:
            current = modules[session.current_module_index]
            self.profile_service.mark_module_completed(profile_key, current["module_id"])
            session = session.model_copy(update={"current_module_index": session.current_module_index + 1, "completed_modules": list(dict.fromkeys([*session.completed_modules, current["module_id"]]))})
            if session.current_module_index >= len(modules):
                return {"formation_session": session.model_copy(update={"status": "completed"}), "workflow_context": WorkflowContextService().complete_workflow(state.get("workflow_context", ConversationWorkflowContext())), "business_answer": _MESSAGES[locale]["completed"], "response_key": "formation_elearning", "status": "completed"}
        content = modules[session.current_module_index]["content"][locale]
        rendered = self._render(_MESSAGES[locale], session, modules, content)
        return {"formation_session": session, "assessment_required": False, "workflow_context": _context(), "business_answer": rendered, "response_key": "formation_elearning", "status": "completed", "internal_pedagogical_source": _module_source(session, modules, content)}

    @staticmethod
    def _render(messages, session, modules, content):
        return "\n".join((messages["progress"].format(level=_LEVEL_NAMES[_locale(session)][session.level], index=session.current_module_index + 1, total=len(modules), title=content["title"]), messages["objective"].format(value=content["objective"]), messages["lesson"].format(value=content["lesson"]), messages["points"].format(value="; ".join(content["key_points"])), messages["checkpoint"].format(value=content["checkpoint"]), messages["next"]))

    def _paused(self, session):
        return {"formation_session": session.model_copy(update={"status": "paused"}), "workflow_context": _context("paused"), "business_answer": _MESSAGES[_locale(session)]["paused"], "response_key": "formation_elearning", "status": "completed"}

    def _cancel(self, session):
        return {"formation_session": session.model_copy(update={"status": "cancelled"}), "workflow_context": WorkflowContextService().clear_workflow(), "business_answer": _MESSAGES[_locale(session)]["cancelled"], "response_key": "formation_elearning", "status": "completed"}

def run_formation_agent(state, profile_service):
    return FormationAgent(profile_service)(state)
