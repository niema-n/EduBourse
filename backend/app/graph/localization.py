"""Deterministic response localization for the text-to-text API boundary."""

# Translation tables intentionally keep complete user-facing sentences together.
# ruff: noqa: E501

from app.agents.contracts import OUT_OF_DOMAIN_MESSAGES
from app.graph.language_adapter import BusinessLanguage, BusinessScript
from app.multilingual.script_detector import count_scripts
from app.multilingual.script_validator import validate_script

MESSAGES: dict[BusinessLanguage, dict[str, str]] = {
    "fr": {
        "pedagogie": "Je peux expliquer les actions, obligations, indices et risques a visee educative.",
        "formation_elearning": "Je peux vous presenter les parcours de formation disponibles a titre educatif.",
        "orientation": "Je peux vous orienter vers un parcours d apprentissage adapte a vos objectifs.",
        "cisi": "Les informations detaillees sur CISI necessitent un catalogue officiel.",
        "quiz": "Je peux proposer un quiz educatif sur les marches et les instruments financiers.",
        "championnat": "Je peux presenter le Championnat de la Bourse et e-Bourse a titre educatif.",
        "support_ecole": "Je peux aider avec l acces, l inscription et la navigation de l Ecole de la Bourse.",
        "out_of_domain": "Je suis specialise en Bourse, marches de capitaux et education financiere.",
        "fallback": "Je n ai pas compris la demande. Je peux aider sur la Bourse et l education financiere.",
        "blocked": "Je ne peux pas recommander un titre ou choisir un investissement pour vous.",
        "error": "Une reponse controlee est temporairement indisponible. Veuillez reformuler votre demande.",
    },
    "en": {
        "pedagogie": "I can explain stocks, bonds, indexes, and risk for educational purposes.",
        "formation_elearning": "I can present available learning paths for educational purposes.",
        "orientation": "I can guide you toward a learning path that matches your goals.",
        "cisi": "Detailed CISI information requires an official catalog.",
        "quiz": "I can offer an educational quiz about markets and financial instruments.",
        "championnat": "I can explain the Bourse Championship and e-Bourse for educational purposes.",
        "support_ecole": "I can help with access, registration, and Bourse School navigation.",
        "out_of_domain": "I specialize in markets, the stock exchange, and financial education.",
        "fallback": "I could not understand the request. I can help with markets and financial education.",
        "blocked": "I cannot recommend a security or choose an investment for you.",
        "error": "A controlled response is temporarily unavailable. Please rephrase your request.",
    },
    "ar": {
        "pedagogie": "يمكنني شرح الأسهم والسندات والمؤشرات والمخاطر لأغراض تعليمية.",
        "formation_elearning": "يمكنني عرض مسارات التعلم المتاحة لأغراض تعليمية.",
        "orientation": "يمكنني إرشادك إلى مسار تعلم يناسب أهدافك.",
        "cisi": "تحتاج المعلومات التفصيلية حول CISI إلى دليل رسمي.",
        "quiz": "يمكنني تقديم اختبار تعليمي حول الأسواق والأدوات المالية.",
        "championnat": "يمكنني شرح بطولة البورصة و e-Bourse لأغراض تعليمية.",
        "support_ecole": "يمكنني المساعدة في الدخول والتسجيل والتنقل في مدرسة البورصة.",
        "out_of_domain": "اختصاصي هو البورصة والأسواق والتثقيف المالي.",
        "fallback": "لم أفهم الطلب. يمكنني المساعدة في البورصة والتثقيف المالي.",
        "blocked": "لا يمكنني أن أوصي بسهم أو أختار استثمارا نيابة عنك.",
        "error": "الرد المتحكم فيه غير متاح مؤقتا. يرجى إعادة صياغة الطلب.",
    },
    "ary": {
        "pedagogie": "N9der nshra7 lik saham, sanadat, indicateurs w lkhatar b tariqa ta3limiya.",
        "formation_elearning": "N9der n3arref lik 3la massarat ta3limiya li kayna.",
        "orientation": "N9der n3awnek tkhtar massar ta3allom kaynasb hadaf dyalk.",
        "cisi": "Lma3loumat mfassla 3la CISI khas-ha catalogue rasmi.",
        "quiz": "N9der n9addem lik quiz ta3limi 3la sou9 w l2adawat lmaliya.",
        "championnat": "N9der nshra7 lik Championnat dyal lBorsa w e-Bourse b tariqa ta3limiya.",
        "support_ecole": "N9der n3awnek f lwolouj, tsjil w navigation dyal lEcole de la Bourse.",
        "out_of_domain": "Ana mokhtass f lBorsa, l2aswa9 w ta3lim mali.",
        "fallback": "Ma fhemtch talab. N9der n3awnek f lBorsa w ta3lim mali.",
        "blocked": "Ma n9derch n3ayen lik saham wla nakhtar lik investissement.",
        "error": "Jawab m7kom bih ma mtabarsh daba. 3awed siyaghat talab.",
    },
}


