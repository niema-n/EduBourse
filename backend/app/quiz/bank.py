"""Stable curated question bank with explicitly authored localized rendering.

The canonical rows below carry the French question, its four options, the
canonical correct letter and the French explanation. Every non-French locale is
read verbatim from :mod:`app.quiz.localized_content`, which stores hand-written
content for each question. No localized prompt, option or explanation is ever
derived at runtime from a topic name, a level or a question index.
"""

# ruff: noqa: E501

from app.quiz.localized_content import (
    LOCALIZED_CONTENT,
    NON_FRENCH_LOCALES,
    localized_entry,
)
from app.quiz.models import QuizQuestion


def _options(a, b, c, d):
    return {"A": a, "B": b, "C": c, "D": d}


def _repair_row_text(value):
    """Recover legacy UTF-8 text in a canonical row that was decoded as Latin-1."""
    markers = (chr(0x00C3), chr(0x00C2), chr(0x00D8), chr(0x00D9), chr(0xFFFD))
    if not any(marker in value for marker in markers):
        return value
    try:
        repaired = value.encode("latin-1").decode("utf-8")
    except UnicodeError:
        return value
    return repaired if sum(value.count(marker) for marker in markers) > sum(repaired.count(marker) for marker in markers) else value


def _question(qid, topic, level, fr, en, ar, ary, options, correct, explanation):
    """Assemble one question from its French row and its authored localizations.

    The ``en``/``ar``/``ary`` row fields are legacy prompt drafts and are
    deliberately unused: every non-French representation comes from the
    explicit content mapping so that nothing is templated at runtime.
    """
    localized_prompts = {"fr/latin": _repair_row_text(fr)}
    localized_options = {"fr/latin": options}
    localized_explanations = {"fr/latin": _repair_row_text(explanation)}
    for language, script in NON_FRENCH_LOCALES:
        entry = localized_entry(qid, language, script)
        locale_key = f"{language}/{script}"
        localized_prompts[locale_key] = entry["prompt"]
        localized_options[locale_key] = dict(entry["options"])
        localized_explanations[locale_key] = entry["explanation"]
    return QuizQuestion(
        question_id=qid,
        topic=topic,
        level=level,
        prompt=_repair_row_text(fr),
        options=options,
        correct_option=correct,
        explanation=_repair_row_text(explanation),
        localized_prompts=localized_prompts,
        localized_options=localized_options,
        localized_explanations=localized_explanations,
    )


_DIAGNOSTIC_ROWS = [
    (
        "diag-1",
        "stock_exchange",
        "beginner",
        "Quel est le rôle principal d'une Bourse ?",
        "What is the main role of a stock exchange?",
        "ما هو الدور الرئيسي للبورصة؟",
        "Chno الدور الرئيسي ديال البورصة؟",
        _options(
            "Organiser les échanges de titres",
            "Garantir un bénéfice",
            "Accorder des prêts",
            "Fixer les salaires",
        ),
        "A",
        "La Bourse organise les échanges de titres dans un cadre réglementé.",
    ),
    (
        "diag-2",
        "stocks_bonds",
        "beginner",
        "Que représente principalement une action ?",
        "What does a stock mainly represent?",
        "ماذا يمثل السهم أساسا؟",
        "Ach kaymattel saham l3adi?",
        _options(
            "Une dette à court terme",
            "Une fraction du capital d'une société",
            "Une garantie de rendement",
            "Une assurance",
        ),
        "B",
        "Une action représente une fraction du capital d'une société.",
    ),
    (
        "diag-3",
        "risk_return",
        "intermediate",
        "Quelle relation décrit le mieux risque et rendement attendu ?",
        "Which statement best describes risk and expected return?",
        "ما العلاقة بين المخاطر والعائد المتوقع؟",
        "Kifach kayrtabto lkhatar w rbe7 lmontadar?",
        _options(
            "Un rendement attendu plus élevé peut impliquer plus de risque",
            "Le risque disparaît toujours",
            "Le rendement est garanti",
            "Ils sont toujours indépendants",
        ),
        "A",
        "Un rendement attendu plus élevé peut s'accompagner d'une incertitude plus forte.",
    ),
    (
        "diag-4",
        "diversification",
        "intermediate",
        "Quel est un objectif de la diversification ?",
        "What is one purpose of diversification?",
        "ما أحد أهداف التنويع؟",
        "Ashno wa7ed men ahdaf tanwi3?",
        _options(
            "Réduire certains risques en répartissant l'exposition",
            "Supprimer tout risque",
            "Garantir le meilleur titre",
            "Éviter toute information",
        ),
        "A",
        "La diversification peut réduire certains risques, sans les supprimer.",
    ),
    (
        "diag-5",
        "primary_secondary_markets",
        "intermediate",
        "Sur quel marché une entreprise émet-elle de nouveaux titres ?",
        "On which market does a company issue new securities?",
        "في أي سوق تصدر الشركة أوراقا مالية جديدة؟",
        "Fach sou9 katssder cherka wra9 maliya jdida?",
        _options(
            "Le marché secondaire",
            "Le marché de l'assurance",
            "Le marché primaire",
            "Le marché immobilier",
        ),
        "C",
        "Le marché primaire concerne l'émission de nouveaux titres.",
    ),
    (
        "diag-6",
        "ipo_disclosure",
        "advanced",
        "À quoi sert un document d'information lors d'une introduction en Bourse ?",
        "What is the purpose of an IPO information document?",
        "ما فائدة وثيقة المعلومات عند الإدراج في البورصة؟",
        "Ach katdir wti9at lma3loumat f IPO?",
        _options(
            "Garantir une plus-value",
            "Promettre le cours futur",
            "Remplacer la réglementation",
            "Présenter les informations utiles à l'évaluation",
        ),
        "D",
        "Le document informe sur l'opération sans garantir sa performance.",
    ),
]


