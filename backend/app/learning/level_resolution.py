"""Deterministic, self-reported learning levels shared by learning agents."""

import re

from app.graph.intent import normalize_text

LEVEL_VARIANTS = {
    "beginner": (
        "débutant",
        "débutante",
        "beginner",
        "مبتدئ",
        "مبتدئة",
        "moubtadi",
        "mobtadi",
        "mobtadi2",
    ),
    "intermediate": (
        "intermédiaire",
        "intermediate",
        "متوسط",
        "متوسطة",
        "متوسط المستوى",
        "moutawassit",
        "motawassit",
    ),
    "advanced": (
        "avancé",
        "avancée",
        "advanced",
        "متقدم",
        "متقدمة",
        "mota9adim",
        "motaqadim",
        "mouta9addem",
    ),
}

CLARIFICATIONS = {
    "fr/latin": "Quel est votre niveau actuel en Bourse : débutant, intermédiaire ou avancé ?",
    "en/latin": (
        "What is your current stock-market knowledge level: beginner, intermediate or advanced?"
    ),
    "ar/arabic": "ما مستواك الحالي في البورصة: مبتدئ أم متوسط أم متقدم؟",
    "ary/arabic": "شنو هو المستوى ديالك دابا فالبورصة: مبتدئ، متوسط ولا متقدم؟",
    "ary/latin": "Chno howa mostawa dyalk daba f lboursa: mobtadi, motawassit wla mota9adim?",
}


def extract_level(text: str, *, allow_bare: bool = False) -> str | None:
    text = normalize_text(text).strip(" .!?؟،")
    # Require an affirmative first-person statement, not a level of the market,
    # a requested course's difficulty, or someone else's level.
    prefix = (
        r"(?:je suis (?:une? )?|j' ai (?:un )?niveau |mon niveau (?:est )?|"
        r"i am (?:an? )?|i'm (?:an? )?|my level is |i have an? (?:level of )?|"
        r"انا (?:مستواي )?|مستواي (?:هو )?|المستوى ديالي (?:هو )?|"
        r"ana (?:niveau dyali )?|(?:niveau|mostawa) dyali (?:howa )?)"
    )
    matches = set()
    for level, variants in LEVEL_VARIANTS.items():
        for variant in variants:
            term = re.escape(normalize_text(variant))
            if allow_bare and re.fullmatch(term, text):
                matches.add(level)
            if re.search(r"(?<!\w)" + prefix + term + r"(?!\w)", text):
                matches.add(level)
    return matches.pop() if len(matches) == 1 else None


def requests_diagnostic(text: str) -> bool:
    text = normalize_text(text)
    return bool(
        re.search(
            r"\b(?:evaluer|evalue|tester|teste) (?:mon |moi|mes connaissances)|"
            r"\b(?:fais.moi|faire|un|le) (?:un )?diagnostic\b|"
            r"\b(?:assess|test|evaluate) my (?:level|knowledge)|\bdiagnostic quiz\b|"
            r"(?:قيم|اختبر|تقييم|اختبار) (?:مستواي|معرفتي)|"
            r"(?:قيم|اختبر) المستوى ديالي|"
            r"\b(?:9iyem|9ayem|testi|qiyem) (?:li |lia )?(?:mostawa|niveau)\b",
            text,
        )
    )


def awaiting_level(state) -> bool:
    context = state.get("workflow_context")
    if isinstance(context, dict):
        return (
            context.get("workflow_step") == "learning_level"
            and context.get("status") == "waiting_user"
        )
    return (
        getattr(context, "workflow_step", None) == "learning_level"
        and getattr(context, "status", None) == "waiting_user"
    )


def resolve_level(state, service):
    key = state.get("thread_id") or state.get("session_id") or "anonymous"
    text = state.get("normalized_message") or state.get("user_input", "")
    diagnostic = requests_diagnostic(text)
    explicit = None if diagnostic else extract_level(text, allow_bare=awaiting_level(state))
    profile = service.get_profile(key)
    if explicit and (profile.learning_level != explicit or profile.level_source != "manual"):
        profile = service.set_level(key, explicit, "manual")
    return profile, explicit, diagnostic


def clarify_level(state, agent):
    from app.graph.workflow_context import WorkflowContextService

    locale = f"{state.get('language', 'fr')}/{state.get('script', 'latin')}"
    return {
        "assessment_required": False,
        "workflow_context": WorkflowContextService().start_workflow(
            active_agent=agent,
            active_workflow=f"{agent}_level_selection",
            workflow_step="learning_level",
            expected_input_kind="choice",
            expected_input_values=[term for terms in LEVEL_VARIANTS.values() for term in terms],
        ),
        "business_answer": CLARIFICATIONS.get(locale, CLARIFICATIONS["fr/latin"]),
        "response_key": agent,
        "status": "completed",
    }
