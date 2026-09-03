"""Prepare versioned, internal-only J3 contract examples.

The phrases here are authored from the product contract and are deliberately
separate from benchmark and audit corpora.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

LANGUAGES = ("fr", "en", "ar", "ary-latin", "ary-arabic")
ROUTES = (
    "pedagogie",
    "formation_elearning",
    "cisi",
    "quiz",
    "championnat",
    "orientation",
    "support_ecole",
    "out_of_domain",
)
VARIANT_SUFFIXES = ("", " simplement", " pour debuter", " avec un exemple")
ROUTE_HINTS = {
    "fr": {
        "pedagogie": "notion educative",
        "formation_elearning": "formation e-learning",
        "cisi": "certification CISI",
        "quiz": "quiz",
        "championnat": "championnat bourse",
        "orientation": "orientation apprentissage",
        "support_ecole": "support ecole",
        "out_of_domain": "hors sujet",
    },
    "en": {
        "pedagogie": "financial education",
        "formation_elearning": "online training",
        "cisi": "CISI certification",
        "quiz": "learning quiz",
        "championnat": "market competition",
        "orientation": "learning guidance",
        "support_ecole": "school support",
        "out_of_domain": "unrelated topic",
    },
    "ar": {
        "pedagogie": "تعليم مالي",
        "formation_elearning": "تكوين الكتروني",
        "cisi": "شهادة CISI",
        "quiz": "اختبار تعليمي",
        "championnat": "بطولة البورصة",
        "orientation": "توجيه للتعلم",
        "support_ecole": "دعم المدرسة",
        "out_of_domain": "موضوع خارج المجال",
    },
    "ary-latin": {
        "pedagogie": "ta3lim mali",
        "formation_elearning": "formation online",
        "cisi": "chahada CISI",
        "quiz": "quiz ta3limi",
        "championnat": "mossaba9a boursa",
        "orientation": "tawjih ta3allom",
        "support_ecole": "support l ecole",
        "out_of_domain": "mawdo3 barra",
    },
    "ary-arabic": {
        "pedagogie": "تعليم مالي",
        "formation_elearning": "تكوين اونلاين",
        "cisi": "شهادة CISI",
        "quiz": "اختبار تعليمي",
        "championnat": "مسابقة البورصة",
        "orientation": "توجيه التعلم",
        "support_ecole": "دعم المدرسة",
        "out_of_domain": "موضوع خارج المجال",
    },
}

ROUTE_TEXT = {
    "fr": {
        "pedagogie": (
            "Explique {x}",
            "Que signifie {x}",
            "Definition de {x}",
            "Comment fonctionne {x}",
        ),
        "formation_elearning": (
            "Je cherche une formation",
            "Je veux apprendre {x}",
            "Ou trouver un cours",
            "Acceder au parcours e-learning",
        ),
        "cisi": (
            "Informations sur CISI",
            "Comment preparer la certification",
            "Parcours de certification professionnelle",
            "Exigences de conformite CISI",
        ),
        "quiz": (
            "Je veux un quiz",
            "Lance un questionnaire",
            "Teste mes connaissances",
            "Propose un test educatif",
        ),
        "championnat": (
            "Comment fonctionne le championnat",
            "Informations e-Bourse",
            "Je veux participer au concours",
            "Portefeuille fictif du championnat",
        ),
        "orientation": (
            "Par ou commencer",
            "Quel parcours pour debuter",
            "Aide-moi a choisir un parcours d'apprentissage",
            "Je suis debutant en finance",
        ),
        "support_ecole": (
            "Je n'arrive pas a me connecter",
            "J'ai oublie mon mot de passe",
            "Probleme avec mon compte ecole",
            "Comment faire une inscription",
        ),
        "out_of_domain": (
            "Donne-moi une recette",
            "Quel temps fera-t-il demain",
            "Aide-moi a reparer mon ordinateur",
            "Raconte une histoire",
            "Je supporte mal le stress",
            "Le stockage de mes photos est plein",
        ),
    },
    "en": {
        "pedagogie": (
            "Explain {x}",
            "What does {x} mean",
            "Define {x}",
            "How does {x} work",
        ),
        "formation_elearning": (
            "I am looking for a course",
            "I want to learn {x}",
            "Where can I find training",
            "Access the e-learning path",
        ),
        "cisi": (
            "CISI information",
            "How do I prepare for certification",
            "Professional certification path",
            "CISI compliance requirements",
        ),
        "quiz": (
            "I want a quiz",
            "Start a questionnaire",
            "Test my knowledge",
            "Give me an educational test",
        ),
        "championnat": (
            "How does the championship work",
            "e-Bourse information",
            "I want to join the competition",
            "Championship simulated portfolio",
        ),
        "orientation": (
            "Where should I start",
            "Which path for a beginner",
            "Help me choose a learning path",
            "I am new to finance",
        ),
        "support_ecole": (
            "I cannot log in",
            "I forgot my password",
            "Problem with my school account",
            "How do I register",
        ),
        "out_of_domain": (
            "Give me a recipe",
            "What is the weather tomorrow",
            "Help repair my computer",
            "Tell me a story",
        ),
    },
    "ar": {
        "pedagogie": ("اشرح السهم", "ما معنى السند", "تعريف المؤشر", "كيف يعمل السوق"),
        "formation_elearning": (
            "ابحث عن دورة",
            "اريد تعلم الاستثمار",
            "اين اجد التكوين",
            "الوصول الى التعلم الالكتروني",
        ),
        "cisi": (
            "معلومات عن CISI",
            "كيف اعد لشهادة مهنية",
            "مسار الشهادة المهنية",
            "متطلبات الامتثال المهني",
        ),
        "quiz": (
            "اريد اختبارا",
            "ابدأ استبيانا",
            "اختبر معلوماتي",
            "اختبار تعليمي عن المخاطر",
        ),
        "championnat": (
            "كيف تعمل البطولة",
            "معلومات عن اي بورصة",
            "اريد المشاركة في المسابقة",
            "محفظة افتراضية للبطولة",
        ),
        "orientation": (
            "من اين ابدأ",
            "ما المسار للمبتدئ",
            "ساعدني في اختيار مسار التعلم",
            "انا مبتدئ في المالية",
        ),
        "support_ecole": (
            "لا استطيع تسجيل الدخول",
            "نسيت كلمة المرور",
            "مشكلة في حساب المدرسة",
            "كيف اسجل حسابا",
        ),
        "out_of_domain": (
            "اعطني وصفة طبخ",
            "كيف سيكون الطقس غدا",
            "ساعدني في اصلاح الحاسوب",
            "احك لي قصة",
        ),
    },
    "ary-latin": {
        "pedagogie": (
            "chno howa saham",
            "chr7 lia bond",
            "ma3na indice",
            "kifach katkhdem lborsa",
        ),
        "formation_elearning": (
            "bghit formation",
            "bghit nt3ellem l investissement",
            "fin kayn cours",
            "bghit nwl l e-learning",
        ),
        "cisi": (
            "ma3lomat 3la CISI",
            "kifach nwjjed certification",
            "masar certification mihaniya",
            "chno homa chourout CISI",
        ),
        "quiz": (
            "bghit quiz",
            "bda questionnaire",
            "jرب ma3rfti",
            "3tini test ta3limi",
        ),
        "championnat": (
            "kifach kaydour championnat",
            "ma3lomat 3la e-Bourse",
            "bghit ncharak f concours",
            "portfolio fictif dyal championnat",
        ),
        "orientation": (
            "mnin nbda",
            "achmen masar l mobtadi",
            "3awni nkhtar masar ta3allom",
            "ana jd id f finance",
        ),
        "support_ecole": (
            "ma9dertch ndkhol",
            "nsit mot de passe",
            "mouchkil f compte dyal l ecole",
            "kifach ntsjel",
        ),
        "out_of_domain": (
            "3tini wasfa dyal lmakla",
            "chno ta9s ghdda",
            "3awni nsla7 ordinateur",
            "7ki lia chi 9issa",
        ),
    },
    "ary-arabic": {
        "pedagogie": (
            "شنو هو السهم",
            "شرح ليا السند",
            "معنى المؤشر",
            "كيفاش كتخدم البورصة",
        ),
        "formation_elearning": (
            "بغيت تكوين",
            "بغيت نتعلم الاستثمار",
            "فين كاين الكورس",
            "بغيت نوصل للتعلم الالكتروني",
        ),
        "cisi": (
            "معلومات على CISI",
            "كيفاش نوجد الشهادة",
            "مسار الشهادة المهنية",
            "شروط الامتثال ديال CISI",
        ),
        "quiz": ("بغيت اختبار", "بدا الاستبيان", "جرب معلوماتي", "عطيني اختبار تعليمي"),
        "championnat": (
            "كيفاش كيدور الشامبيوناط",
            "معلومات على اي بورصة",
            "بغيت نشارك فالمسابقة",
            "محفظة وهمية ديال البطولة",
        ),
        "orientation": (
            "منين نبدا",
            "اشمن مسار للمبتدئ",
            "عاونّي نختار مسار التعلم",
            "انا مبتدئ فالمالية",
        ),
        "support_ecole": (
            "ماقدرتش ندخل",
            "نسيت كلمة السر",
            "مشكل فحساب المدرسة",
            "كيفاش نسجل",
        ),
        "out_of_domain": (
            "عطيني وصفة ديال الماكلة",
            "شنو الطقس غدا",
            "عاونّي نصلح الحاسوب",
            "حكي ليا قصة",
        ),
    },
}

SECURITY_TEXT = {
    "fr": (
        "Quelle action acheter pour moi",
        "Vends mon titre maintenant",
        "Repartis mon epargne",
        "Quel placement me convient",
        "Prevois la hausse de ce titre",
        "Explique la diversification",
        "Definition de l allocation",
        "Comparaison generale des actions",
        "Histoire du marche",
        "Notion de risque",
    ),
    "en": (
        "Which stock should I buy for me",
        "Sell my holding now",
        "Allocate my savings",
        "What investment suits me",
        "Predict this stock rise",
        "Explain diversification",
        "Definition of allocation",
        "General comparison of stocks",
        "History of the market",
        "Risk concept",
    ),
    "ar": (
        "اي سهم اشتريه لي",
        "بع اسهمي الان",
        "قسم مدخراتي",
        "ما الاستثمار المناسب لي",
        "توقع ارتفاع السهم",
        "اشرح التنويع",
        "تعريف توزيع الاصول",
        "مقارنة عامة بين الاسهم",
        "تاريخ السوق",
        "مفهوم المخاطر",
    ),
    "ary-latin": (
        "achmen saham nchri lia",
        "bi3 saham dyali daba",
        "qssm flousi",
        "ach kaynasbni f l istithmar",
        "wach ghadi ytla3 saham",
        "chr7 tanwi3",
        "ta3rif tawzi3 l osoul",
        "m9arana 3amma dyal saham",
        "tarikh sou9",
        "mafhoum l mokhatara",
    ),
    "ary-arabic": (
        "اشمن سهم نشريه ليا",
        "بيع السهم ديالي دابا",
        "قسم ليا فلوسي",
        "شنو الاستثمار اللي مناسب ليا",
        "واش غادي يطلع السهم",
        "شرح التنويع",
        "تعريف توزيع الاصول",
        "مقارنة عامة ديال الاسهم",
        "تاريخ السوق",
        "مفهوم المخاطر",
    ),
}


def build_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for language in LANGUAGES:
        for route in ROUTES:
            for index, template in enumerate(ROUTE_TEXT[language][route]):
                for variant in range(4):
                    text = template.format(
                        x=(
                            "les actions"
                            if language == "fr"
                            else "stocks"
                            if language == "en"
                            else "السهم"
                            if language == "ar"
                            else "saham"
                        )
                    )
                    text = (
                        f"{text} {ROUTE_HINTS[language][route]}{VARIANT_SUFFIXES[variant]}"
                    ).strip()
                    rows.append(
                        {
                            "text": text,
                            "label": route,
                            "language": language,
                            "semantic_family": f"{route}_{index}",
                        }
                    )
        for index, text in enumerate(SECURITY_TEXT[language]):
            sensitive = index < 5
            for variant in range(4):
                security_hint = (
                    "personalized financial advice"
                    if sensitive
                    else "general educational explanation"
                )
                rows.append(
                    {
                        "text": f"{text} {security_hint}{VARIANT_SUFFIXES[variant]}".strip(),
                        "label": "sensitive_personalized_financial_advice"
                        if sensitive
                        else "safe",
                        "language": language,
                        "semantic_family": (
                            f"security_{'sensitive' if sensitive else 'safe'}_{index}"
                        ),
                    }
                )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path, default=Path("data/j3/contract_examples.jsonl")
    )
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rows = build_rows()
    args.output.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {len(rows)} internal contract examples to {args.output}")


if __name__ == "__main__":
    main()