_NORMAL_ROWS = {
    "beginner": [
        (
            "stock",
            "Que représente une action ordinaire ?",
            "What does an ordinary stock represent?",
            "ماذا يمثل السهم العادي؟",
            "Ach kaymattel saham l3adi?",
            _options(
                "Une facture",
                "Une part du capital de la société",
                "Une dette bancaire",
                "Une garantie",
            ),
            "B",
            "Une action est liée à une part du capital de la société.",
        ),
        (
            "bond",
            "Que représente généralement une obligation ?",
            "What does a bond generally represent?",
            "ماذا تمثل السندات عادة؟",
            "Ach katmattel lsanadat?",
            _options("Une créance sur l'émetteur", "Une action", "Un dividende", "Un indice"),
            "A",
            "Une obligation représente généralement une créance sur son émetteur.",
        ),
        (
            "dividend",
            "Qu'est-ce qu'un dividende ?",
            "What is a dividend?",
            "ما هو التوزيع النقدي للمساهم؟",
            "Ach howa dividende?",
            _options(
                "Une taxe", "Un ordre", "Une distribution éventuelle aux actionnaires", "Un indice"
            ),
            "C",
            "Un dividende est une distribution éventuelle aux actionnaires.",
        ),
        (
            "index",
            "Que suit un indice boursier ?",
            "What does a stock index track?",
            "ماذا يتابع المؤشر؟",
            "Ach kaytbe3 lmo2achir?",
            _options(
                "Une seule dette",
                "Les salaires",
                "Un taux garanti",
                "L'évolution d'un ensemble de valeurs",
            ),
            "D",
            "Un indice suit l'évolution d'un ensemble de valeurs.",
        ),
        (
            "investor",
            "Que doit considérer un investisseur avant une décision ?",
            "What should an investor consider before a decision?",
            "ما الذي ينبغي للمستثمر مراعاته؟",
            "Ach khas lmostatmir ychof?",
            _options(
                "Uniquement la publicité",
                "Objectifs, informations et risques",
                "Un rendement garanti",
                "Aucun élément",
            ),
            "B",
            "Une décision doit tenir compte des objectifs, des informations et des risques.",
        ),
        (
            "risk",
            "Que signifie le risque financier ?",
            "What does financial risk mean?",
            "ماذا يعني الخطر المالي؟",
            "Ach kay3ni lkhatar lmali?",
            _options(
                "Une garantie",
                "Un prix fixe",
                "Un résultat qui peut différer de l'attendu",
                "Une obligation légale",
            ),
            "C",
            "Le résultat réel peut différer du résultat attendu.",
        ),
        (
            "return",
            "Que mesure le rendement ?",
            "What does return measure?",
            "ماذا يقيس العائد؟",
            "Ach kay9iss rbe7?",
            _options(
                "Le résultat d'un placement sur une période",
                "Le nombre d'actions",
                "Le règlement",
                "La liquidité uniquement",
            ),
            "A",
            "Le rendement mesure le résultat d'un placement sur une période.",
        ),
        (
            "diversification",
            "À quoi sert une diversification de base ?",
            "What is a basic purpose of diversification?",
            "ما فائدة التنويع الأساسي؟",
            "3lach kan7tajou tanwi3?",
            _options(
                "Garantir un titre",
                "Éviter les règles",
                "Supprimer toute perte",
                "Répartir l'exposition entre plusieurs actifs",
            ),
            "D",
            "La diversification répartit l'exposition entre plusieurs actifs.",
        ),
        (
            "market_rules",
            "Pourquoi les règles de marché sont-elles utiles ?",
            "Why are market rules useful?",
            "لماذا قواعد السوق مهمة؟",
            "3lach qawa3ed sou9 mohimma?",
            _options(
                "Pour supprimer le risque",
                "Pour favoriser un marché ordonné et transparent",
                "Pour garantir les prix",
                "Pour remplacer l'information",
            ),
            "B",
            "Les règles favorisent un fonctionnement ordonné et transparent.",
        ),
        (
            "primary_intro",
            "Que signifie l'émission de nouveaux titres ?",
            "What does issuing new securities mean?",
            "ماذا يعني إصدار أوراق مالية جديدة؟",
            "Ach kay3ni isdar wra9 maliya jdida?",
            _options(
                "Une revente entre investisseurs",
                "Une assurance",
                "Une offre initiale par l'émetteur",
                "Un dividende",
            ),
            "C",
            "Les nouveaux titres sont proposés par leur émetteur sur le marché primaire.",
        ),
    ],
    "intermediate": [
        (
            "stock_bond_context",
            "Pourquoi une action et une obligation ne donnent-elles pas le même droit ?",
            "Why do a stock and a bond give different rights?",
            "لماذا يختلف حق حامل السهم عن حامل السند؟",
            "3lach saham w sanad ma kay3tiwch nafs l7e9?",
            _options(
                "L'une est liée au capital, l'autre à une créance",
                "Elles sont identiques",
                "Les deux garantissent un gain",
                "Aucune n'a d'émetteur",
            ),
            "A",
            "L'action est liée au capital, tandis que l'obligation est une créance.",
        ),
        (
            "opcvm",
            "Quel est le principe général d'un OPCVM ?",
            "What is the general principle of a collective fund?",
            "ما المبدأ العام لصندوق استثمار جماعي؟",
            "Ach howa lmobda2 dyal OPCVM?",
            _options(
                "Un titre sans règles",
                "Une garantie de rendement",
                "Un prêt personnel",
                "Des capitaux gérés collectivement selon des règles",
            ),
            "D",
            "Un OPCVM rassemble des capitaux gérés collectivement selon des règles définies.",
        ),
        (
            "diversification_application",
            "Quelle limite faut-il rappeler à la diversification ?",
            "What limitation of diversification should be remembered?",
            "ما حدود التنويع؟",
            "Ashno l7ed dyal tanwi3?",
            _options(
                "Elle garantit le gain",
                "Elle ne supprime pas tous les risques",
                "Elle interdit toute perte",
                "Elle remplace l'analyse",
            ),
            "B",
            "La diversification peut réduire certains risques, mais ne les supprime pas.",
        ),
        (
            "limit_order",
            "Que fixe un ordre à cours limité ?",
            "What does a limit order set?",
            "ماذا يحدد الأمر المحدد السعر؟",
            "Ach kay7edded l2amr b taman mahded?",
            _options(
                "Un dividende",
                "Un indice",
                "Une limite de prix d'exécution",
                "Une échéance fiscale",
            ),
            "C",
            "L'ordre à cours limité fixe une limite de prix pour l'exécution.",
        ),
        (
            "secondary_market",
            "Que se passe-t-il sur le marché secondaire ?",
            "What happens in the secondary market?",
            "ماذا يحدث في السوق الثانوية؟",
            "Ach kaytra f sou9 t-tani?",
            _options(
                "Des titres déjà émis sont échangés",
                "Une société crée toujours des titres",
                "Des salaires sont fixés",
                "Des prêts sont garantis",
            ),
            "A",
            "Le marché secondaire permet l'échange de titres déjà émis.",
        ),
        (
            "ipo",
            "Que caractérise une introduction en Bourse ?",
            "What characterizes an IPO?",
            "ما الذي يميز الإدراج الأولي؟",
            "Ach kaymiyyez l idraj l2awali?",
            _options(
                "Une assurance",
                "Un dividende",
                "Une revente privée",
                "L'admission initiale des titres sur un marché",
            ),
            "D",
            "L'IPO correspond à l'admission initiale des titres d'une société.",
        ),
        (
            "horizon",
            "Pourquoi l'horizon de placement est-il pertinent ?",
            "Why is investment horizon relevant educationally?",
            "لماذا أفق الاستثمار مهم تعليميا؟",
            "3lach lmodda mohimma ta3limiyan?",
            _options(
                "Il garantit un rendement",
                "Il met fluctuations et objectifs en contexte",
                "Il supprime les risques",
                "Il fixe le cours",
            ),
            "B",
            "L'horizon aide à mettre les fluctuations et objectifs en contexte.",
        ),
        (
            "participants",
            "Quel est le rôle d'un intermédiaire agréé ?",
            "What can an authorized intermediary do?",
            "ما دور الوسيط المرخص؟",
            "Ach kaydir lwasit lm3tamed?",
            _options(
                "Garantir une plus-value",
                "Modifier les lois",
                "Faciliter certaines opérations selon les règles",
                "Supprimer le marché",
            ),
            "C",
            "Il facilite certaines opérations dans le cadre des règles applicables.",
        ),
        (
            "volatility",
            "Que décrit la volatilité ?",
            "What does volatility describe?",
            "ماذا تصف التقلبات؟",
            "Ach katwassaf tta9allobat?",
            _options(
                "L'ampleur des variations de prix",
                "Le capital garanti",
                "Les dividendes futurs",
                "La durée d'une IPO",
            ),
            "A",
            "La volatilité décrit l'ampleur et la fréquence des variations de prix.",
        ),
        (
            "risk_return_application",
            "Un rendement passé garantit-il le rendement futur ?",
            "Does past return guarantee future return?",
            "هل يضمن العائد السابق العائد المستقبلي؟",
            "Wach rbe7 li فات kaydmen rbe7 jdid?",
            _options(
                "Oui toujours",
                "Seulement pour une action",
                "Seulement avec un indice",
                "Non, les performances passées ne garantissent pas les futures",
            ),
            "D",
            "Les performances passées ne garantissent pas les performances futures.",
        ),
    ],
    "advanced": [
        (
            "corporate_action",
            "Quel peut être l'effet d'une augmentation de capital ?",
            "What can be an effect of a capital increase?",
            "ما أثر زيادة رأس المال؟",
            "Ashno y9der ykoun ta2tir zyada f rass lmal?",
            _options(
                "Elle peut modifier capital et droits relatifs",
                "Elle supprime l'émetteur",
                "Elle garantit le cours",
                "Elle interdit l'information",
            ),
            "A",
            "Une augmentation de capital peut modifier le capital et les droits associés.",
        ),
        (
            "ipo_mechanism",
            "Pourquoi la fixation du prix est-elle importante lors d'une IPO ?",
            "Why is price setting important in an IPO?",
            "لماذا تحديد السعر مهم عند الإدراج؟",
            "3lach t7did taman mohim f IPO?",
            _options(
                "Elle garantit le rendement",
                "Elle remplace la loi",
                "Elle met en relation offre, demande et information",
                "Elle supprime le risque",
            ),
            "C",
            "Le prix met en relation l'offre, la demande et l'information disponible.",
        ),
        (
            "disclosure",
            "À quoi sert l'information périodique d'un émetteur ?",
            "What is periodic issuer disclosure for?",
            "ما فائدة المعلومات الدورية عن المصدر؟",
            "3lach lma3loumat d-dawriya mohimma?",
            _options(
                "Suivre situation et risques de l'émetteur",
                "Garantir un bénéfice",
                "Fixer tous les cours",
                "Remplacer l'audit",
            ),
            "A",
            "Elle aide à suivre la situation et les risques de l'émetteur.",
        ),
        (
            "market_structure",
            "Que recouvre la structure d'un marché ?",
            "What does market structure include?",
            "ماذا تشمل بنية السوق؟",
            "Ash kat3ni bina2 sou9?",
            _options(
                "Les salaires",
                "Les dividendes garantis",
                "Les bénéfices futurs",
                "Les règles d'accès, de négociation et de transparence",
            ),
            "D",
            "La structure comprend notamment les règles d'accès, de négociation et de transparence.",
        ),
        (
            "liquidity_risk",
            "Que signifie un risque de liquidité ?",
            "What does liquidity risk mean?",
            "ماذا يعني خطر السيولة؟",
            "Ach kay3ni khatar siyoula?",
            _options(
                "Un rendement garanti",
                "La difficulté possible de vendre rapidement sans impact important",
                "Une IPO",
                "Un dividende",
            ),
            "B",
            "Le risque de liquidité est la difficulté possible de vendre rapidement sans impact important.",
        ),
        (
            "opcvm_value",
            "À quoi sert la valeur liquidative d'un fonds ?",
            "What is a fund net asset value used for?",
            "فيم تستخدم قيمة صافي أصول الصندوق؟",
            "Fach katsta3mel l9ima s-safiya dyal sandou9?",
            _options(
                "À fixer les salaires",
                "À garantir un rendement",
                "À évaluer une part selon les actifs et règles",
                "À supprimer la volatilité",
            ),
            "C",
            "La valeur liquidative sert à évaluer une part selon les actifs et règles du fonds.",
        ),
        (
            "market_order",
            "Quel compromis présente un ordre au marché ?",
            "What trade-off does a market order present?",
            "ما المقايضة في الأمر بسعر السوق؟",
            "Ashno lmo3adala f amr sou9?",
            _options(
                "Il privilégie l'exécution sans garantir le prix exact",
                "Il garantit le prix",
                "Il crée une société",
                "Il interdit la vente",
            ),
            "A",
            "L'ordre au marché privilégie l'exécution sans garantir le prix exact.",
        ),
        (
            "participant_roles",
            "Pourquoi séparer les rôles des participants ?",
            "Why separate participant roles?",
            "لماذا فصل أدوار المشاركين؟",
            "3lach kanfsslo adwar lmocharikin?",
            _options(
                "Pour garantir un gain",
                "Pour supprimer les règles",
                "Pour fixer tous les prix",
                "Pour clarifier les responsabilités et limiter certains conflits",
            ),
            "D",
            "La séparation clarifie les responsabilités et peut limiter certains conflits.",
        ),
        (
            "financial_analysis",
            "Sur quoi repose une analyse financière prudente ?",
            "What does a careful financial analysis rely on?",
            "على ماذا يعتمد التحليل المالي الحذر؟",
            "3la ach katbna l'analyse lmaliya?",
            _options(
                "Sur une publicité",
                "Sur des informations pertinentes et leurs limites",
                "Sur une promesse",
                "Sur un seul cours",
            ),
            "B",
            "Elle repose sur des informations pertinentes, vérifiables et leurs limites.",
        ),
        (
            "securities_operation",
            "Une information réglementaire garantit-elle une performance ?",
            "Does regulatory information guarantee performance?",
            "هل تضمن المعلومات التنظيمية الأداء؟",
            "Wach lma3louma tanzimiya katdmen l2ada2?",
            _options(
                "Oui toujours",
                "Oui pour une IPO",
                "Non, elle informe sans promettre un rendement",
                "Seulement pour les obligations",
            ),
            "C",
            "L'information réglementaire informe, mais ne garantit pas une performance future.",
        ),
    ],
}


