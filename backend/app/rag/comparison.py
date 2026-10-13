"""Bounded multilingual comparison coverage; vocabulary is never answer evidence.

Only retrieved body text can satisfy a concept. Titles, contents-page entries,
conversation history and the query expansion vocabulary cannot establish facts.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


def fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).casefold()
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.replace("ـ", "").replace("ى", "ي")


def arabic(words: str) -> str:
    return rf"(?<![ا-ي])(?:[وفبلك]{{0,2}})?(?:ال)?(?:{words})(?![ا-ي])"


@dataclass(frozen=True)
class Concept:
    key: str
    aliases: str
    labels: tuple[str, str, str]
    definition: str

    def __post_init__(self):
        object.__setattr__(self, "aliases", fold(self.aliases))
        object.__setattr__(self, "definition", fold(self.definition))


# Search aliases and definitional vocabulary, not templates for factual answers.
CONCEPTS = (
    Concept(
        "stock",
        r"\b(?:actions?|stocks?|shares?|equity)\b|" + arabic("سهم|اسهم"),
        ("action", "stock / equity", "السهم"),
        r"propriet|ownership|part.{0,45}capital|share.{0,35}company|ملكي|حص[ةه].{0,30}راس مال",
    ),
    Concept(
        "bond",
        r"\b(?:obligations?|bonds?)\b|" + arabic("سند|سندات"),
        ("obligation", "bond", "السند"),
        r"creance|\bdette\b|\bpret\b|emprunt|\bdebt\b|\bloan\b|دين|قرض",
    ),
    Concept(
        "fund",
        r"\b(?:opcvm|ucits|mutual funds?|fonds(?: de placement)?|sicav|fcp)\b|"
        + arabic("صندوق|صناديق")
        + r"|هيئات التوظيف الجماعي",
        ("OPCVM", "mutual fund / UCITS", "صناديق الاستثمار"),
        r"collecti|pool|gestion|portefeuille|portfolio|جماع|محفظ|تدبير|ادار",
    ),
    Concept(
        "direct",
        r"\b(?:investissement direct|direct investment|direct investing)\b|"
        r"استثمار.{0,8}مباشر",
        ("investissement direct", "direct investment", "الاستثمار المباشر"),
        r"direct|deten|achet|ger|hold|own|manage|مباشر|شراء|بنفس|راس",
    ),
    Concept(
        "ipo",
        r"\bipo\b|introduction(?:s)? en bourse|initial public offering|"
        r"اكتتاب.{0,12}(?:اول|عام)|ادراج.{0,12}(?:اول|بورص)",
        ("introduction en bourse IPO", "IPO", "الاكتتاب العام الاولي"),
        r"public|capital|offering|premier|first|جمهور|راس مال|اول|طرح",
    ),
    Concept(
        "secondary",
        r"marche secondaire|secondary market|السوق الثانوي[ةه]?",
        ("marché secondaire", "secondary market", "السوق الثانوية"),
        r"echang|negoci|deja emis|existing|trad|resal|تداول|تبادل|بيع|سبق",
    ),
    Concept(
        "primary",
        r"marche primaire|primary market|السوق الاولي[ةه]?",
        ("marché primaire", "primary market", "السوق الاولية"),
        r"emission|nouve|issu|new|اصدار|جديد|طرح",
    ),
    Concept(
        "etf",
        r"\betfs?\b|exchange.traded funds?|fonds cotes?|صناديق.{0,12}متداول",
        ("ETF", "ETF", "صناديق المؤشرات المتداولة"),
        r"indice|index|track|cot|exchange|مؤشر|موشر|تتبع|متداول",
    ),
)

COMPARISON = re.compile(
    r"\b(?:compar\w*|difference\w*|differ\w*|versus|vs|far9|fer9|lfer9|lfar9)\b|فرق|مقارن"
)
DIMENSIONS = {
    "return": (
        r"rendement|remuneration|return|dividend|coupon|interest|interet|"
        r"عايد|ارباح|كوبون|فوايد|ربح"
    ),
    "risk": r"risqu|risk|volatil|default|liquidit|perte|loss|مخاطر|خطر|خسار|سيول|تقلب|عجز|تعثر",
    "rights": r"droit|rights?|obligation|vote|voting|repay|rembours|حق|حقوق|تصويت|سداد|التزام",
}
FEATURES = {
    "dividend": ("return", r"dividend|ارباح|رباح"),
    "interest": ("return", r"coupon|interet|interest|كوبون|فوايد|فايد[ةه]"),
    "capital_gain": ("return", r"plus.value|capital gain|ربح.{0,25}(?:بيع|راسمال)|تغير.{0,20}قيم"),
    "capital_loss": ("risk", r"perte|loss|خسار"),
    "volatility": ("risk", r"volatil|fluctuat|تقلب"),
    "liquidity": ("risk", r"liquidit|سيول"),
    "default": ("risk", r"defaut|default|credit risk|risque de credit|عجز|تعثر"),
    "voting": ("rights", r"vote|voting|تصويت"),
    # Darija conjugates the root (كيتسدد/يسدد) beside the nominal forms.
    "repayment": ("rights", r"rembours|repay|سداد|تسديد|سدد"),
    # A right to information, not any "document d'information" in the corpus.
    "information": (
        "rights",
        r"droits?.{0,30}information|information.{0,40}(?:actionnaire|porteur)|"
        r"حق.{0,30}معلومات|الحصول على.{0,25}معلومات|الاطلاع على",
    ),
}
SOURCE_MECHANICS = re.compile(
    fold(
        r"(?:sources?|documents?|extraits?).{0,55}(?:ne .{0,15}(?:defini|precis|mention|detail)|"
        r"does not|do not|doesn't|don't|not (?:defin|specif|mention)|insuffis|insufficient)|"
        r"selon (?:les|la|le) (?:extraits|sources?|documents?)|extraits recuperes|"
        r"according to (?:the )?(?:sources?|documents?|excerpts?)|"
        r"retrieved (?:evidence|context|passages)|"
        r"(?:حسب|علي حساب|بناء علي)\s*(?:المصدر(?![ةه])|المصادر|الوثائق|المقاطع|"
        r"المعلومات المتوفر[ةه])|"
        r"(?:المصدر(?![ةه])|المصادر|الوثيق[ةه]|الوثائق|المقاطع|النصوص)"
        r"(?:\s+[^\s]+){0,2}\s*(?:ما|لا|لم)\s*(?:كي|كت|ي|ت)?"
        r"(?:ذكر|حدد|قول|قال|وضح|بين|نص|قدم|شير|تضمن|فيها)|"
        r"(?:ما|لا|لم)\s*(?:كي|كت|ي|ت)?(?:ذكر|حدد|قول|وضح|بين|قدم|شير)"
        r"(?:\s+[^\s]+){0,1}\s*(?:المصدر(?![ةه])|المصادر|الوثائق|المقاطع)|"
        r"ما لقيتش فالمصدر|بناء.{0,8}علي الوثائق"
    )
)


# "avoir l'obligation de ..." is a legal duty of the issuer, never the debt instrument.
DUTY_SENSE = re.compile(
    fold(r"(?:a|as|ont|avoir|avez|avons|avais|aura|ayant)\s+l['’]\s*obligation")
)
# Only a debt instrument owns a creditor's mechanics; elsewhere a creditor clause is context.
CREDITOR_CONTEXT = re.compile(fold(r"creanci|creditor|دائن|obligataire"))
DEBT_CONCEPTS = frozenset({"bond"})
# Mechanisms belong to one instrument and may never be borrowed from the other. Risk facets
# (loss, volatility, liquidity, default) stay governed by the risk dimension itself, which
# still requires cited evidence for that concept.
MECHANISM_FEATURES = frozenset({"dividend", "interest", "capital_gain", "voting", "repayment"})
CLAUSE_BOUNDARY = re.compile(
    fold(r"\.|;|:|،|؛|\n|\bapres\b|\bafter\b|\bonce\b|من بعد|بعد ما|بعد ")
)


def _instrument_mention(value: str, concept: Concept, match: re.Match, etf_spans) -> bool:
    if concept.key == "bond" and DUTY_SENSE.search(value[max(0, match.start() - 24) : match.end()]):
        return False
    # Ignore only fund mentions within an ETF name, not a separate fund.
    if concept.key == "fund" and any(
        start <= match.start() and match.end() <= end for start, end in etf_spans
    ):
        return False
    return True


def _mentions(value: str) -> list[tuple[int, int, str]]:
    etf_spans = [m.span() for m in re.finditer(CONCEPTS[-1].aliases, value)]
    found = []
    for concept in CONCEPTS:
        for match in re.finditer(concept.aliases, value):
            if _instrument_mention(value, concept, match, etf_spans):
                found.append((match.start(), match.end(), concept.key))
    return sorted(found)


def attribution_clauses(passage: str, concept: Concept) -> list[str]:
    """A feature is claimed for a concept only by a clause that predicates it of it."""
    clauses = [clause for clause in CLAUSE_BOUNDARY.split(passage) if clause.strip()]
    if concept.key in DEBT_CONCEPTS:
        return clauses
    return [clause for clause in clauses if not CREDITOR_CONTEXT.search(clause)]


def features_in(text: str, concept: Concept) -> set[str]:
    found: set[str] = set()
    for passage in concept_passages(text, concept):
        for clause in attribution_clauses(passage, concept):
            for name, (_dimension, pattern) in FEATURES.items():
                if re.search(pattern, clause):
                    found.add(name)
    return found


def concepts_in(text: str) -> tuple[Concept, ...]:
    value = fold(text)
    by_key = {concept.key: concept for concept in CONCEPTS}
    first: dict[str, int] = {}
    for start, _end, key in _mentions(value):
        first.setdefault(key, start)
    return tuple(by_key[key] for key, _ in sorted(first.items(), key=lambda item: item[1]))


def comparison_concepts(query: str) -> tuple[Concept, ...]:
    concepts = concepts_in(query)
    return concepts if len(concepts) >= 2 and COMPARISON.search(fold(query)) else ()


def has_source_mechanics(text: str) -> bool:
    return bool(SOURCE_MECHANICS.search(fold(text)))


def concept_passages(text: str, concept: Concept) -> list[str]:
    # Contents-page lines and isolated numbered headings are not substantive text.
    if re.search(r"table\s+des\s+matieres|table\s+of\s+contents|sommaire|فهرس", fold(text)):
        return []
    lines = [
        line
        for line in fold(text).splitlines()
        if not re.search(r"\.{3,}|(?:sommaire|table of contents|فهرس)", line)
    ]
    text = "\n".join(lines)
    mentions = _mentions(text)
    passages = []
    for index, (start, end, key) in enumerate(mentions):
        if key != concept.key:
            continue
        stop = next((p for p, _, other in mentions[index + 1 :] if other != key), len(text))
        if stop < len(text):
            separator = max(
                text.rfind("\n", end, stop),
                text.rfind(";", end, stop),
                text.rfind("،", end, stop),
                text.rfind(".", end, stop),
            )
            if separator >= end:
                stop = separator + 1
        # Include the predicate immediately before a postposed subject ("coupon للسند").
        boundary = (
            max(
                text.rfind("\n", 0, start),
                text.rfind(";", 0, start),
                text.rfind("،", 0, start),
                text.rfind(".", 0, start),
            )
            + 1
        )
        previous = mentions[index - 1][1] if index else 0
        passage = text[max(boundary, previous) : stop]
        if len(re.findall(r"\w+", passage)) >= 2 and not has_source_mechanics(passage):
            passages.append(passage)
    return passages


def coverage(text: str, concept: Concept) -> set[str]:
    covered: set[str] = set()
    for passage in concept_passages(text, concept):
        if len(re.findall(r"\w+", passage)) >= 3 and re.search(concept.definition, passage):
            covered.add("definition")
    for feature in features_in(text, concept):
        covered.add(FEATURES[feature][0])
    return covered


def evidence_coverage(chunks, concept: Concept) -> set[str]:
    return set().union(*(coverage(chunk.text, concept) for chunk in chunks))


def required_dimensions(query: str) -> set[str]:
    value = fold(query)
    # "obligation" is also an instrument, not a request for obligations/rights.
    return {"definition"} | {
        name
        for name, pattern in DIMENSIONS.items()
        if re.search(pattern.replace("|obligation", ""), value)
    }


# Pedagogical enrichment target for a comparison: retrieved when the corpus has it,
# never required of the answer. Only required_dimensions(query) can fail a comparison.
COMPARISON_DIMENSIONS = ("definition", "return", "risk", "rights")
DIMENSION_LABELS = {
    "ar": {
        "definition": "التعريف والطبيعة",
        "return": "العائد",
        "risk": "المخاطر",
        "rights": "الحقوق والالتزامات",
    },
    "en": {
        "definition": "definition and nature",
        "return": "return",
        "risk": "risks",
        "rights": "rights and obligations",
    },
    "fr": {
        "definition": "définition et nature",
        "return": "rendement",
        "risk": "risques",
        "rights": "droits et obligations",
    },
}


def desired_dimensions(query: str) -> set[str]:
    return set(COMPARISON_DIMENSIONS) | required_dimensions(query)


def targeted_query(
    concept: Concept,
    language: str,
    script: str,
    dimensions: set[str] | None = None,
) -> str:
    wanted = [name for name in COMPARISON_DIMENSIONS if not dimensions or name in dimensions]
    wanted = wanted or list(COMPARISON_DIMENSIONS)
    locale = "ar" if script == "arabic" else "en" if language == "en" else "fr"
    labels = [DIMENSION_LABELS[locale][name] for name in wanted]
    if locale == "ar":
        return f"{concept.labels[2]}: " + " و".join(labels)
    if locale == "en":
        return f"{concept.labels[1]}: " + ", ".join(labels)
    return f"{concept.labels[0]} : " + ", ".join(labels)


COMPARISON_INSTRUCTION = """
COMPARISON COMPLETENESS CONTRACT (takes precedence over partial-answer instructions)
Define EVERY concept listed in COMPARISON_CONCEPTS, then compare them coherently.
Open on the one sentence that states the core distinction, then one short paragraph per
concept, then the supported differences in return, risks and rights, then one short
synthesis. A simple comparison stays around 120-220 words in a few short paragraphs:
prefer flowing prose over a multi-section report, use a list only when the question needs
one, and expand only when the user asked for a detailed treatment. For a comparison this
replaces the general criterion-by-criterion presentation: write connected teaching
paragraphs, with no section headings, no bold labels and no bullet list unless the user
asked for one, so the answer can be read aloud as one explanation.
Only use dimensions actually established by SOURCE CONTEXT.
COMPARISON_SUPPORTED lists, per concept, the dimensions the retrieved evidence establishes:
use only those for that concept, never fill a missing one from general knowledge, and
accept that one concept may legitimately carry fewer dimensions than the other. A dimension
absent for one concept is simply left out, in silence: never state, in any language, what
the sources do, do not or do not explicitly mention, and never comment on their coverage.
Cite, in used_evidence_ids, every evidence block a dimension of your answer comes from: a
dimension whose evidence you do not cite must be left out of the answer.
Never infer a bond's characteristics from stock evidence or vice versa. A heading,
contents entry or mention alone does not define an instrument. Cite substantive evidence
for EACH concept. Do not fill a gap with general knowledge. If a definition cannot be
supported, return insufficient_evidence=true with no evidence IDs and no substantive answer.
Start directly with the concepts, not with the research process. Never write "la source
ne définit pas", "le document ne précise pas", "selon les extraits récupérés",
"حسب المصدر", "المصدر ما كيحددش", "لا يذكر المصدر", "المصادر المتوفرة", "المقاطع المرفقة"
or "الوثائق ما كتذكرش", in Darija or in MSA. Citations are metadata.
In ary/arabic, use natural Moroccan Darija in Arabic script: a professional, concise,
confident financial educator, not dominant MSA, promotional language or a search report.
Vocabulary in the coverage contract is search intent, NOT additional factual evidence.
"""


def limitation(language: str, script: str) -> str:
    return {
        ("fr", "latin"): "Je ne peux pas établir une comparaison fiable de tous ces éléments.",
        ("en", "latin"): "I cannot establish a reliable comparison of all these concepts.",
        ("ar", "arabic"): "لا يمكنني تقديم مقارنة موثوقة تشمل جميع هذه المفاهيم.",
        ("ary", "arabic"): "ما نقدرش نعطيك دابا مقارنة موثوقة وكاملة بين هاد المفاهيم.",
        ("ary", "latin"): "Ma n9derch n3tik daba mo9arana mawto9a w kamla bin had lmafahim.",
    }[(language, script)]


def _numbers(text: str) -> set[str]:
    """Numerical financial claims must be traceable, ignoring list numbering."""
    text = re.sub(r"\[S\d+\]", "", text)
    text = re.sub(r"(?m)^\s*(?:\*\*)?\d+[.)]\s*", "", text)
    return set(re.findall(r"\d+(?:[.,]\d+)?\s*%?", text))


def comparison_gaps(
    answer: str,
    concepts: tuple[Concept, ...],
    chunks,
    *,
    required: set[str] | None = None,
) -> list[str]:
    """Why a comparison is not publishable: bounded reason codes, never answer text."""
    reasons: list[str] = []
    if has_source_mechanics(answer):
        reasons.append("source_mechanics")
    for concept in concepts:
        key = concept.key
        actual = coverage(answer, concept)
        supported = evidence_coverage(chunks, concept)
        if "definition" not in actual:
            reasons.append(f"{key}.definition_missing_from_answer")
        if "definition" not in supported:
            reasons.append(f"{key}.definition_missing_from_cited_evidence")
        reasons.extend(
            f"{key}.{name}_required_but_absent"
            for name in sorted(((required or set()) & supported) - actual)
        )
        # Unsupported return/risk/right dimensions may not be invented to fill a table.
        reasons.extend(
            f"{key}.{name}_claimed_without_cited_evidence" for name in sorted(actual - supported)
        )
        # A mechanism of the other instrument may not be borrowed, but it counts as
        # claimed only where a clause predicates it of this concept.
        claimed = features_in(answer, concept) & MECHANISM_FEATURES
        established = set().union(
            *(features_in(chunk.text, concept) for chunk in chunks), set()
        )
        reasons.extend(
            f"{key}.{name}_mechanism_not_established"
            for name in sorted(claimed - established)
        )
    if not _numbers(answer) <= _numbers("\n".join(c.text for c in chunks)):
        reasons.append("untraceable_numbers")
    return reasons


def answer_covers(
    answer: str,
    concepts: tuple[Concept, ...],
    chunks,
    *,
    required: set[str] | None = None,
) -> bool:
    return not comparison_gaps(answer, concepts, chunks, required=required)


def rewrite_preserves_comparison(source: str, candidate: str) -> bool:
    """Protect an already complete comparison during final localization."""
    from types import SimpleNamespace

    concepts = concepts_in(source)
    if len(concepts) < 2 or any("definition" not in coverage(source, c) for c in concepts):
        return True
    return answer_covers(
        candidate,
        concepts,
        [SimpleNamespace(text=source)],
        required={"definition", "return", "risk", "rights"},
    )
