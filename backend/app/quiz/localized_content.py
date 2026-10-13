"""Explicitly authored localized quiz content for the curated question bank.

This module holds static, hand-authored content only. Every non-French variant
is written out in full: prompt, the four options A/B/C/D, and the explanation.

Rules that this data must always satisfy (enforced by the unit tests):

* Positional semantic alignment -- option ``X`` carries the same financial
  meaning in every locale as the canonical French option ``X``.
* The canonical correct letter is identical across all locales.
* No option announces itself as the correct one.
* ``ary/latin`` contains no Arabic codepoints; ``ary/arabic`` is Moroccan
  Darija in Arabic script and is never a copy of the MSA row.

Nothing here is generated at runtime from a topic name, level or index.
"""

# ruff: noqa: E501

NON_FRENCH_LOCALES: tuple[tuple[str, str], ...] = (
    ("en", "latin"),
    ("ar", "arabic"),
    ("ary", "latin"),
    ("ary", "arabic"),
)

LOCALIZED_CONTENT: dict[str, dict[tuple[str, str], dict[str, object]]] = {
    "diag-1": {
        ("en", "latin"): {
            "prompt": "What is the main role of a stock exchange?",
            "options": {
                "A": "To organise the trading of securities within a regulated framework",
                "B": "To guarantee a profit to every investor",
                "C": "To grant loans to companies and households",
                "D": "To set wages in the economy",
            },
            "explanation": "A stock exchange organises the trading of securities inside a regulated framework; it does not promise profits, lend money or set wages.",
        },
        ("ar", "arabic"): {
            "prompt": "ما هو الدور الرئيسي للبورصة؟",
            "options": {
                "A": "تنظيم تبادل الأوراق المالية في إطار منظم",
                "B": "ضمان الربح لكل مستثمر",
                "C": "منح القروض للشركات والأفراد",
                "D": "تحديد الأجور في الاقتصاد",
            },
            "explanation": "تنظم البورصة تداول الأوراق المالية داخل إطار قانوني، ولا تضمن ربحا ولا تمنح قروضا ولا تحدد الأجور.",
        },
        ("ary", "latin"): {
            "prompt": "Chno howa dour l2assassi dyal lborsa?",
            "options": {
                "A": "Katnadem tbadol dyal l awra9 lmaliya f itar mnadem",
                "B": "Katdmen rbe7 l kola mostatmir",
                "C": "Kat3ti l9rod l charikat w nnas",
                "D": "Kat7edded lujour f l iqtisad",
            },
            "explanation": "Lborsa katnadem tbadol dyal l awra9 lmaliya f itar qanouni, ma katdmen ta rbe7 wla kat3ti 9rod wla kat7edded lujour.",
        },
        ("ary", "arabic"): {
            "prompt": "شنو هو الدور الأساسي ديال البورصة؟",
            "options": {
                "A": "كتنظم تبادل الأوراق المالية ف إطار منظم",
                "B": "كتضمن الربح لكل مستثمر",
                "C": "كتعطي القروض للشركات والناس",
                "D": "كتحدد الأجور فالاقتصاد",
            },
            "explanation": "البورصة كتنظم تبادل الأوراق المالية ف إطار قانوني، ماكتضمنش الربح وماكتعطيش القروض وماكتحددش الأجور.",
        },
    },
    "diag-2": {
        ("en", "latin"): {
            "prompt": "What does a share mainly represent?",
            "options": {
                "A": "A short-term debt owed by the company",
                "B": "A fraction of a company's capital",
                "C": "A guaranteed return paid every year",
                "D": "An insurance contract",
            },
            "explanation": "A share represents a fraction of a company's capital, which makes the holder a part-owner rather than a creditor.",
        },
        ("ar", "arabic"): {
            "prompt": "ماذا يمثل السهم بشكل أساسي؟",
            "options": {
                "A": "دينا قصير الأجل على الشركة",
                "B": "جزءا من رأس مال الشركة",
                "C": "عائدا مضمونا يدفع كل سنة",
                "D": "عقد تأمين",
            },
            "explanation": "يمثل السهم جزءا من رأس مال الشركة، فيصبح حامله شريكا في الملكية وليس دائنا.",
        },
        ("ary", "latin"): {
            "prompt": "Ash kaymattel saham f charika?",
            "options": {
                "A": "Din 9sir lmoudda 3la charika",
                "B": "Jouz2 mn ras lmal dyal charika",
                "C": "Rbe7 mdmoun kaytkhalles kola 3am",
                "D": "3a9d dyal ta2min",
            },
            "explanation": "Saham kaymattel jouz2 mn ras lmal dyal charika, 3la haqach moul saham kaywlli charik f lmilkiya machi dayn.",
        },
        ("ary", "arabic"): {
            "prompt": "أشنو كيمثل السهم فالشركة؟",
            "options": {
                "A": "دين قصير المدة على الشركة",
                "B": "جزء من رأس المال ديال الشركة",
                "C": "ربح مضمون كيتخلص كل عام",
                "D": "عقد ديال التأمين",
            },
            "explanation": "السهم كيمثل جزء من رأس المال ديال الشركة، ومولاه كيولي شريك فالملكية ماشي دائن.",
        },
    },
    "diag-3": {
        ("en", "latin"): {
            "prompt": "Which statement best describes the link between risk and expected return?",
            "options": {
                "A": "A higher expected return may involve taking more risk",
                "B": "Risk always disappears over time",
                "C": "The return is fixed and guaranteed in advance",
                "D": "Risk and return are always independent of each other",
            },
            "explanation": "Seeking a higher expected return usually means accepting greater uncertainty; the extra return is expected, never promised.",
        },
        ("ar", "arabic"): {
            "prompt": "أي عبارة تصف العلاقة بين المخاطر والعائد المتوقع؟",
            "options": {
                "A": "العائد المتوقع الأعلى قد يستلزم تحمل مخاطر أكبر",
                "B": "المخاطر تختفي دائما مع مرور الوقت",
                "C": "العائد محدد ومضمون مسبقا",
                "D": "المخاطر والعائد مستقلان دائما عن بعضهما",
            },
            "explanation": "السعي إلى عائد متوقع أعلى يعني عادة قبول قدر أكبر من عدم اليقين، فالعائد متوقع وليس موعودا به.",
        },
        ("ary", "latin"): {
            "prompt": "Chno l3ala9a bin lkhatar w rrbe7 lmontadar?",
            "options": {
                "A": "Rrbe7 lmontadar lli kbir momkin yjib m3ah mkhatir kter",
                "B": "Lmkhatir kaytmse7 dima m3a lwe9t",
                "C": "Rrbe7 m7dood w mdmoun mn 9bel",
                "D": "Lmkhatir w rrbe7 dima mst9lin 3la be3diyathom",
            },
            "explanation": "Ila bghiti rbe7 montadar kter, khassek t9bel 3adam yaqin kter; rrbe7 howa montadar machi mou3oud bih.",
        },
        ("ary", "arabic"): {
            "prompt": "أشنو العلاقة بين المخاطر والربح المنتظر؟",
            "options": {
                "A": "الربح المنتظر لي كبير يمكن يجي معاه مخاطر كثر",
                "B": "المخاطر كتمحى ديما مع الوقت",
                "C": "الربح محدود ومضمون من قبل",
                "D": "المخاطر والربح ديما مستقلين على بعضياتهم",
            },
            "explanation": "إلا بغيتي ربح منتظر كثر، خاصك تقبل عدم اليقين كثر؛ الربح هو منتظر ماشي موعود بيه.",
        },
    },
    "diag-4": {
        ("en", "latin"): {
            "prompt": "What is one purpose of diversification?",
            "options": {
                "A": "To reduce certain risks by spreading exposure across several assets",
                "B": "To remove every risk from a portfolio",
                "C": "To guarantee that the best-performing security is selected",
                "D": "To avoid having to read any information",
            },
            "explanation": "Diversification spreads exposure so that one disappointing position weighs less, but it reduces certain risks without eliminating them.",
        },
        ("ar", "arabic"): {
            "prompt": "ما الهدف من تنويع الاستثمارات؟",
            "options": {
                "A": "تقليل بعض المخاطر عبر توزيع الانكشاف على عدة أصول",
                "B": "إزالة كل المخاطر من المحفظة",
                "C": "ضمان اختيار أفضل ورقة مالية أداء",
                "D": "الاستغناء عن قراءة أي معلومة",
            },
            "explanation": "يوزع التنويع الانكشاف حتى يقل أثر أي مركز خاسر، لكنه يخفف بعض المخاطر دون أن يلغيها.",
        },
        ("ary", "latin"): {
            "prompt": "3lash kaydiro tanwi3 f l istitmar?",
            "options": {
                "A": "Bach yn9so chi mkhatir mn khlal twzi3 lflous 3la bezzaf d l asol",
                "B": "Bach ymse7o kol lmkhatir mn lportefeuille",
                "C": "Bach ydemno khtiyar a7san wra9a f l ada2",
                "D": "Bach may9rawch ta ma3louma",
            },
            "explanation": "Tanwi3 kaywzze3 l inkichaf 7it wa7d lmarkaz khayeb may2ttarch bezzaf, walakin kayn9es chi mkhatir machi kaymse7hom kolhom.",
        },
        ("ary", "arabic"): {
            "prompt": "علاش كيديرو التنويع فالاستثمار؟",
            "options": {
                "A": "باش ينقصو شي مخاطر عن طريق توزيع الفلوس على بزاف ديال الأصول",
                "B": "باش يمحيو كل المخاطر من المحفظة",
                "C": "باش يضمنو اختيار أحسن ورقة فالأداء",
                "D": "باش مايقراو حتى معلومة",
            },
            "explanation": "التنويع كيوزع الانكشاف حيت واحد المركز خايب مايأثرش بزاف، ولكن كينقص شي مخاطر ماكيمحيهومش كاملين.",
        },
    },
    "diag-5": {
        ("en", "latin"): {
            "prompt": "On which market does a company issue new securities?",
            "options": {
                "A": "The secondary market, where existing securities change hands",
                "B": "The insurance market",
                "C": "The primary market, where newly created securities are issued",
                "D": "The real-estate market",
            },
            "explanation": "New securities are created and sold for the first time on the primary market; later trades between investors take place on the secondary market.",
        },
        ("ar", "arabic"): {
            "prompt": "في أي سوق تصدر الشركة أوراقا مالية جديدة؟",
            "options": {
                "A": "السوق الثانوي حيث تتداول الأوراق القائمة",
                "B": "سوق التأمين",
                "C": "السوق الأولي حيث تصدر الأوراق المالية الجديدة",
                "D": "السوق العقاري",
            },
            "explanation": "تصدر الأوراق المالية الجديدة وتباع لأول مرة في السوق الأولي، أما التداول اللاحق بين المستثمرين فيتم في السوق الثانوي.",
        },
        ("ary", "latin"): {
            "prompt": "F ina sou9 katsder charika wra9 maliya jdida?",
            "options": {
                "A": "Sou9 ttanawi fin kaytbadlo lwra9 lli deja kaynin",
                "B": "Sou9 dyal ta2minat",
                "C": "Sou9 l2awwali fin kaytsedro lwra9 lmaliya jdida",
                "D": "Sou9 dyal l3a9ar",
            },
            "explanation": "Lwra9 lmaliya jdida kaytsedro w kaytba3o l lewwel merra f sou9 l2awwali, w mn be3d kaytbadlo bin lmostatmirin f sou9 ttanawi.",
        },
        ("ary", "arabic"): {
            "prompt": "فأي سوق كتصدر الشركة أوراق مالية جديدة؟",
            "options": {
                "A": "السوق الثانوي فين كيتبادلو الأوراق لي ديجا كاينين",
                "B": "السوق ديال التأمينات",
                "C": "السوق الأولي فين كيتصدرو الأوراق المالية الجديدة",
                "D": "السوق ديال العقار",
            },
            "explanation": "الأوراق المالية الجديدة كيتصدرو وكيتباعو لأول مرة فالسوق الأولي، ومن بعد كيتبادلو بين المستثمرين فالسوق الثانوي.",
        },
    },
    "diag-6": {
        ("en", "latin"): {
            "prompt": "What is the purpose of the information document published for an IPO?",
            "options": {
                "A": "To guarantee a capital gain to subscribers",
                "B": "To promise the future share price",
                "C": "To replace the applicable regulation",
                "D": "To present the information needed to evaluate the operation",
            },
            "explanation": "The IPO information document sets out the issuer's situation, the terms of the offer and its risks so investors can form their own judgement; it promises nothing about performance.",
        },
        ("ar", "arabic"): {
            "prompt": "ما الغرض من وثيقة المعلومات المنشورة عند الإدراج في البورصة؟",
            "options": {
                "A": "ضمان تحقيق أرباح رأسمالية للمكتتبين",
                "B": "الوعد بسعر السهم في المستقبل",
                "C": "تعويض الأنظمة والقوانين المعمول بها",
                "D": "تقديم المعلومات اللازمة لتقييم العملية",
            },
            "explanation": "تعرض وثيقة الإدراج وضعية المصدر وشروط العملية ومخاطرها ليكون المستثمر رأيه بنفسه، وهي لا تعد بأي أداء.",
        },
        ("ary", "latin"): {
            "prompt": "Chno lfayda dyal wat9a d lma3loumat lli katnchar f l IPO?",
            "options": {
                "A": "Katdmen rbe7 f ras lmal l ferra9a lli chraw",
                "B": "Kat3ed b taman dyal saham f lmosta9bal",
                "C": "Kat3awad l qawanin lli khedama",
                "D": "Kat9ddem lma3loumat lli khass bach ttqiyyem l3amaliya",
            },
            "explanation": "Wat9a d l IPO kat3ard wad3iyat lmosder w chourout l3amaliya w lmkhatir dyalha bach lmostatmir ykawwen ra2yo, walakin ma kat3ed b ta ada2.",
        },
        ("ary", "arabic"): {
            "prompt": "شنو الفايدة ديال وثيقة المعلومات لي كتنشر فالإدراج؟",
            "options": {
                "A": "كتضمن ربح فرأس المال للي شراو",
                "B": "كتوعد بثمن السهم فالمستقبل",
                "C": "كتعوض القوانين لي خدامة",
                "D": "كتقدم المعلومات لي خاصة باش تقيم العملية",
            },
            "explanation": "وثيقة الإدراج كتعرض وضعية المصدر وشروط العملية والمخاطر ديالها باش المستثمر يكون رأيو، ولكن ماكتوعد بحتى أداء.",
        },
    },
    "beginner-1": {
        ("en", "latin"): {
            "prompt": "What does an ordinary share represent for its holder?",
            "options": {
                "A": "An invoice issued to a customer",
                "B": "A share in the company's capital",
                "C": "A bank loan granted to the company",
                "D": "A guarantee against loss",
            },
            "explanation": "An ordinary share gives its holder a stake in the company's capital, with the rights and the uncertainty that ownership carries.",
        },
        ("ar", "arabic"): {
            "prompt": "ماذا يمثل السهم العادي لحامله؟",
            "options": {
                "A": "فاتورة موجهة إلى زبون",
                "B": "حصة في رأس مال الشركة",
                "C": "قرضا بنكيا ممنوحا للشركة",
                "D": "ضمانة ضد الخسارة",
            },
            "explanation": "يمنح السهم العادي حامله حصة في رأس مال الشركة، بما يترتب عن الملكية من حقوق ومن عدم يقين.",
        },
        ("ary", "latin"): {
            "prompt": "Ashno kay3ni saham 3adi lmostatmir?",
            "options": {
                "A": "Fatura msifta l chi klian",
                "B": "7essa f ras lmal dyal charika",
                "C": "Selfa bankiya lli khdat charika",
                "D": "Daman ded lkhsara",
            },
            "explanation": "Saham 3adi kay3ti l moulah 7essa f ras lmal dyal charika, b l7o9o9 w b 3adam lyaqin lli kayjiw m3a lmilkiya.",
        },
        ("ary", "arabic"): {
            "prompt": "أشنو كيعني السهم العادي لمولاه؟",
            "options": {
                "A": "فاتورة مصيفطة لشي كليان",
                "B": "حصة فرأس المال ديال الشركة",
                "C": "سلفة بنكية لي خدات الشركة",
                "D": "ضمانة ضد الخسارة",
            },
            "explanation": "السهم العادي كيعطي لمولاه حصة فرأس المال ديال الشركة، بالحقوق وبعدم اليقين لي كيجيو مع الملكية.",
        },
    },
    "beginner-2": {
        ("en", "latin"): {
            "prompt": "What does a bond generally represent?",
            "options": {
                "A": "A claim held against the issuer that borrowed the money",
                "B": "A share in the issuer's capital",
                "C": "A dividend paid to shareholders",
                "D": "A stock-market index",
            },
            "explanation": "A bond is a debt security: the holder lends to the issuer and holds a claim, unlike a shareholder who owns part of the capital.",
        },
        ("ar", "arabic"): {
            "prompt": "ماذا يمثل السند عموما؟",
            "options": {
                "A": "دينا في ذمة الجهة المصدرة التي اقترضت المال",
                "B": "حصة في رأس مال الجهة المصدرة",
                "C": "أرباحا موزعة على المساهمين",
                "D": "مؤشرا للسوق المالي",
            },
            "explanation": "السند ورقة دين: يقرض حامله الجهة المصدرة ويصبح دائنا لها، خلافا للمساهم الذي يملك جزءا من رأس المال.",
        },
        ("ary", "latin"): {
            "prompt": "Ash kaymattel sanad b chakl 3am?",
            "options": {
                "A": "Din f dimmat lmosder lli tsellef lflous",
                "B": "7essa f ras lmal dyal lmosder",
                "C": "Arba7 mwezz3a 3la lmossahimin",
                "D": "Mo2achir dyal sou9 lmal",
            },
            "explanation": "Sanad howa wra9 dyal din: moulah kaysellef lmosder w kaywlli dayn 3lih, machi b7al lmossahim lli kaymlek jouz2 mn ras lmal.",
        },
        ("ary", "arabic"): {
            "prompt": "أشنو كيمثل السند بشكل عام؟",
            "options": {
                "A": "دين فذمة المصدر لي تسلف الفلوس",
                "B": "حصة فرأس المال ديال المصدر",
                "C": "أرباح موزعة على المساهمين",
                "D": "مؤشر ديال سوق المال",
            },
            "explanation": "السند هو ورقة ديال الدين: مولاه كيسلف المصدر وكيولي دائن عليه، ماشي بحال المساهم لي كيملك جزء من رأس المال.",
        },
    },
    "beginner-3": {
        ("en", "latin"): {
            "prompt": "What is a dividend?",
            "options": {
                "A": "A tax levied on the company's turnover",
                "B": "An instruction sent to a broker to buy or sell",
                "C": "A possible distribution of profit to shareholders",
                "D": "An index measuring the whole market",
            },
            "explanation": "A dividend is a share of profit that a company may distribute to its shareholders; it is decided each year and is never automatic.",
        },
        ("ar", "arabic"): {
            "prompt": "ما هو توزيع الأرباح؟",
            "options": {
                "A": "ضريبة تفرض على رقم معاملات الشركة",
                "B": "أمر يوجه إلى الوسيط للشراء أو البيع",
                "C": "توزيع محتمل لجزء من الأرباح على المساهمين",
                "D": "مؤشر يقيس أداء السوق كاملة",
            },
            "explanation": "توزيع الأرباح هو جزء من أرباح الشركة قد يوزع على المساهمين، ويقرر كل سنة وليس تلقائيا.",
        },
        ("ary", "latin"): {
            "prompt": "Chno howa dividende f charika?",
            "options": {
                "A": "Dariba kattfred 3la ra9m lmo3amalat dyal charika",
                "B": "Amr kaytsifet l wasit bach ychri wla ybi3",
                "C": "Twzi3 momkin dyal jouz2 mn l arba7 3la lmossahimin",
                "D": "Mo2achir kay9is l ada2 dyal sou9 kamla",
            },
            "explanation": "Dividende howa jouz2 mn arba7 charika lli momkin ytwezze3 3la lmossahimin, w kaytqarrar kol 3am w machi otomatiki.",
        },
        ("ary", "arabic"): {
            "prompt": "شنو هو توزيع الأرباح فالشركة؟",
            "options": {
                "A": "ضريبة كتفرض على رقم المعاملات ديال الشركة",
                "B": "أمر كيتصيفط للوسيط باش يشري ولا يبيع",
                "C": "توزيع ممكن ديال جزء من الأرباح على المساهمين",
                "D": "مؤشر كيقيس الأداء ديال السوق كاملة",
            },
            "explanation": "توزيع الأرباح هو جزء من أرباح الشركة لي ممكن يتوزع على المساهمين، وكيتقرر كل عام وماشي أوتوماتيكي.",
        },
    },
    "beginner-4": {
        ("en", "latin"): {
            "prompt": "What does a stock-market index track?",
            "options": {
                "A": "The repayment of one single debt",
                "B": "The level of wages in the economy",
                "C": "A guaranteed interest rate",
                "D": "The performance of a defined group of securities",
            },
            "explanation": "A stock-market index follows the performance of a defined basket of securities and is used to observe how a market or a segment evolves.",
        },
        ("ar", "arabic"): {
            "prompt": "ماذا يتتبع المؤشر البورصي؟",
            "options": {
                "A": "سداد دين واحد بعينه",
                "B": "مستوى الأجور في الاقتصاد",
                "C": "نسبة فائدة مضمونة",
                "D": "تطور مجموعة محددة من الأوراق المالية",
            },
            "explanation": "يتتبع المؤشر البورصي أداء سلة محددة من الأوراق المالية، ويستعمل لمتابعة تطور سوق أو قطاع معين.",
        },
        ("ary", "latin"): {
            "prompt": "Ash kaytbe3 lmo2achir lborsi?",
            "options": {
                "A": "Khlas dyal wa7d ddin bou7do",
                "B": "Mostawa lujour f l iqtisad",
                "C": "Nisbat fa2ida mdmouna",
                "D": "Tatawor dyal majmou3a m7addda dyal l awra9 lmaliya",
            },
            "explanation": "Lmo2achir lborsi kaytbe3 l ada2 dyal salla m7addda dyal l awra9 lmaliya, w kayt3ml bach tchouf kifach kaytatawwar chi sou9 wla chi 9ita3.",
        },
        ("ary", "arabic"): {
            "prompt": "أشنو كيتبع المؤشر البورصي؟",
            "options": {
                "A": "خلاص ديال واحد الدين بوحدو",
                "B": "مستوى الأجور فالاقتصاد",
                "C": "نسبة فائدة مضمونة",
                "D": "تطور مجموعة محددة ديال الأوراق المالية",
            },
            "explanation": "المؤشر البورصي كيتبع الأداء ديال سلة محددة ديال الأوراق المالية، وكيتعمل باش تشوف كيفاش كيتطور شي سوق ولا شي قطاع.",
        },
    },
    "beginner-5": {
        ("en", "latin"): {
            "prompt": "What should an investor consider before taking a decision?",
            "options": {
                "A": "Only the advertising seen about a product",
                "B": "Their objectives, the available information and the risks",
                "C": "A return promised in advance",
                "D": "Nothing in particular, since the outcome is a matter of luck",
            },
            "explanation": "A sound decision starts from the investor's own objectives, the information actually available and an honest reading of the risks involved.",
        },
        ("ar", "arabic"): {
            "prompt": "ماذا ينبغي أن يراعي المستثمر قبل اتخاذ قراره؟",
            "options": {
                "A": "الإشهار وحده الذي شاهده عن المنتج",
                "B": "أهدافه والمعلومات المتاحة والمخاطر المرتبطة",
                "C": "عائدا موعودا به مسبقا",
                "D": "لا شيء بالخصوص، لأن النتيجة مسألة حظ",
            },
            "explanation": "ينطلق القرار السليم من أهداف المستثمر ومن المعلومات المتاحة فعلا ومن قراءة صادقة للمخاطر.",
        },
        ("ary", "latin"): {
            "prompt": "Ash khass lmostatmir ychouf 9bel ma yakhod 9raro?",
            "options": {
                "A": "Ghir chi rreklam lli chaf 3la lmontouj",
                "B": "L ahdaf dyalo w lma3loumat lli kaynin w lmkhatir",
                "C": "Rbe7 mou3oud bih mn 9bel",
                "D": "Walo b lkhsos, 7it nnatija mas2ala dyal zher",
            },
            "explanation": "L9rar lmezyan kaybda mn l ahdaf dyal lmostatmir w mn lma3loumat lli kayna b sse7 w mn qra2a sari7a l lmkhatir.",
        },
        ("ary", "arabic"): {
            "prompt": "أشنو خاص المستثمر يشوف قبل مايدير القرار ديالو؟",
            "options": {
                "A": "غير شي ريكلام لي شاف على المنتوج",
                "B": "الأهداف ديالو والمعلومات لي كاينين والمخاطر",
                "C": "ربح موعود بيه من قبل",
                "D": "والو بالخصوص، حيت النتيجة مسألة ديال الزهر",
            },
            "explanation": "القرار المزيان كيبدا من الأهداف ديال المستثمر ومن المعلومات لي كاينة بصح ومن قراءة صريحة للمخاطر.",
        },
    },
    "beginner-6": {
        ("en", "latin"): {
            "prompt": "What does financial risk mean?",
            "options": {
                "A": "A guarantee attached to an investment",
                "B": "A price that stays fixed over time",
                "C": "The possibility that the outcome differs from what was expected",
                "D": "A legal obligation imposed on investors",
            },
            "explanation": "Financial risk is the possibility that the actual result of an investment differs from the expected one, in either direction.",
        },
        ("ar", "arabic"): {
            "prompt": "ماذا تعني المخاطر المالية؟",
            "options": {
                "A": "ضمانة مرتبطة بالاستثمار",
                "B": "سعرا يبقى ثابتا مع مرور الوقت",
                "C": "احتمال أن تختلف النتيجة الفعلية عما كان متوقعا",
                "D": "التزاما قانونيا مفروضا على المستثمرين",
            },
            "explanation": "المخاطر المالية هي احتمال أن تختلف النتيجة الفعلية للاستثمار عن النتيجة المتوقعة، صعودا أو نزولا.",
        },
        ("ary", "latin"): {
            "prompt": "Ash kat3ni lmkhatir lmaliya?",
            "options": {
                "A": "Daman mrbout b l istitmar",
                "B": "Taman lli kaybqa tabet m3a lwe9t",
                "C": "I7timal belli nnatija lli kayna tkhtalef 3la lli kan mtwe99e3",
                "D": "Iltizam qanouni mefroud 3la lmostatmirin",
            },
            "explanation": "Lmkhatir lmaliya howa i7timal belli nnatija l7a9i9iya dyal l istitmar tkhtalef 3la lli kan mtwe99e3, l fou9 wla l te7t.",
        },
        ("ary", "arabic"): {
            "prompt": "أشنو كتعني المخاطر المالية؟",
            "options": {
                "A": "ضمانة مربوطة بالاستثمار",
                "B": "ثمن لي كيبقى ثابت مع الوقت",
                "C": "احتمال بلي النتيجة لي كاينة تختلف على لي كان متوقع",
                "D": "التزام قانوني مفروض على المستثمرين",
            },
            "explanation": "المخاطر المالية هي احتمال بلي النتيجة الحقيقية ديال الاستثمار تختلف على لي كان متوقع، لفوق ولا لتحت.",
        },
    },
    "beginner-7": {
        ("en", "latin"): {
            "prompt": "What does return measure?",
            "options": {
                "A": "The result of an investment over a given period",
                "B": "The number of shares held in a portfolio",
                "C": "The set of rules that govern the market",
                "D": "Only how easily an asset can be sold",
            },
            "explanation": "Return measures what an investment produced over a defined period, which is why the period must always be stated alongside it.",
        },
        ("ar", "arabic"): {
            "prompt": "ماذا يقيس العائد؟",
            "options": {
                "A": "نتيجة استثمار خلال فترة زمنية محددة",
                "B": "عدد الأسهم الموجودة في المحفظة",
                "C": "مجموعة القواعد التي تنظم السوق",
                "D": "سهولة بيع الأصل فقط",
            },
            "explanation": "يقيس العائد ما حققه الاستثمار خلال فترة محددة، ولهذا يجب ذكر الفترة الزمنية معه دائما.",
        },
        ("ary", "latin"): {
            "prompt": "Ash kay9is rrbe7 dyal l istitmar?",
            "options": {
                "A": "Nnatija dyal chi tawdif 3la modda m7addda",
                "B": "3adad dyal l as-hom lli f lportefeuille",
                "C": "Majmou3 l qawa3id lli kaynadmo sou9",
                "D": "Ghir soulat lbi3 dyal l assel",
            },
            "explanation": "Rrbe7 kay9is chnou 7e99e9 l istitmar f modda m7addda, w 3la haqach khass dima tdkor lmodda m3ah.",
        },
        ("ary", "arabic"): {
            "prompt": "أشنو كيقيس الربح ديال الاستثمار؟",
            "options": {
                "A": "النتيجة ديال شي توظيف على مدة محددة",
                "B": "عدد ديال الأسهم لي فالمحفظة",
                "C": "مجموع القواعد لي كينظمو السوق",
                "D": "غير سهولة البيع ديال الأصل",
            },
            "explanation": "الربح كيقيس شنو حقق الاستثمار فمدة محددة، وعلاحقاش خاص ديما تذكر المدة معاه.",
        },
    },
    "beginner-8": {
        ("en", "latin"): {
            "prompt": "What is a basic purpose of spreading an investment across assets?",
            "options": {
                "A": "To guarantee the performance of one chosen security",
                "B": "To avoid having to follow market rules",
                "C": "To make any loss impossible",
                "D": "To spread exposure across several different assets",
            },
            "explanation": "Basic diversification spreads money across several assets so the portfolio does not depend on the fate of a single position.",
        },
        ("ar", "arabic"): {
            "prompt": "كيف يساعد توزيع الاستثمار على عدة أصول؟",
            "options": {
                "A": "بضمان أداء ورقة مالية واحدة مختارة",
                "B": "بتفادي الالتزام بقواعد السوق",
                "C": "بجعل أي خسارة مستحيلة",
                "D": "بتوزيع الانكشاف على عدة أصول مختلفة",
            },
            "explanation": "يوزع التنويع الأساسي الأموال على عدة أصول حتى لا تتوقف المحفظة على مصير مركز واحد.",
        },
        ("ary", "latin"): {
            "prompt": "Kifach kay3awen twzi3 l istitmar 3la bezzaf d l asol?",
            "options": {
                "A": "B daman l ada2 dyal wa7d lwra9a mkhtara",
                "B": "B tafadi l iltizam b qawa3id sou9",
                "C": "B jji3l ay khsara mosta7ila",
                "D": "B twzi3 lflous 3la bezzaf d l asol lmokhtalfa",
            },
            "explanation": "Tanwi3 l assassi kaywezze3 lflous 3la bezzaf d l asol 7it lportefeuille may bqach mrbout b masir dyal wa7d lmarkaz bou7do.",
        },
        ("ary", "arabic"): {
            "prompt": "كيفاش كيعاون توزيع الاستثمار على بزاف ديال الأصول؟",
            "options": {
                "A": "بضمان الأداء ديال واحد الورقة مختارة",
                "B": "بتفادي الالتزام بقواعد السوق",
                "C": "بجعل أي خسارة مستحيلة",
                "D": "بتوزيع الفلوس على بزاف ديال الأصول المختلفة",
            },
            "explanation": "التنويع الأساسي كيوزع الفلوس على بزاف ديال الأصول حيت المحفظة مابقاش مربوطة بمصير واحد المركز بوحدو.",
        },
    },
    "beginner-9": {
        ("en", "latin"): {
            "prompt": "Why are market rules useful?",
            "options": {
                "A": "Because they remove risk from investing",
                "B": "Because they support an orderly and transparent market",
                "C": "Because they guarantee the price of every security",
                "D": "Because they replace the need for information",
            },
            "explanation": "Market rules organise how orders, disclosure and settlement work so that participants operate on a transparent and even basis; they do not remove risk.",
        },
        ("ar", "arabic"): {
            "prompt": "لماذا تعد قواعد السوق مفيدة؟",
            "options": {
                "A": "لأنها تزيل المخاطر عن الاستثمار",
                "B": "لأنها تدعم سوقا منظمة وشفافة",
                "C": "لأنها تضمن سعر كل ورقة مالية",
                "D": "لأنها تغني عن الحاجة إلى المعلومة",
            },
            "explanation": "تنظم قواعد السوق سير الأوامر والإفصاح والتسوية حتى يتعامل المشاركون في إطار شفاف ومتكافئ، وهي لا تلغي المخاطر.",
        },
        ("ary", "latin"): {
            "prompt": "3lash qawa3id sou9 mohimma?",
            "options": {
                "A": "7it kaymse7 lmkhatir 3la l istitmar",
                "B": "7it kat3awen bach sou9 tkoun mnadma w chaffafa",
                "C": "7it kaddmen taman dyal kol wra9a maliya",
                "D": "7it kat3awad l7aja l lma3louma",
            },
            "explanation": "Qawa3id sou9 kaynadmo l awamir w l ifsa7 w tteswiya bach lmocharikin ykhedmo f itar chaffaf w mtkafi2, walakin ma kaymse7ouch lmkhatir.",
        },
        ("ary", "arabic"): {
            "prompt": "علاش قواعد السوق مهمة؟",
            "options": {
                "A": "حيت كتمحي المخاطر على الاستثمار",
                "B": "حيت كتعاون باش السوق تكون منظمة وشفافة",
                "C": "حيت كتضمن الثمن ديال كل ورقة مالية",
                "D": "حيت كتعوض الحاجة للمعلومة",
            },
            "explanation": "قواعد السوق كينظمو الأوامر والإفصاح والتسوية باش المشاركين يخدمو ف إطار شفاف ومتكافئ، ولكن ماكيمحيوش المخاطر.",
        },
    },
    "beginner-10": {
        ("en", "latin"): {
            "prompt": "What does issuing new securities mean?",
            "options": {
                "A": "A resale of existing securities between investors",
                "B": "The purchase of an insurance contract",
                "C": "An initial offer of newly created securities by the issuer",
                "D": "The payment of a dividend to shareholders",
            },
            "explanation": "Issuing means the issuer creates and offers new securities for the first time; trades between investors afterwards are a different, secondary operation.",
        },
        ("ar", "arabic"): {
            "prompt": "ماذا يعني إصدار أوراق مالية جديدة؟",
            "options": {
                "A": "إعادة بيع أوراق قائمة بين المستثمرين",
                "B": "شراء عقد تأمين",
                "C": "عرضا أوليا لأوراق مالية جديدة من طرف المصدر",
                "D": "دفع أرباح للمساهمين",
            },
            "explanation": "يعني الإصدار أن الجهة المصدرة تنشئ أوراقا جديدة وتعرضها لأول مرة، أما التبادل اللاحق بين المستثمرين فعملية ثانوية مختلفة.",
        },
        ("ary", "latin"): {
            "prompt": "Ash kay3ni tesdir dyal wra9 maliya jdida?",
            "options": {
                "A": "I3adat lbi3 dyal wra9 lli deja kaynin bin lmostatmirin",
                "B": "Chra dyal 3a9d ta2min",
                "C": "3ard awwali dyal wra9 maliya jdida mn 3nd lmosder",
                "D": "Khlas dyal arba7 l lmossahimin",
            },
            "explanation": "Tesdir kay3ni belli lmosder kaysne3 wra9 jdida w kay3erdhom l lewwel merra, ama tbadol lli kayji mn be3d bin lmostatmirin dakchi 3amaliya tanawiya.",
        },
        ("ary", "arabic"): {
            "prompt": "أشنو كيعني إصدار أوراق مالية جديدة؟",
            "options": {
                "A": "إعادة البيع ديال أوراق لي ديجا كاينين بين المستثمرين",
                "B": "شرا ديال عقد تأمين",
                "C": "عرض أولي ديال أوراق مالية جديدة من عند المصدر",
                "D": "خلاص ديال الأرباح للمساهمين",
            },
            "explanation": "الإصدار كيعني بلي المصدر كيصنع أوراق جديدة وكيعرضهم لأول مرة، أما التبادل لي كيجي من بعد بين المستثمرين داكشي عملية ثانوية.",
        },
    },
    "intermediate-1": {
        ("en", "latin"): {
            "prompt": "Why do a share and a bond not give the same rights?",
            "options": {
                "A": "One is linked to the company's capital, the other to a claim on the issuer",
                "B": "They are identical instruments with different names",
                "C": "Both of them guarantee a gain to the holder",
                "D": "Neither of them has an identified issuer",
            },
            "explanation": "A shareholder owns part of the capital and bears the company's fortunes, while a bondholder is a creditor with a contractual claim; the two positions carry different rights.",
        },
        ("ar", "arabic"): {
            "prompt": "لماذا لا يمنح السهم والسند الحقوق نفسها؟",
            "options": {
                "A": "أحدهما مرتبط برأس المال والآخر بدين على المصدر",
                "B": "هما أداة واحدة باسمين مختلفين",
                "C": "كلاهما يضمن ربحا لحامله",
                "D": "لا توجد لأي منهما جهة مصدرة",
            },
            "explanation": "يملك المساهم جزءا من رأس المال ويتحمل نتائج الشركة، أما حامل السند فدائن له حق تعاقدي، ولذلك تختلف حقوق الطرفين.",
        },
        ("ary", "latin"): {
            "prompt": "3lash saham w sanad ma kay3tiwch nefs l7o9o9?",
            "options": {
                "A": "Wa7ed mrbout b ras lmal w lakhor b din 3la lmosder",
                "B": "Homa nefs l2ada b joj smiyat",
                "C": "Bjouj kaydemno rbe7 l moulahom",
                "D": "Ta wa7ed fihom ma 3ando jiha mosdira",
            },
            "explanation": "Lmossahim kaymlek jouz2 mn ras lmal w kaydduz m3a nata2ij charika, ama moul sanad howa dayn 3ando 7e99 ta3a9odi, w 3la haqach l7o9o9 mkhtalfa.",
        },
        ("ary", "arabic"): {
            "prompt": "علاش السهم والسند ماشي بحال بحال فالحقوق؟",
            "options": {
                "A": "واحد مربوط برأس المال والآخر بدين على المصدر",
                "B": "هوما نفس الأداة بجوج سميات",
                "C": "بجوج كيضمنو ربح لمولاهم",
                "D": "حتى واحد فيهم ماعندو جهة مصدرة",
            },
            "explanation": "المساهم كيملك جزء من رأس المال وكيدوز مع نتائج الشركة، أما مول السند فهو دائن عندو حق تعاقدي، وعلاحقاش الحقوق مختلفة.",
        },
    },
    "intermediate-2": {
        ("en", "latin"): {
            "prompt": "What is the general principle of an OPCVM collective fund?",
            "options": {
                "A": "A security traded outside any rules",
                "B": "A return guaranteed to every subscriber",
                "C": "A personal loan granted to each investor",
                "D": "Capital pooled from investors and managed collectively under defined rules",
            },
            "explanation": "An OPCVM pools money from many investors and has it managed collectively according to a defined policy and regulatory framework; the value of a unit still varies.",
        },
        ("ar", "arabic"): {
            "prompt": "ما المبدأ العام لصندوق الاستثمار الجماعي؟",
            "options": {
                "A": "ورقة مالية تتداول خارج أي قواعد",
                "B": "عائدا مضمونا لكل مكتتب",
                "C": "قرضا شخصيا يمنح لكل مستثمر",
                "D": "أموالا مجمعة من المستثمرين تدار جماعيا وفق قواعد محددة",
            },
            "explanation": "يجمع صندوق الاستثمار الجماعي أموال عدة مستثمرين ويديرها وفق سياسة محددة وإطار تنظيمي، وتبقى قيمة الحصة متغيرة.",
        },
        ("ary", "latin"): {
            "prompt": "Chno lmabda2 l3am dyal OPCVM?",
            "options": {
                "A": "Wra9a maliya kattbadel barra 3la ay qawa3id",
                "B": "Rbe7 mdmoun l kol wa7ed lli ktetb",
                "C": "Selfa chakhsiya kat3ta l kol mostatmir",
                "D": "Flous mejmou3a mn lmostatmirin w mdabbra jama3iyan b qawa3id m7addda",
            },
            "explanation": "OPCVM kayjme3 flous d bezzaf d lmostatmirin w kaydabber 3lihom jama3iyan b siyasa m7addda w itar tandimi, w l9ima dyal l7essa kadduz w tji.",
        },
        ("ary", "arabic"): {
            "prompt": "شنو المبدأ العام ديال صندوق الاستثمار الجماعي؟",
            "options": {
                "A": "ورقة مالية كتتبادل برا على أي قواعد",
                "B": "ربح مضمون لكل واحد لي اكتتب",
                "C": "سلفة شخصية كتعطى لكل مستثمر",
                "D": "فلوس مجموعة من المستثمرين ومدبرة جماعيا بقواعد محددة",
            },
            "explanation": "الصندوق الجماعي كيجمع فلوس ديال بزاف ديال المستثمرين وكيدبر عليهم جماعيا بسياسة محددة وإطار تنظيمي، والقيمة ديال الحصة كتدوز وتجي.",
        },
    },
    "intermediate-3": {
        ("en", "latin"): {
            "prompt": "What limit of diversification should be kept in mind?",
            "options": {
                "A": "It guarantees a gain once enough assets are held",
                "B": "It does not remove every risk from a portfolio",
                "C": "It makes any loss impossible",
                "D": "It replaces the need for financial analysis",
            },
            "explanation": "Diversification reduces risks specific to one issuer, but market-wide risk remains, so it lowers exposure without removing it.",
        },
        ("ar", "arabic"): {
            "prompt": "ما الحد الذي ينبغي تذكره بخصوص التنويع؟",
            "options": {
                "A": "يضمن الربح بمجرد امتلاك عدد كاف من الأصول",
                "B": "لا يزيل كل المخاطر من المحفظة",
                "C": "يجعل أي خسارة مستحيلة",
                "D": "يغني عن التحليل المالي",
            },
            "explanation": "يقلل التنويع المخاطر الخاصة بجهة مصدرة بعينها، لكن مخاطر السوق ككل تبقى قائمة، فهو يخفف الانكشاف دون أن يلغيه.",
        },
        ("ary", "latin"): {
            "prompt": "Ash howa l7ed dyal tanwi3 lli khass ntfekkroh?",
            "options": {
                "A": "Kaydmen rrbe7 ila 3andek bezzaf d l asol",
                "B": "Ma kaymse7ch kol lmkhatir mn lportefeuille",
                "C": "Kaykhelli ay khsara mosta7ila",
                "D": "Kat3awad l7aja l ttahlil lmali",
            },
            "explanation": "Tanwi3 kayn9es lmkhatir lkhassa b chi mosder b3ino, walakin lmkhatir dyal sou9 kamla kabqa, ya3ni kayn9es l inkichaf machi kaymse7o.",
        },
        ("ary", "arabic"): {
            "prompt": "أشنو هو الحد ديال التنويع لي خاص نتفكروه؟",
            "options": {
                "A": "كيضمن الربح إلا عندك بزاف ديال الأصول",
                "B": "ماكيمحيش كل المخاطر من المحفظة",
                "C": "كيخلي أي خسارة مستحيلة",
                "D": "كيعوض الحاجة للتحليل المالي",
            },
            "explanation": "التنويع كينقص المخاطر الخاصة بشي مصدر بعينو، ولكن مخاطر السوق كاملة كتبقى، يعني كينقص الانكشاف ماكيمحيهش.",
        },
    },
    "intermediate-4": {
        ("en", "latin"): {
            "prompt": "What does a limit order set?",
            "options": {
                "A": "The dividend that the company will pay",
                "B": "The composition of a market index",
                "C": "A price limit beyond which the order must not be executed",
                "D": "A tax deadline for the investor",
            },
            "explanation": "A limit order fixes the worst acceptable execution price, so it protects the price but does not guarantee that the order will be filled.",
        },
        ("ar", "arabic"): {
            "prompt": "ماذا يحدد الأمر بسعر محدد؟",
            "options": {
                "A": "الأرباح التي ستوزعها الشركة",
                "B": "تركيبة مؤشر السوق",
                "C": "حدا سعريا لا يجوز تجاوزه عند التنفيذ",
                "D": "أجلا ضريبيا يخص المستثمر",
            },
            "explanation": "يحدد الأمر بسعر محدد أسوأ سعر مقبول للتنفيذ، فهو يحمي السعر لكنه لا يضمن تنفيذ الأمر.",
        },
        ("ary", "latin"): {
            "prompt": "Ash kay7dded l amr b taman m7dood?",
            "options": {
                "A": "L arba7 lli ghadi twezze3 charika",
                "B": "Tarkiba dyal mo2achir sou9",
                "C": "7ed d taman lli ma khassoch ytjawez f tenfid",
                "D": "Ajal daribi lli khass lmostatmir",
            },
            "explanation": "L amr b taman m7dood kay7dded 9be7 taman m9boul l tenfid, ya3ni kay7mi taman walakin ma kaydmench belli l amr ghadi ytnaffed.",
        },
        ("ary", "arabic"): {
            "prompt": "أشنو كيحدد الأمر بثمن محدود؟",
            "options": {
                "A": "الأرباح لي غادي توزع الشركة",
                "B": "التركيبة ديال مؤشر السوق",
                "C": "حد ديال الثمن لي ماخاصوش يتجاوز فالتنفيذ",
                "D": "أجل ضريبي لي خاص المستثمر",
            },
            "explanation": "الأمر بثمن محدود كيحدد قبح ثمن مقبول للتنفيذ، يعني كيحمي الثمن ولكن ماكيضمنش بلي الأمر غادي يتنفذ.",
        },
    },
    "intermediate-5": {
        ("en", "latin"): {
            "prompt": "What happens on the secondary market?",
            "options": {
                "A": "Securities that were already issued are traded between investors",
                "B": "A company always creates brand-new securities",
                "C": "Wages are negotiated and set",
                "D": "Bank loans are guaranteed by the exchange",
            },
            "explanation": "The secondary market is where investors trade securities among themselves after issuance; the issuer receives no new money from those trades.",
        },
        ("ar", "arabic"): {
            "prompt": "ماذا يحدث في السوق الثانوي؟",
            "options": {
                "A": "تتداول أوراق مالية سبق إصدارها بين المستثمرين",
                "B": "تنشئ الشركة دائما أوراقا مالية جديدة",
                "C": "تحدد الأجور ويتفاوض بشأنها",
                "D": "تضمن البورصة القروض البنكية",
            },
            "explanation": "السوق الثانوي هو المكان الذي يتبادل فيه المستثمرون الأوراق المالية بعد إصدارها، ولا تحصل الجهة المصدرة على أموال جديدة من هذه الصفقات.",
        },
        ("ary", "latin"): {
            "prompt": "Ash kaywqe3 f sou9 ttanawi?",
            "options": {
                "A": "Wra9 maliya lli deja tsedro kaytbadlo bin lmostatmirin",
                "B": "Charika dima katsne3 wra9 maliya jdida",
                "C": "Lujour kaytnaqcho w kayt7eddo",
                "D": "Lborsa kaddmen l 9rod lbankiya",
            },
            "explanation": "Sou9 ttanawi howa fin lmostatmirin kaytbadlo lwra9 lmaliya binathom mora ma tsedro, w lmosder ma kaykhod ta flous jdida mn had l3amaliyat.",
        },
        ("ary", "arabic"): {
            "prompt": "أشنو كيوقع فالسوق الثانوي؟",
            "options": {
                "A": "أوراق مالية لي ديجا تصدرو كيتبادلو بين المستثمرين",
                "B": "الشركة ديما كتصنع أوراق مالية جديدة",
                "C": "الأجور كيتناقشو وكيتحددو",
                "D": "البورصة كتضمن القروض البنكية",
            },
            "explanation": "السوق الثانوي هو فين المستثمرين كيتبادلو الأوراق المالية بيناتهم من بعد ماتصدرو، والمصدر ماكياخد حتى فلوس جديدة من هاد العمليات.",
        },
    },
    "intermediate-6": {
        ("en", "latin"): {
            "prompt": "What characterises an initial public offering?",
            "options": {
                "A": "The subscription of an insurance policy",
                "B": "The payment of a dividend to existing shareholders",
                "C": "A private resale between two identified parties",
                "D": "The first admission of a company's securities to trading on a market",
            },
            "explanation": "An IPO is the first admission of a company's securities to trading on a regulated market, which opens them to a wide investor base and to ongoing disclosure duties.",
        },
        ("ar", "arabic"): {
            "prompt": "ما الذي يميز الإدراج الأولي في البورصة؟",
            "options": {
                "A": "الاكتتاب في عقد تأمين",
                "B": "توزيع أرباح على المساهمين الحاليين",
                "C": "إعادة بيع خاصة بين طرفين محددين",
                "D": "الإدراج الأول لأوراق الشركة للتداول في السوق",
            },
            "explanation": "الإدراج الأولي هو أول قبول لأوراق الشركة للتداول في سوق منظمة، مما يفتحها أمام جمهور واسع من المستثمرين ويرتب عليها التزامات إفصاح مستمرة.",
        },
        ("ary", "latin"): {
            "prompt": "Ash kaymayyez l IPO f lborsa?",
            "options": {
                "A": "L iktitab f 3a9d ta2min",
                "B": "Twzi3 arba7 3la lmossahimin lli kaynin",
                "C": "I3adat bi3 khassa bin joj tarafin m3rofin",
                "D": "Awwel idraj dyal wra9 charika bach ttbadel f sou9",
            },
            "explanation": "L IPO howa lewwel qbol dyal wra9 charika bach ttbadel f sou9 mnaddma, w hadchi kayfte7ha 3la jomhour kbir d lmostatmirin w kayjib m3ah wajibat d l ifsa7.",
        },
        ("ary", "arabic"): {
            "prompt": "أشنو كيميز الإدراج الأولي فالبورصة؟",
            "options": {
                "A": "الاكتتاب فعقد تأمين",
                "B": "توزيع أرباح على المساهمين لي كاينين",
                "C": "إعادة بيع خاصة بين جوج أطراف معروفين",
                "D": "أول إدراج ديال أوراق الشركة باش تتبادل فالسوق",
            },
            "explanation": "الإدراج الأولي هو أول قبول ديال أوراق الشركة باش تتبادل فسوق منظمة، وهادشي كيفتحها على جمهور كبير ديال المستثمرين وكيجيب معاه واجبات ديال الإفصاح.",
        },
    },
    "intermediate-7": {
        ("en", "latin"): {
            "prompt": "Why is the investment horizon relevant?",
            "options": {
                "A": "Because a long horizon guarantees a positive return",
                "B": "Because it puts price fluctuations and objectives into context",
                "C": "Because it removes the risks attached to an investment",
                "D": "Because it fixes the future price of the security",
            },
            "explanation": "The horizon says how long the money can stay invested, which is what makes a given level of fluctuation either tolerable or unsuitable for the investor's goal.",
        },
        ("ar", "arabic"): {
            "prompt": "لماذا يعد أفق الاستثمار مهما؟",
            "options": {
                "A": "لأن الأفق الطويل يضمن عائدا إيجابيا",
                "B": "لأنه يضع تقلبات الأسعار والأهداف في سياقها",
                "C": "لأنه يزيل المخاطر المرتبطة بالاستثمار",
                "D": "لأنه يحدد سعر الورقة في المستقبل",
            },
            "explanation": "يحدد الأفق المدة التي يمكن أن تبقى فيها الأموال مستثمرة، وهو ما يجعل مستوى معينا من التقلب مقبولا أو غير مناسب لهدف المستثمر.",
        },
        ("ary", "latin"): {
            "prompt": "3lash of9 l istitmar mohim?",
            "options": {
                "A": "7it l of9 ttwil kaydmen rbe7 ijabi",
                "B": "7it kaydir tqalobat l aswa9 w l ahdaf f siya9hom",
                "C": "7it kaymse7 lmkhatir lli mrbouta b l istitmar",
                "D": "7it kay7dded taman dyal lwra9a f lmosta9bal",
            },
            "explanation": "L of9 kay9oul chhal mn wa9t lflous t9der tb9a mwaddfa, w hada howa lli kaykhelli chi mostawa d tta9allob m9boul wla machi mnaseb l hadaf dyal lmostatmir.",
        },
        ("ary", "arabic"): {
            "prompt": "علاش أفق الاستثمار مهم؟",
            "options": {
                "A": "حيت الأفق الطويل كيضمن ربح إيجابي",
                "B": "حيت كيدير تقلبات الأسواق والأهداف فالسياق ديالهم",
                "C": "حيت كيمحي المخاطر لي مربوطة بالاستثمار",
                "D": "حيت كيحدد ثمن الورقة فالمستقبل",
            },
            "explanation": "الأفق كيقول شحال من وقت الفلوس تقدر تبقى موظفة، وهادا هو لي كيخلي شي مستوى ديال التقلب مقبول ولا ماشي مناسب لهدف المستثمر.",
        },
    },
    "intermediate-8": {
        ("en", "latin"): {
            "prompt": "What is the role of an authorised intermediary?",
            "options": {
                "A": "To guarantee a capital gain to its clients",
                "B": "To modify the laws that govern the market",
                "C": "To carry out and facilitate certain operations within the applicable rules",
                "D": "To replace the market and trade in its place",
            },
            "explanation": "An authorised intermediary is licensed to receive and transmit orders and to carry out certain operations for clients within the applicable rules; it does not promise results.",
        },
        ("ar", "arabic"): {
            "prompt": "ما دور الوسيط المعتمد؟",
            "options": {
                "A": "ضمان تحقيق ربح رأسمالي لعملائه",
                "B": "تعديل القوانين التي تنظم السوق",
                "C": "تنفيذ وتسهيل بعض العمليات في إطار القواعد المعمول بها",
                "D": "تعويض السوق والتداول مكانها",
            },
            "explanation": "الوسيط المعتمد مرخص له بتلقي الأوامر ونقلها وتنفيذ بعض العمليات لفائدة العملاء ضمن القواعد المعمول بها، وهو لا يعد بأي نتيجة.",
        },
        ("ary", "latin"): {
            "prompt": "Chno dour dyal lwasit lm3temed?",
            "options": {
                "A": "Ydmen rbe7 f ras lmal l klianat dyalo",
                "B": "Ybeddel l qawanin lli kaynadmo sou9",
                "C": "Ynaffed w ysahhel chi 3amaliyat f itar l qawa3id lli khedama",
                "D": "Y3awad sou9 w ytbadel f blastha",
            },
            "explanation": "Lwasit lm3temed 3ando rokhsa bach yakhod l awamir w ysiftha w ynaffed chi 3amaliyat l klianat f itar l qawa3id, walakin ma kay3ed b ta natija.",
        },
        ("ary", "arabic"): {
            "prompt": "شنو الدور ديال الوسيط المعتمد؟",
            "options": {
                "A": "يضمن ربح فرأس المال للكليان ديالو",
                "B": "يبدل القوانين لي كينظمو السوق",
                "C": "ينفذ ويسهل شي عمليات ف إطار القواعد لي خدامة",
                "D": "يعوض السوق ويتبادل فبلاصتها",
            },
            "explanation": "الوسيط المعتمد عندو رخصة باش ياخد الأوامر ويصيفطهم وينفذ شي عمليات للكليان ف إطار القواعد، ولكن ماكيوعد بحتى نتيجة.",
        },
    },
    "intermediate-9": {
        ("en", "latin"): {
            "prompt": "What does volatility describe?",
            "options": {
                "A": "The size and frequency of price variations",
                "B": "The portion of capital that is guaranteed",
                "C": "The dividends a company will pay in the future",
                "D": "How long an IPO procedure lasts",
            },
            "explanation": "Volatility measures how widely and how often a price moves; a high volatility means larger swings in both directions, not a predicted direction.",
        },
        ("ar", "arabic"): {
            "prompt": "ماذا يصف التقلب؟",
            "options": {
                "A": "حجم تغيرات الأسعار ووتيرتها",
                "B": "الجزء المضمون من رأس المال",
                "C": "الأرباح التي ستوزعها الشركة مستقبلا",
                "D": "المدة التي تستغرقها عملية الإدراج",
            },
            "explanation": "يقيس التقلب مدى اتساع حركة السعر وتواترها، والتقلب المرتفع يعني تحركات أوسع في الاتجاهين وليس اتجاها متوقعا.",
        },
        ("ary", "latin"): {
            "prompt": "Ash kaywsef tta9allob dyal l aswa9?",
            "options": {
                "A": "7ejm dyal tbeddolat taman w wtirathom",
                "B": "Jouz2 mdmoun mn ras lmal",
                "C": "L arba7 lli ghadi twezze3 charika mn be3d",
                "D": "Lmodda lli katakhod 3amaliyat l idraj",
            },
            "explanation": "Tta9allob kay9is chhal taman kaytharrek w chhal mn merra, w tta9allob l3ali kay3ni 7arakat kbar f jjiha bjouj machi jiha m3rofa.",
        },
        ("ary", "arabic"): {
            "prompt": "أشنو كيوصف التقلب ديال الأسواق؟",
            "options": {
                "A": "الحجم ديال تبدلات الثمن والوتيرة ديالهم",
                "B": "الجزء المضمون من رأس المال",
                "C": "الأرباح لي غادي توزع الشركة من بعد",
                "D": "المدة لي كتاخد عملية الإدراج",
            },
            "explanation": "التقلب كيقيس شحال الثمن كيتحرك وشحال من مرة، والتقلب العالي كيعني حركات كبار فالجيهة بجوج ماشي جيهة معروفة.",
        },
    },
    "intermediate-10": {
        ("en", "latin"): {
            "prompt": "Does a past return guarantee the future return?",
            "options": {
                "A": "Yes, past results always repeat themselves",
                "B": "Yes, but only in the case of a share",
                "C": "Yes, but only when an index is involved",
                "D": "No, past performance does not guarantee future performance",
            },
            "explanation": "Past performance is history: it describes conditions that already occurred and gives no assurance about future results, whatever the instrument.",
        },
        ("ar", "arabic"): {
            "prompt": "هل يضمن الأداء السابق الأداء المستقبلي؟",
            "options": {
                "A": "نعم، فالنتائج السابقة تتكرر دائما",
                "B": "نعم، لكن في حالة السهم فقط",
                "C": "نعم، لكن عندما يتعلق الأمر بمؤشر فقط",
                "D": "لا، فالأداء السابق لا يضمن الأداء المستقبلي",
            },
            "explanation": "الأداء السابق تاريخ مضى: يصف ظروفا وقعت فعلا ولا يقدم أي ضمان بشأن النتائج المقبلة مهما كانت الأداة المالية.",
        },
        ("ary", "latin"): {
            "prompt": "Wach l2ada2 li fat kaydmen lmosta9bal?",
            "options": {
                "A": "Iyeh, nnata2ij l9dima kaytkerro dima",
                "B": "Iyeh, walakin ghir f 7alat saham",
                "C": "Iyeh, walakin ghir mnin kaykon mo2achir",
                "D": "La, l ada2 li fat ma kaydmench l ada2 jjay",
            },
            "explanation": "L ada2 li fat howa tarikh: kaywsef dourouf lli we93o deja w ma kay3ti ta daman 3la nnata2ij jjaya, ay men kant l2ada lmaliya.",
        },
        ("ary", "arabic"): {
            "prompt": "واش الربح القديم كيضمن المستقبل؟",
            "options": {
                "A": "إيه، النتائج القديمة كيتكررو ديما",
                "B": "إيه، ولكن غير فحالة السهم",
                "C": "إيه، ولكن غير منين كيكون مؤشر",
                "D": "لا، الأداء لي فات ماكيضمنش الأداء الجاي",
            },
            "explanation": "الأداء لي فات هو تاريخ: كيوصف ظروف لي وقعو ديجا وماكيعطي حتى ضمانة على النتائج الجاية، أي من كانت الأداة المالية.",
        },
    },
    "advanced-1": {
        ("en", "latin"): {
            "prompt": "What can be an effect of a capital increase?",
            "options": {
                "A": "It can change the capital structure and the relative rights of existing shareholders",
                "B": "It removes the issuer from the market",
                "C": "It guarantees the share price after the operation",
                "D": "It suspends the issuer's disclosure obligations",
            },
            "explanation": "A capital increase creates new shares, so an existing holding may end up representing a smaller proportion of the capital and of the associated rights unless its holder subscribes.",
        },
        ("ar", "arabic"): {
            "prompt": "ما الأثر الذي قد تحدثه الزيادة في رأس المال؟",
            "options": {
                "A": "قد تغير بنية رأس المال والحقوق النسبية للمساهمين الحاليين",
                "B": "تلغي وجود الجهة المصدرة في السوق",
                "C": "تضمن سعر السهم بعد العملية",
                "D": "توقف التزامات الإفصاح على المصدر",
            },
            "explanation": "تنشئ الزيادة في رأس المال أسهما جديدة، فقد تمثل الحصة القائمة نسبة أصغر من رأس المال ومن الحقوق المرتبطة به ما لم يكتتب صاحبها.",
        },
        ("ary", "latin"): {
            "prompt": "Ash momkin ykon ta2tir dyal ziyada f ras lmal?",
            "options": {
                "A": "Momkin tbeddel bniyat ras lmal w l7o9o9 nnisbiya dyal lmossahimin lli kaynin",
                "B": "Katmse7 lmosder mn sou9",
                "C": "Kaddmen taman dyal saham mora l3amaliya",
                "D": "Kat7bes wajibat l ifsa7 3la lmosder",
            },
            "explanation": "Ziyada f ras lmal katsne3 as-hom jdida, ya3ni l7essa lli kayna momkin tbqa katmattel nisba sghira mn ras lmal w mn l7o9o9 ila ma chraych moulha.",
        },
        ("ary", "arabic"): {
            "prompt": "أشنو ممكن يكون التأثير ديال الزيادة فرأس المال؟",
            "options": {
                "A": "ممكن تبدل بنية رأس المال والحقوق النسبية ديال المساهمين لي كاينين",
                "B": "كتمحي المصدر من السوق",
                "C": "كتضمن ثمن السهم من بعد العملية",
                "D": "كتحبس واجبات الإفصاح على المصدر",
            },
            "explanation": "الزيادة فرأس المال كتصنع أسهم جديدة، يعني الحصة لي كاينة ممكن تبقى كتمثل نسبة صغيرة من رأس المال ومن الحقوق إلا ماشراش مولاها.",
        },
    },
    "advanced-2": {
        ("en", "latin"): {
            "prompt": "Why is price setting important in an IPO?",
            "options": {
                "A": "Because it guarantees the return of the subscribers",
                "B": "Because it replaces the legal framework of the operation",
                "C": "Because it brings together supply, demand and the published information",
                "D": "Because it removes the risk carried by the securities",
            },
            "explanation": "The IPO price is where the issuer's offer, investor demand and the information published in the prospectus meet; a badly set price penalises one side or the other.",
        },
        ("ar", "arabic"): {
            "prompt": "لماذا يعد تحديد السعر مهما في عملية الإدراج؟",
            "options": {
                "A": "لأنه يضمن عائد المكتتبين",
                "B": "لأنه يعوض الإطار القانوني للعملية",
                "C": "لأنه يجمع بين العرض والطلب والمعلومات المنشورة",
                "D": "لأنه يزيل المخاطر التي تحملها الأوراق المالية",
            },
            "explanation": "سعر الإدراج هو النقطة التي يلتقي فيها عرض المصدر وطلب المستثمرين والمعلومات المنشورة في وثيقة الإدراج، وسوء تحديده يضر بأحد الطرفين.",
        },
        ("ary", "latin"): {
            "prompt": "3lash t7did taman mohim f l IPO?",
            "options": {
                "A": "7it kaddmen rrbe7 dyal ferra9a lli ktetbo",
                "B": "7it kat3awad l itar l qanouni dyal l3amaliya",
                "C": "7it kajme3 bin l3ard w ttalab w lma3loumat lli tnachro",
                "D": "7it kaymse7 lmkhatir lli fihom lwra9 lmaliya",
            },
            "explanation": "Taman dyal l IPO howa nno9ta fin kaytla9a l3ard dyal lmosder m3a ttalab dyal lmostatmirin m3a lma3loumat lli f wat9a d l idraj, w ila tt7edded ghalet kaydor b chi jiha.",
        },
        ("ary", "arabic"): {
            "prompt": "علاش تحديد الثمن مهم فالإدراج؟",
            "options": {
                "A": "حيت كيضمن الربح ديال لي اكتتبو",
                "B": "حيت كيعوض الإطار القانوني ديال العملية",
                "C": "حيت كيجمع بين العرض والطلب والمعلومات لي تنشرو",
                "D": "حيت كيمحي المخاطر لي فيهم الأوراق المالية",
            },
            "explanation": "الثمن ديال الإدراج هو النقطة فين كيتلاقى العرض ديال المصدر مع الطلب ديال المستثمرين مع المعلومات لي فوثيقة الإدراج، وإلا تحدد غالط كيضر بشي جيهة.",
        },
    },
    "advanced-3": {
        ("en", "latin"): {
            "prompt": "What is periodic issuer disclosure for?",
            "options": {
                "A": "To let investors follow the issuer's situation and its risks over time",
                "B": "To guarantee that the issuer will make a profit",
                "C": "To set the price of every listed security",
                "D": "To replace the statutory audit of the accounts",
            },
            "explanation": "Periodic disclosure gives investors regular, comparable information on the issuer's activity, results and risks so they can update their assessment between two operations.",
        },
        ("ar", "arabic"): {
            "prompt": "ما الغرض من المعلومات الدورية للمصدر؟",
            "options": {
                "A": "تمكين المستثمرين من متابعة وضعية المصدر ومخاطره عبر الزمن",
                "B": "ضمان تحقيق المصدر لأرباح",
                "C": "تحديد أسعار جميع الأوراق المالية المدرجة",
                "D": "تعويض التدقيق القانوني للحسابات",
            },
            "explanation": "تقدم المعلومات الدورية للمستثمرين بيانات منتظمة وقابلة للمقارنة عن نشاط المصدر ونتائجه ومخاطره حتى يحدثوا تقييمهم بين عملية وأخرى.",
        },
        ("ary", "latin"): {
            "prompt": "Chno l fayda dyal lma3loumat ddawriya dyal lmosder?",
            "options": {
                "A": "Tkhelli lmostatmirin ytab3o wad3iyat lmosder w lmkhatir dyalo m3a lwe9t",
                "B": "Tdmen belli lmosder ghadi yrbe7",
                "C": "T7edded l atmina dyal ga3 lwra9 lmodraja",
                "D": "T3awad ttad9i9 l qanouni dyal l7issabat",
            },
            "explanation": "Lma3loumat ddawriya kat3ti l lmostatmirin mo3tayat mnaddma w qabla l lmoqarana 3la nachat lmosder w nata2ijo w lmkhatir dyalo bach yjeddo ttaqyim dyalhom.",
        },
        ("ary", "arabic"): {
            "prompt": "شنو الفايدة ديال المعلومات الدورية ديال المصدر؟",
            "options": {
                "A": "تخلي المستثمرين يتبعو وضعية المصدر والمخاطر ديالو مع الوقت",
                "B": "تضمن بلي المصدر غادي يربح",
                "C": "تحدد الأثمنة ديال كاع الأوراق المدرجة",
                "D": "تعوض التدقيق القانوني ديال الحسابات",
            },
            "explanation": "المعلومات الدورية كتعطي للمستثمرين معطيات منظمة وقابلة للمقارنة على نشاط المصدر والنتائج والمخاطر ديالو باش يجددو التقييم ديالهم.",
        },
    },
    "advanced-4": {
        ("en", "latin"): {
            "prompt": "What does the structure of a market cover?",
            "options": {
                "A": "The level of wages paid by listed companies",
                "B": "A dividend guaranteed to every shareholder",
                "C": "The future profits of the listed issuers",
                "D": "The rules on access, trading and transparency",
            },
            "explanation": "Market structure describes who may access the market, how orders are matched and what must be disclosed; these rules shape liquidity and price formation.",
        },
        ("ar", "arabic"): {
            "prompt": "ماذا تشمل بنية السوق؟",
            "options": {
                "A": "مستوى الأجور في الشركات المدرجة",
                "B": "أرباحا مضمونة لكل مساهم",
                "C": "الأرباح المستقبلية للمصدرين المدرجين",
                "D": "قواعد الولوج والتداول والشفافية",
            },
            "explanation": "تصف بنية السوق من يحق له الولوج وكيفية مقابلة الأوامر وما يجب الإفصاح عنه، وهذه القواعد تؤثر في السيولة وفي تكون الأسعار.",
        },
        ("ary", "latin"): {
            "prompt": "Ash katchmel bniyat sou9?",
            "options": {
                "A": "Mostawa lujour f charikat lmodraja",
                "B": "Arba7 mdmouna l kol mossahim",
                "C": "L arba7 jjaya dyal lmosderin lmodrajin",
                "D": "Qawa3id dyal ddokhoul w tbadol w chaffafiya",
            },
            "explanation": "Bniyat sou9 katwsef chkoun 9der ydkhol w kifach kaytla9aw l awamir w chnou khass ytnchar, w had l qawa3id kat2ttar f ssiyoula w f takwin l atmina.",
        },
        ("ary", "arabic"): {
            "prompt": "أشنو كتشمل بنية السوق؟",
            "options": {
                "A": "مستوى الأجور فالشركات المدرجة",
                "B": "أرباح مضمونة لكل مساهم",
                "C": "الأرباح الجاية ديال المصدرين المدرجين",
                "D": "قواعد الدخول والتبادل والشفافية",
            },
            "explanation": "بنية السوق كتوصف شكون قدر يدخل وكيفاش كيتلاقاو الأوامر وشنو خاص يتنشر، وهاد القواعد كيأثرو فالسيولة وفتكوين الأثمنة.",
        },
    },
    "advanced-5": {
        ("en", "latin"): {
            "prompt": "What does liquidity risk mean?",
            "options": {
                "A": "A return that is guaranteed to the holder",
                "B": "The possible difficulty of selling quickly without a significant price impact",
                "C": "The procedure of an initial public offering",
                "D": "The distribution of a dividend to shareholders",
            },
            "explanation": "Liquidity risk is the risk that a position cannot be sold quickly at a price close to the last quoted one, which typically shows up on thinly traded securities.",
        },
        ("ar", "arabic"): {
            "prompt": "ماذا تعني مخاطر السيولة؟",
            "options": {
                "A": "عائدا مضمونا لحامل الورقة",
                "B": "صعوبة محتملة في البيع بسرعة دون أثر كبير على السعر",
                "C": "مسطرة الإدراج الأولي في البورصة",
                "D": "توزيع أرباح على المساهمين",
            },
            "explanation": "مخاطر السيولة هي احتمال تعذر بيع المركز بسرعة بسعر قريب من آخر سعر معلن، وتظهر عادة في الأوراق قليلة التداول.",
        },
        ("ary", "latin"): {
            "prompt": "Ash kat3ni mkhatir siyoula?",
            "options": {
                "A": "Rbe7 mdmoun l moul lwra9a",
                "B": "So3oba momkina bach tbi3 dghya bla ma ytharrek taman bezzaf",
                "C": "Mastarat l idraj l awwali f lborsa",
                "D": "Twzi3 arba7 3la lmossahimin",
            },
            "explanation": "Mkhatir siyoula howa i7timal belli ma t9derch tbi3 lmarkaz dghya b taman 9rib mn akhir taman m3lan, w hadchi kaybane bezzaf f lwra9 lli ma kaytbadloch bezzaf.",
        },
        ("ary", "arabic"): {
            "prompt": "أشنو كتعني مخاطر السيولة؟",
            "options": {
                "A": "ربح مضمون لمول الورقة",
                "B": "صعوبة ممكنة باش تبيع دغيا بلا مايتحرك الثمن بزاف",
                "C": "مسطرة الإدراج الأولي فالبورصة",
                "D": "توزيع أرباح على المساهمين",
            },
            "explanation": "مخاطر السيولة هي احتمال بلي ماتقدرش تبيع المركز دغيا بثمن قريب من آخر ثمن معلن، وهادشي كيبان بزاف فالأوراق لي ماكيتبادلوش بزاف.",
        },
    },
    "advanced-6": {
        ("en", "latin"): {
            "prompt": "What is a fund's net asset value used for?",
            "options": {
                "A": "To set the salaries of the management company",
                "B": "To guarantee the return paid to unit holders",
                "C": "To value one unit from the fund's assets under its valuation rules",
                "D": "To remove the volatility of the fund's portfolio",
            },
            "explanation": "The net asset value divides the fund's assets, valued under its own rules, by the number of units, giving the reference price at which units are subscribed or redeemed.",
        },
        ("ar", "arabic"): {
            "prompt": "ما الغرض من القيمة الصافية لأصول الصندوق؟",
            "options": {
                "A": "تحديد أجور شركة التدبير",
                "B": "ضمان العائد الذي يدفع لحاملي الحصص",
                "C": "تقييم الحصة انطلاقا من أصول الصندوق وفق قواعد تقييمه",
                "D": "إزالة تقلبات محفظة الصندوق",
            },
            "explanation": "تقسم القيمة الصافية أصول الصندوق المقيمة وفق قواعده على عدد الحصص، فتعطي السعر المرجعي الذي تكتتب أو تسترد به الحصص.",
        },
        ("ary", "latin"): {
            "prompt": "Chno l fayda dyal l9ima ssafiya dyal sandou9?",
            "options": {
                "A": "T7edded lujour dyal charikat ttadbir",
                "B": "Tdmen rrbe7 lli kaytkhalles l mwalin l7ossas",
                "C": "Tqiyyem l7essa mn l asol dyal sandou9 b qawa3id ttaqyim dyalo",
                "D": "Tmse7 tta9allob dyal portefeuille dyal sandou9",
            },
            "explanation": "L9ima ssafiya kat9sem l asol dyal sandou9 lli mqiyma b qawa3ido 3la 3adad l7ossas, w kat3ti taman lmarje3i lli bih kaytchraw wla kaytraddo l7ossas.",
        },
        ("ary", "arabic"): {
            "prompt": "شنو الفايدة ديال القيمة الصافية ديال الصندوق؟",
            "options": {
                "A": "كتحدد الأجور ديال شركة التدبير",
                "B": "كتضمن الربح لي كيتخلص لموالين الحصص",
                "C": "كتقيم الحصة من الأصول ديال الصندوق بقواعد التقييم ديالو",
                "D": "كتمحي التقلب ديال المحفظة ديال الصندوق",
            },
            "explanation": "القيمة الصافية كتقسم الأصول ديال الصندوق لي مقيمة بقواعدو على عدد الحصص، وكتعطي الثمن المرجعي لي بيه كيتشراو ولا كيتردو الحصص.",
        },
    },
    "advanced-7": {
        ("en", "latin"): {
            "prompt": "What trade-off does a market order involve?",
            "options": {
                "A": "It favours execution speed without guaranteeing the exact price obtained",
                "B": "It guarantees the exact price at which the trade will be done",
                "C": "It creates a new company on the market",
                "D": "It prevents the holder from ever selling the security",
            },
            "explanation": "A market order is executed against the best prices available, so it maximises the chance of being filled while leaving the final price uncertain, especially on a thin order book.",
        },
        ("ar", "arabic"): {
            "prompt": "ما المفاضلة التي ينطوي عليها أمر السوق؟",
            "options": {
                "A": "يفضل سرعة التنفيذ دون ضمان السعر الذي سيتم به",
                "B": "يضمن بالضبط السعر الذي ستنفذ به الصفقة",
                "C": "ينشئ شركة جديدة في السوق",
                "D": "يمنع حامل الورقة من بيعها",
            },
            "explanation": "ينفذ أمر السوق مقابل أفضل الأسعار المتاحة، فيرفع فرص التنفيذ لكنه يترك السعر النهائي غير مؤكد، خاصة عند ضعف دفتر الأوامر.",
        },
        ("ary", "latin"): {
            "prompt": "Ash howa ttanazol lli fih amr sou9?",
            "options": {
                "A": "Kayfeddel sor3at tenfid bla ma ydmen taman b dde9",
                "B": "Kaydmen taman lli ghadi ytnaffed bih b dde9",
                "C": "Kaysne3 charika jdida f sou9",
                "D": "Kayemne3 moul lwra9a bach ybi3ha",
            },
            "explanation": "Amr sou9 kaytnaffed b a7san l atmina lli kaynin, ya3ni kayzid f 7ozoz tenfid walakin kaykhelli taman nniha2i machi m2ekked, khassatan ila kan daftar l awamir khawi.",
        },
        ("ary", "arabic"): {
            "prompt": "أشنو هو التنازل لي فيه أمر السوق؟",
            "options": {
                "A": "كيفضل سرعة التنفيذ بلا مايضمن الثمن بالدقة",
                "B": "كيضمن الثمن لي غادي يتنفذ بيه بالدقة",
                "C": "كيصنع شركة جديدة فالسوق",
                "D": "كيمنع مول الورقة باش يبيعها",
            },
            "explanation": "أمر السوق كيتنفذ بأحسن الأثمنة لي كاينين، يعني كيزيد فحظوظ التنفيذ ولكن كيخلي الثمن النهائي ماشي مؤكد، خصوصا إلا كان دفتر الأوامر خاوي.",
        },
    },
    "advanced-8": {
        ("en", "latin"): {
            "prompt": "Why are the roles of market participants kept separate?",
            "options": {
                "A": "To guarantee a gain to every participant",
                "B": "To free participants from the market rules",
                "C": "To let a single participant set all the prices",
                "D": "To clarify responsibilities and limit certain conflicts of interest",
            },
            "explanation": "Separating roles such as management, custody and control means the same party does not both take decisions and check them, which limits conflicts of interest.",
        },
        ("ar", "arabic"): {
            "prompt": "لماذا يفصل بين أدوار المشاركين في السوق؟",
            "options": {
                "A": "لضمان ربح لكل مشارك",
                "B": "لإعفاء المشاركين من قواعد السوق",
                "C": "لتمكين مشارك واحد من تحديد كل الأسعار",
                "D": "لتوضيح المسؤوليات والحد من بعض تضارب المصالح",
            },
            "explanation": "يعني فصل أدوار التدبير والحفظ والمراقبة ألا يجمع طرف واحد بين اتخاذ القرار ومراقبته، وهو ما يحد من تضارب المصالح.",
        },
        ("ary", "latin"): {
            "prompt": "3lash kayfer9o adwar lmocharikin f sou9?",
            "options": {
                "A": "Bach ydemno rbe7 l kol mocharik",
                "B": "Bach y3fiw lmocharikin mn qawa3id sou9",
                "C": "Bach mocharik wa7ed y7edded ga3 l atmina",
                "D": "Bach ywde7o lmas2ouliyat w yn9so chi tadarob f lmasali7",
            },
            "explanation": "Tefri9 l adwar bin ttadbir w l7ifd w lmoraqaba kay3ni belli ta jiha ma katakhod l9rar w kat9ebbo b nefsha, w hadchi kayn9es tadarob lmasali7.",
        },
        ("ary", "arabic"): {
            "prompt": "علاش كيفرقو أدوار المشاركين فالسوق؟",
            "options": {
                "A": "باش يضمنو ربح لكل مشارك",
                "B": "باش يعفيو المشاركين من قواعد السوق",
                "C": "باش مشارك واحد يحدد كاع الأثمنة",
                "D": "باش يوضحو المسؤوليات وينقصو شي تضارب فالمصالح",
            },
            "explanation": "تفريق الأدوار بين التدبير والحفظ والمراقبة كيعني بلي حتى جيهة ماكتاخد القرار وكتراقبو بنفسها، وهادشي كينقص تضارب المصالح.",
        },
    },
    "advanced-9": {
        ("en", "latin"): {
            "prompt": "What does a careful financial analysis rely on?",
            "options": {
                "A": "On the advertising published about the security",
                "B": "On relevant, verifiable information and an awareness of its limits",
                "C": "On a promise of performance made by a third party",
                "D": "On a single price observed on one day",
            },
            "explanation": "A careful analysis uses relevant and verifiable information, and states what that information does not cover, rather than resting on one figure or one claim.",
        },
        ("ar", "arabic"): {
            "prompt": "على ماذا يقوم التحليل المالي الحذر؟",
            "options": {
                "A": "على الإشهار المنشور حول الورقة المالية",
                "B": "على معلومات وجيهة وقابلة للتحقق مع إدراك حدودها",
                "C": "على وعد بالأداء يقدمه طرف ثالث",
                "D": "على سعر واحد لوحظ في يوم واحد",
            },
            "explanation": "يعتمد التحليل الحذر على معلومات وجيهة وقابلة للتحقق ويبين ما لا تغطيه هذه المعلومات، بدل الاكتفاء برقم واحد أو بادعاء واحد.",
        },
        ("ary", "latin"): {
            "prompt": "3lash kayrtakez ttahlil lmali l7adir?",
            "options": {
                "A": "3la rreklam lli tnchar 3la lwra9a lmaliya",
                "B": "3la ma3loumat mohimma w qabla l tta7a99o9 m3a ma3rifat 7doudha",
                "C": "3la wa3d b l ada2 kay3tih chi taraf talet",
                "D": "3la taman wa7ed lli tchaf f nhar wa7ed",
            },
            "explanation": "Ttahlil l7adir kayst3mel ma3loumat mohimma w qabla l tta7a99o9 w kaybayyen chnou ma katghattich had lma3loumat, 3wed ma ye3temd 3la ra9m wa7ed wla d3wa wa7da.",
        },
        ("ary", "arabic"): {
            "prompt": "على أشنو كيرتكز التحليل المالي الحذر؟",
            "options": {
                "A": "على الريكلام لي تنشر على الورقة المالية",
                "B": "على معلومات مهمة وقابلة للتحقق مع معرفة الحدود ديالها",
                "C": "على وعد بالأداء كيعطيه شي طرف ثالث",
                "D": "على ثمن واحد لي تشاف فنهار واحد",
            },
            "explanation": "التحليل الحذر كيستعمل معلومات مهمة وقابلة للتحقق وكيبين شنو ماكتغطيش هاد المعلومات، عوض مايعتمد على رقم واحد ولا دعوى وحدة.",
        },
    },
    "advanced-10": {
        ("en", "latin"): {
            "prompt": "Does regulatory information guarantee a performance?",
            "options": {
                "A": "Yes, published regulatory information always guarantees the outcome",
                "B": "Yes, but only in the case of an initial public offering",
                "C": "No, it informs the investor without promising any return",
                "D": "Yes, but only for bonds and other debt securities",
            },
            "explanation": "Regulatory information exists so that investors can judge an operation or an issuer on a documented basis; it improves transparency but never turns into a promise of return.",
        },
        ("ar", "arabic"): {
            "prompt": "هل تضمن المعلومة التنظيمية تحقيق أداء معين؟",
            "options": {
                "A": "نعم، فالمعلومة التنظيمية المنشورة تضمن النتيجة دائما",
                "B": "نعم، لكن في حالة الإدراج الأولي فقط",
                "C": "لا، فهي تخبر المستثمر دون أن تعده بأي عائد",
                "D": "نعم، لكن بالنسبة للسندات وأوراق الدين فقط",
            },
            "explanation": "توجد المعلومة التنظيمية ليقيم المستثمر عملية أو مصدرا على أساس موثق، فهي ترفع الشفافية لكنها لا تتحول أبدا إلى وعد بعائد.",
        },
        ("ary", "latin"): {
            "prompt": "Wach lma3louma ttandimiya kaddmen chi ada2?",
            "options": {
                "A": "Iyeh, lma3louma ttandimiya lli tnachrat kaddmen nnatija dima",
                "B": "Iyeh, walakin ghir f 7alat l idraj l awwali",
                "C": "La, kat3lem lmostatmir bla ma t3edo b ta rbe7",
                "D": "Iyeh, walakin ghir bnnisba l sanadat w wra9 ddin",
            },
            "explanation": "Lma3louma ttandimiya kayna bach lmostatmir y9der y7kem 3la chi 3amaliya wla chi mosder b tari9a mwatt9a, katzid f chaffafiya walakin 3emmerha ma katwlli w3d b rbe7.",
        },
        ("ary", "arabic"): {
            "prompt": "واش المعلومة التنظيمية كتضمن شي أداء؟",
            "options": {
                "A": "إيه، المعلومة التنظيمية لي تنشرات كتضمن النتيجة ديما",
                "B": "إيه، ولكن غير فحالة الإدراج الأولي",
                "C": "لا، كتعلم المستثمر بلا ماتوعدو بحتى ربح",
                "D": "إيه، ولكن غير بالنسبة للسندات وأوراق الدين",
            },
            "explanation": "المعلومة التنظيمية كاينة باش المستثمر يقدر يحكم على شي عملية ولا شي مصدر بطريقة موثقة، كتزيد فالشفافية ولكن عمرها ماكتولي وعد بربح.",
        },
    },
}


def localized_entry(question_id: str, language: str, script: str) -> dict[str, object]:
    """Return the authored entry for one question and one non-French locale."""
    try:
        return LOCALIZED_CONTENT[question_id][(language, script)]
    except KeyError as exc:  # pragma: no cover - guarded by the unit tests
        raise KeyError(
            f"missing authored localization for {question_id} in {language}/{script}"
        ) from exc