def _from_row(row, level, index):
    topic, fr, en, ar, ary, options, correct, explanation = row
    return _question(
        f"{level}-{index + 1}", topic, level, fr, en, ar, ary, options, correct, explanation
    )


DIAGNOSTIC_BANK = [_question(*row) for row in _DIAGNOSTIC_ROWS]
NORMAL_BANK = {
    level: [_from_row(row, level, index) for index, row in enumerate(rows)]
    for level, rows in _NORMAL_ROWS.items()
}

CANONICAL_QUESTION_IDS = tuple(
    [question.question_id for question in DIAGNOSTIC_BANK]
    + [question.question_id for bank in NORMAL_BANK.values() for question in bank]
)

# Every canonical question must have an explicitly authored row per non-French
# locale; a missing entry is a packaging error and must fail at import time.
_missing = [
    (question_id, locale)
    for question_id in CANONICAL_QUESTION_IDS
    for locale in NON_FRENCH_LOCALES
    if locale not in LOCALIZED_CONTENT.get(question_id, {})
]
if _missing:  # pragma: no cover - guarded by the unit tests
    raise RuntimeError(f"missing authored quiz localizations: {_missing}")


def normal_bank(level: str, count: int = 10) -> list[QuizQuestion]:
    """Return the approved level bank, with an explicit bounded count."""
    if level not in NORMAL_BANK:
        raise ValueError(f"unsupported learning level: {level}")
    if not 1 <= count <= len(NORMAL_BANK[level]):
        raise ValueError("quiz count must be between 1 and 10")
    return NORMAL_BANK[level][:count]