DARIJA_ARABIC_MESSAGES = {
    "pedagogie": "نقدر نشرح ليك ببساطة شنو هما الأسهم والسندات والمؤشرات والمخاطر.",
    "formation_elearning": "نقدر نعرفك على المسارات التعليمية اللي كاينة.",
    "orientation": "نقدر نعاونك تختار مسار تعلم مناسب للهدف ديالك.",
    "cisi": "المعلومات المفصلة على CISI خاصها الكاتالوغ الرسمي.",
    "quiz": "نقدر ندير ليك كويز تعليمي على السوق والأدوات المالية.",
    "championnat": "نقدر نشرح ليك بطولة البورصة و e-Bourse بطريقة بسيطة.",
    "support_ecole": "نقدر نعاونك فالولوج والتسجيل والتنقل فمدرسة البورصة.",
    "out_of_domain": "أنا مختص فالبورصة والأسواق والتثقيف المالي.",
    "fallback": "ما فهمتش الطلب. نقدر نعاونك فالبورصة والتثقيف المالي.",
    "blocked": "ما نقدرش نعيّن ليك سهم ولا نختار ليك استثمار.",
    "error": "الجواب المتحكّم فيه ما متوفرش دابا. عاود صيغ الطلب.",
}


def localize_answer(
    business_answer: str,
    language: BusinessLanguage,
    script: BusinessScript,
    *,
    route: str = "fallback",
    response_key: str | None = None,
    blocked: bool = False,
    error: bool = False,
) -> str:
    if route == "quiz" and response_key == "quiz" and business_answer.strip() and not blocked and not error:
        return business_answer
    key = "error" if error else "blocked" if blocked else route
    if key == "out_of_domain":
        return OUT_OF_DOMAIN_MESSAGES[(language, script)]
    answer = MESSAGES[language].get(key, MESSAGES[language]["fallback"])
    static_response = response_key == route and route in MESSAGES[language]
    if (
        static_response
        and not blocked
        and not error
        and route != "fallback"
    ):
        answer = business_answer if language == "fr" else MESSAGES[language][route]
    elif (
        business_answer.strip()
        and not blocked
        and not error
        and route not in {"out_of_domain", "fallback"}
    ):
        answer = business_answer
    if language == "ary" and script == "arabic":
        # Keep the Darija business wording in Arabic script for this boundary.
        if static_response and not blocked and not error and route != "fallback":
            known_translation = DARIJA_ARABIC_MESSAGES.get(route)
            if known_translation:
                return known_translation
        if business_answer.strip() and not blocked and not error and route != "fallback":
            return business_answer
        return DARIJA_ARABIC_MESSAGES.get(key, "ما فهمتش الطلب.")
    return answer


def validate_localized_script(
    text: str, language: BusinessLanguage, script: BusinessScript
) -> bool:
    technical_language = {
        "fr": "fr",
        "en": "en",
        "ar": "ar",
        "ary": "ary-latin" if script == "latin" else "ary-arabic",
    }[language]
    if not validate_script(text, technical_language).valid:
        return False
    latin_count, arabic_count = count_scripts(text)
    if script == "latin":
        return arabic_count <= max(2, int(latin_count * 0.20))
    return arabic_count >= max(3, int(latin_count * 0.50))
