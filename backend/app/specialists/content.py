"""Small authored multilingual responses for J7 specialist agents."""
# ruff: noqa: E501

from types import MappingProxyType

LOCALES = ("fr/latin", "en/latin", "ar/arabic", "ary/latin", "ary/arabic")

_CONTENT = MappingProxyType({
    "cisi": MappingProxyType({
        "fr/latin": "CISI propose un parcours de certification financière. Préparez les concepts, entraînez-vous avec des questions et vérifiez les informations administratives dans le catalogue officiel; les frais, dates et conditions actuels ne sont pas disponibles ici.",
        "en/latin": "CISI offers a financial certification learning path. Prepare the concepts, practise with questions, and check current administrative details in the official catalogue; fees, dates, and eligibility are not available here.",
        "ar/arabic": "يقدم CISI مسارا تعليميا للحصول على شهادة مالية. راجع المفاهيم وتدرب على الأسئلة، وتحقق من التفاصيل الإدارية الحالية في الدليل الرسمي؛ فالرسوم والمواعيد وشروط الأهلية غير متاحة هنا.",
        "ary/latin": "CISI kay3ti massar ta3allomi dyal certification f lmajal lmali. Raje3 lmafahim w tmern 3la l2as2ila, w chekk lma3loumat l2idariya f catalogue rasmi; l2atman w lmwa3id w chourout ma kaynach hna.",
        "ary/arabic": "CISI كيعطي مسار تعليمي ديال شهادة فالمجال المالي. راجع المفاهيم وتدرب على الأسئلة، وتأكد من المعطيات الإدارية فالدليل الرسمي؛ الأثمنة والمواعيد والشروط ما متوفراش هنا.",
    }),
    "championnat": MappingProxyType({
        "fr/latin": "Le Championnat et e-Bourse sont des environnements de simulation: les transactions et le portefeuille y sont virtuels. Utilisez-les pour observer vos décisions, le risque et la diversification; les classements, prix et données en direct ne sont pas disponibles ici.",
        "en/latin": "The Championship and e-Bourse are simulation environments: transactions and portfolios are virtual. Use them to review decisions, risk, and diversification; live rankings, prices, and competition data are not available here.",
        "ar/arabic": "البطولة و e-Bourse بيئتان للمحاكاة، فالمعاملات والمحفظة فيهما افتراضيتان. استعملهما لمراجعة القرارات والمخاطر والتنويع؛ أما الترتيب والأسعار والبيانات المباشرة فغير متاحة هنا.",
        "ary/latin": "Championnat w e-Bourse homa bi2at simulation: lmo3amalat w portefeuille fihom virtuels. Sta3melhom bach traj3 9raratek w lkhatar w t-tanwi3; classement w tman w ma3loumat live ma kaynach hna.",
        "ary/arabic": "Championnat و e-Bourse هما بيئات ديال المحاكاة، المعاملات والمحفظة فيهم افتراضية. استعملهم باش تراجع القرارات والمخاطر والتنويع؛ الترتيب والأثمنة والمعطيات المباشرة ما متوفراش هنا.",
    }),
    "support_ecole": MappingProxyType({
        "fr/latin": "L’École de la Bourse regroupe des services éducatifs comme la Formation, le Quiz, le Championnat et l’orientation CISI. Pour accéder à un parcours, utilisez la Formation; pour vérifier vos acquis, utilisez le Quiz. Les informations de compte, horaires, prix et contacts ne sont pas disponibles ici.",
        "en/latin": "École de la Bourse brings together educational services such as Formation, Quiz, Championship, and CISI orientation. Use Formation to follow a path and Quiz to check your knowledge. Account details, opening hours, prices, and contacts are not available here.",
        "ar/arabic": "تجمع مدرسة البورصة خدمات تعليمية مثل التكوين والاختبار والبطولة والتوجيه نحو CISI. استعمل التكوين لاتباع مسار تعليمي والاختبار للتحقق من معارفك. تفاصيل الحساب والمواعيد والأسعار وبيانات الاتصال غير متاحة هنا.",
        "ary/latin": "Ecole de la Bourse fiha khadamat ta3limiya b7al Formation, Quiz, Championnat w tawjih CISI. Sta3mel Formation bach teb3 massar, w Quiz bach tchek lma3rifa dyalk. Ma3loumat compte w lwa9t w taman w contacts ma kaynach hna.",
        "ary/arabic": "مدرسة البورصة فيها خدمات تعليمية بحال التكوين والاختبار والبطولة والتوجيه نحو CISI. استعمل التكوين باش تتبع مسار، والاختبار باش تشيك المعرفة ديالك. معلومات الحساب والمواعيد والأثمنة وبيانات الاتصال ما متوفراش هنا.",
    }),
    "out_of_domain": MappingProxyType({
        "fr/latin": "Ma mission est de vous accompagner dans votre apprentissage des marchés financiers et de la Bourse. Cette demande est hors de mon périmètre pédagogique. Je peux vous aider avec les instruments financiers, les marchés de capitaux, la gestion du risque ou les services de l’École de la Bourse.",
        "en/latin": "My mission is to support your learning about financial markets and the stock exchange. This request is outside my educational scope. I can help with financial instruments, capital markets, risk management, or École de la Bourse services.",
        "ar/arabic": "مهمتي هي مساعدتك على تعلم الأسواق المالية والبورصة. هذا الطلب خارج نطاقي التعليمي. يمكنني مساعدتك في فهم الأدوات المالية وأسواق رأس المال وإدارة المخاطر أو خدمات مدرسة البورصة.",
        "ary/latin": "Lmohemma dyali hiya n3awnek t3ellem l2aswa9 lmaliya w lborsa. Had talab barra mn lmajal ta3limi dyali. N9der n3awnek f l2adawat lmaliya, aswa9 rass lmal, tadbir lkhatar w khadamat Ecole de la Bourse.",
        "ary/arabic": "المهمة ديالي هي نعاونك تتعلم الأسواق المالية والبورصة. هاد الطلب خارج على المجال التعليمي ديالي. نقدر نعاونك فالأدوات المالية وأسواق رأس المال وتدبير المخاطر ولا خدمات مدرسة البورصة.",
    }),
})


def render_specialist_response(route: str, language: str, script: str) -> str:
    locale = f"{language}/{script}"
    if locale not in LOCALES or route not in _CONTENT:
        raise ValueError("unsupported specialist locale or route")
    return _CONTENT[route][locale]
