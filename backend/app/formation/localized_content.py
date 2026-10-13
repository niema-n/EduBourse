"""Explicitly authored multilingual Formation dataset."""
# ruff: noqa: E501

LOCALES = ['fr/latin', 'en/latin', 'ar/arabic', 'ary/latin', 'ary/arabic']

FORMATION_LOCALIZED_CONTENT = {'beginner': [{'module_id': 'beginner_01',
               'locales': {'fr/latin': {'title': "Rôle d'une Bourse",
                                        'objective': 'La Bourse organise la rencontre entre émetteurs et '
                                                     "investisseurs. À retenir pour ce module : Rôle d'une Bourse.",
                                        'lesson': 'Elle publie des règles et facilite la confrontation des ordres.',
                                        'key_points': ["Point central : Rôle d'une Bourse.",
                                                       "L'apprentissage ne garantit aucun profit."],
                                        'checkpoint': 'Quel rôle la Bourse joue-t-elle entre émetteur et investisseur '
                                                      '?'},
                           'en/latin': {'title': 'The role of a stock exchange',
                                        'objective': 'Explain how an exchange organizes contact between issuers and '
                                                     'investors. Module takeaway: The role of a stock exchange.',
                                        'lesson': 'An exchange publishes trading rules and brings buy and sell orders '
                                                  'together in an organized venue.',
                                        'key_points': ['Core point: The role of a stock exchange.',
                                                       'Learning does not guarantee profit.'],
                                        'checkpoint': 'How does an exchange connect an issuer with an investor?'},
                           'ar/arabic': {'title': 'دور البورصة',
                                         'objective': 'تنظم البورصة تداول الأوراق المالية وفق قواعد معلنة. للمبتدئين.',
                                         'lesson': 'تنظم البورصة تداول الأوراق المالية وفق قواعد معلنة.',
                                         'key_points': ['تنظم البورصة تداول الأوراق المالية وفق قواعد معلنة.',
                                                        'التعلم لا يضمن أي ربح.'],
                                         'checkpoint': 'كيف تساهم البورصة؟'},
                           'ary/latin': {'title': 'Dour lborsa',
                                         'objective': 'Fhem kifach lborsa katnadem l3ala9a bin lmossdir w '
                                                      'lmoustathmir. Khlaa dyal had lmodule: Dour lborsa.',
                                         'lesson': 'Lborsa kat7ett 9awanin w katjme3 chra w lbi3 f sou9 mratab.',
                                         'key_points': ['N9ta l2assasiya: Dour lborsa.',
                                                        'Ta3allom machi daman dyal rbe7.'],
                                         'checkpoint': 'Ashno dour lborsa bin lmossdir w lmoustathmirs'},
                           'ary/arabic': {'title': 'شنو هي البورصة؟',
                                          'objective': 'البورصة سوق منظم كيتلاقاو فيه الشرا والبيع بقواعد واضحة. '
                                                       'للمبتدئين.',
                                          'lesson': 'البورصة سوق منظم كيتلاقاو فيه الشرا والبيع بقواعد واضحة.',
                                          'key_points': ['البورصة سوق منظم كيتلاقاو فيه الشرا والبيع بقواعد واضحة.',
                                                         'التعلم ما كيضمن حتى ربح.'],
                                          'checkpoint': 'شنو الدور ديال البورصة؟'}}},
              {'module_id': 'beginner_02',
               'locales': {'fr/latin': {'title': 'Actions et obligations',
                                        'objective': "Distinguer la propriété d'une action et la créance d'une "
                                                     'obligation. À retenir pour ce module : Actions et obligations.',
                                        'lesson': 'Une action représente une part du capital; une obligation '
                                                  'représente une dette envers son émetteur.',
                                        'key_points': ['Point central : Actions et obligations.',
                                                       "L'apprentissage ne garantit aucun profit."],
                                        'checkpoint': 'Quelle différence de droit existe entre actionnaire et '
                                                      'obligataire ?'},
                           'en/latin': {'title': 'Stocks and bonds',
                                        'objective': 'Distinguish ownership rights from the creditor relationship of a '
                                                     'bond. Module takeaway: Stocks and bonds.',
                                        'lesson': 'A stock represents ownership in capital; a bond represents a debt '
                                                  'claim against its issuer.',
                                        'key_points': ['Core point: Stocks and bonds.',
                                                       'Learning does not guarantee profit.'],
                                        'checkpoint': 'Which right differs between a shareholder and a bondholder?'},
                           'ar/arabic': {'title': 'الأسهم والسندات',
                                         'objective': 'يمثل السهم ملكية، ويمثل السند دينا على المصدر. للمبتدئين.',
                                         'lesson': 'يمثل السهم ملكية، ويمثل السند دينا على المصدر.',
                                         'key_points': ['يمثل السهم ملكية، ويمثل السند دينا على المصدر.',
                                                        'التعلم لا يضمن أي ربح.'],
                                         'checkpoint': 'ما الفرق بينهما؟'},
                           'ary/latin': {'title': 'Sohom w sanadat',
                                         'objective': 'Myez bin lmilkiya dyal sahm w l7e9 f sanad. Khlaa dyal had '
                                                      'lmodule: Sohom w sanadat.',
                                         'lesson': 'Sahm kay3ti 7e9 f lmilkiya, w sanad kay3ti 7e9 f din 3la lmossdir.',
                                         'key_points': ['N9ta l2assasiya: Sohom w sanadat.',
                                                        'Ta3allom machi daman dyal rbe7.'],
                                         'checkpoint': 'Ashno lfar9 bin l7e9 dyal mol sahm w mol sanads'},
                           'ary/arabic': {'title': 'السهم والسند',
                                          'objective': 'السهم كيعطي ملكية فشركة، والسند كيعني دين على اللي صدره. '
                                                       'للمبتدئين.',
                                          'lesson': 'السهم كيعطي ملكية فشركة، والسند كيعني دين على اللي صدره.',
                                          'key_points': ['السهم كيعطي ملكية فشركة، والسند كيعني دين على اللي صدره.',
                                                         'التعلم ما كيضمن حتى ربح.'],
                                          'checkpoint': 'شنو الفرق بين السهم والسند؟'}}},
              {'module_id': 'beginner_03',
               'locales': {'fr/latin': {'title': 'Marché primaire et secondaire',
                                        'objective': 'Comprendre la différence entre émission et revente de titres. À '
                                                     'retenir pour ce module : Marché primaire et secondaire.',
                                        'lesson': "Sur le marché primaire, l'émetteur lève des fonds; sur le marché "
                                                  'secondaire, les investisseurs échangent des titres existants.',
                                        'key_points': ['Point central : Marché primaire et secondaire.',
                                                       "L'apprentissage ne garantit aucun profit."],
                                        'checkpoint': "Sur quel marché l'entreprise reçoit-elle les fonds de "
                                                      "l'émission ?"},
                           'en/latin': {'title': 'Primary and secondary markets',
                                        'objective': 'Distinguish new issuance from later trading of existing '
                                                     'securities. Module takeaway: Primary and secondary markets.',
                                        'lesson': 'In the primary market an issuer raises funds; in the secondary '
                                                  'market investors trade securities already issued.',
                                        'key_points': ['Core point: Primary and secondary markets.',
                                                       'Learning does not guarantee profit.'],
                                        'checkpoint': 'Which market provides funds to the issuer at issuance?'},
                           'ar/arabic': {'title': 'السوق الأولية والثانوية',
                                         'objective': 'تستقبل الأولية إصدارات جديدة، وتتداول الثانوية أوراقا قائمة. '
                                                      'للمبتدئين.',
                                         'lesson': 'تستقبل الأولية إصدارات جديدة، وتتداول الثانوية أوراقا قائمة.',
                                         'key_points': ['تستقبل الأولية إصدارات جديدة، وتتداول الثانوية أوراقا قائمة.',
                                                        'التعلم لا يضمن أي ربح.'],
                                         'checkpoint': 'أين يحصل المصدر على التمويل؟'},
                           'ary/latin': {'title': 'Sou9 l2awali w tanawi',
                                         'objective': 'Fhem lfar9 bin lissdar w tbadol dyal l2awra9. Khlaa dyal had '
                                                      'lmodule: Sou9 l2awali w tanawi.',
                                         'lesson': 'Sou9 l2awali kayjib flous l lmossdir, w tanawi kaykhlli '
                                                   'lmoustathmirin ytbadlo l2awra9.',
                                         'key_points': ['N9ta l2assasiya: Sou9 l2awali w tanawi.',
                                                        'Ta3allom machi daman dyal rbe7.'],
                                         'checkpoint': 'Fin kaywsel lflous l lmossdir waqt lissdars'},
                           'ary/arabic': {'title': 'السوق اللولية والثانوية',
                                          'objective': 'السوق اللولية فيها إصدارات جديدة، والثانوية فيها أوراق كاينة. '
                                                       'للمبتدئين.',
                                          'lesson': 'السوق اللولية فيها إصدارات جديدة، والثانوية فيها أوراق كاينة.',
                                          'key_points': ['السوق اللولية فيها إصدارات جديدة، والثانوية فيها أوراق '
                                                         'كاينة.',
                                                         'التعلم ما كيضمن حتى ربح.'],
                                          'checkpoint': 'فين كيمشي التمويل؟'}}},
              {'module_id': 'beginner_04',
               'locales': {'fr/latin': {'title': 'Risque et rendement',
                                        'objective': 'Relier rendement attendu, incertitude et absence de garantie. À '
                                                     'retenir pour ce module : Risque et rendement.',
                                        'lesson': "Un rendement potentiel plus élevé peut s'accompagner d'une "
                                                  "incertitude plus forte; aucun rendement n'est garanti.",
                                        'key_points': ['Point central : Risque et rendement.',
                                                       "L'apprentissage ne garantit aucun profit."],
                                        'checkpoint': "Pourquoi un rendement attendu n'est-il pas une promesse ?"},
                           'en/latin': {'title': 'Risk and return basics',
                                        'objective': 'Relate expected return, uncertainty and the absence of '
                                                     'guarantees. Module takeaway: Risk and return basics.',
                                        'lesson': 'A higher potential return can involve greater uncertainty; no '
                                                  'expected return is guaranteed.',
                                        'key_points': ['Core point: Risk and return basics.',
                                                       'Learning does not guarantee profit.'],
                                        'checkpoint': 'Why is expected return not a promise?'},
                           'ar/arabic': {'title': 'المخاطر والعائد',
                                         'objective': 'يرتبط العائد المتوقع بمستوى المخاطرة ولا يضمن أي نتيجة. '
                                                      'للمبتدئين.',
                                         'lesson': 'يرتبط العائد المتوقع بمستوى المخاطرة ولا يضمن أي نتيجة.',
                                         'key_points': ['يرتبط العائد المتوقع بمستوى المخاطرة ولا يضمن أي نتيجة.',
                                                        'التعلم لا يضمن أي ربح.'],
                                         'checkpoint': 'لماذا لا يضمن العائد؟'},
                           'ary/latin': {'title': 'Lmkhatra w rbe7',
                                         'objective': 'Rbet bin rbe7 moutawa9a3 w l3adam dyal lya9in. Khlaa dyal had '
                                                      'lmodule: Lmkhatra w rbe7.',
                                         'lesson': 'Rbe7 moutawa9a3 kbir y9der yji m3a mkhatra ktr, w ma kayn ta chi '
                                                   'daman.',
                                         'key_points': ['N9ta l2assasiya: Lmkhatra w rbe7.',
                                                        'Ta3allom machi daman dyal rbe7.'],
                                         'checkpoint': '3lach rbe7 moutawa9a3 machi wa3ds'},
                           'ary/arabic': {'title': 'المخاطرة والربح',
                                          'objective': 'الربح المتوقع كيرتبط بالمخاطرة وما كاين حتى ضمان للنتيجة. '
                                                       'للمبتدئين.',
                                          'lesson': 'الربح المتوقع كيرتبط بالمخاطرة وما كاين حتى ضمان للنتيجة.',
                                          'key_points': ['الربح المتوقع كيرتبط بالمخاطرة وما كاين حتى ضمان للنتيجة.',
                                                         'التعلم ما كيضمن حتى ربح.'],
                                          'checkpoint': 'علاش الربح ما كيضمنش النتيجة؟'}}},
              {'module_id': 'beginner_05',
               'locales': {'fr/latin': {'title': 'Bases de la diversification',
                                        'objective': "Comprendre pourquoi répartir l'exposition peut réduire certains "
                                                     'risques. À retenir pour ce module : Bases de la diversification.',
                                        'lesson': "Répartir l'exposition entre plusieurs actifs limite l'effet d'un "
                                                  'seul événement, sans supprimer tous les risques.',
                                        'key_points': ['Point central : Bases de la diversification.',
                                                       "L'apprentissage ne garantit aucun profit."],
                                        'checkpoint': 'Quel risque la diversification ne peut-elle pas supprimer ?'},
                           'en/latin': {'title': 'Diversification basics',
                                        'objective': 'Explain how spreading exposure can reduce some risks. Module '
                                                     'takeaway: Diversification basics.',
                                        'lesson': 'Spreading exposure across assets limits the effect of one event '
                                                  'without removing every risk.',
                                        'key_points': ['Core point: Diversification basics.',
                                                       'Learning does not guarantee profit.'],
                                        'checkpoint': 'Which risk cannot diversification eliminate?'},
                           'ar/arabic': {'title': 'التنويع',
                                         'objective': 'يوزع التنويع التعرض على أصول مختلفة لتقليل الأثر. للمبتدئين.',
                                         'lesson': 'يوزع التنويع التعرض على أصول مختلفة لتقليل الأثر.',
                                         'key_points': ['يوزع التنويع التعرض على أصول مختلفة لتقليل الأثر.',
                                                        'التعلم لا يضمن أي ربح.'],
                                         'checkpoint': 'كيف يساعد التنويع؟'},
                           'ary/latin': {'title': 'Asasiyat tnoui3',
                                         'objective': 'Fhem kifach t9sim lta3arrod y9der yn9es chi mkhatra. Khlaa dyal '
                                                      'had lmodule: Asasiyat tnoui3.',
                                         'lesson': 'Mlli kan9smo lta3arrod 3la ktar mn asl, kan7eddo athar dyal wa7ed '
                                                   'l7adath bla ma n7eydo ga3 lmkhater.',
                                         'key_points': ['N9ta l2assasiya: Asasiyat tnoui3.',
                                                        'Ta3allom machi daman dyal rbe7.'],
                                         'checkpoint': 'Ashno lmkhatra li tnoui3 ma kay7yedhachs'},
                           'ary/arabic': {'title': 'التنويع',
                                          'objective': 'التنويع كيقسم التعرض على أصول مختلفة باش يخفف الأثر. '
                                                       'للمبتدئين.',
                                          'lesson': 'التنويع كيقسم التعرض على أصول مختلفة باش يخفف الأثر.',
                                          'key_points': ['التنويع كيقسم التعرض على أصول مختلفة باش يخفف الأثر.',
                                                         'التعلم ما كيضمن حتى ربح.'],
                                          'checkpoint': 'كيفاش يقدر التنويع يخفف المخاطر؟'}}},
              {'module_id': 'beginner_06',
               'locales': {'fr/latin': {'title': 'Indices boursiers',
                                        'objective': 'Lire un indice comme une mesure construite du marché. À retenir '
                                                     'pour ce module : Indices boursiers.',
                                        'lesson': 'Un indice combine plusieurs titres selon une méthode; il décrit une '
                                                  'évolution et ne représente pas un titre unique.',
                                        'key_points': ['Point central : Indices boursiers.',
                                                       "L'apprentissage ne garantit aucun profit."],
                                        'checkpoint': 'Que mesure un indice et que ne mesure-t-il pas ?'},
                           'en/latin': {'title': 'Stock-market indexes',
                                        'objective': 'Read an index as a constructed measure of market movement. '
                                                     'Module takeaway: Stock-market indexes.',
                                        'lesson': 'An index combines several securities using a stated method; it '
                                                  'describes movement rather than one security.',
                                        'key_points': ['Core point: Stock-market indexes.',
                                                       'Learning does not guarantee profit.'],
                                        'checkpoint': 'What does an index measure and what does it not measure?'},
                           'ar/arabic': {'title': 'المؤشرات',
                                         'objective': 'تلخص المؤشرات أداء مجموعة من الأوراق. للمبتدئين.',
                                         'lesson': 'تلخص المؤشرات أداء مجموعة من الأوراق.',
                                         'key_points': ['تلخص المؤشرات أداء مجموعة من الأوراق.',
                                                        'التعلم لا يضمن أي ربح.'],
                                         'checkpoint': 'ماذا يقيس المؤشر؟'},
                           'ary/latin': {'title': 'Mouachirat sou9',
                                         'objective': 'Fhem lmouachir kmi9yass morakkab l7arakat sou9. Khlaa dyal had '
                                                      'lmodule: Mouachirat sou9.',
                                         'lesson': 'Lmouachir kayjme3 ktar mn wara9a b tari9a m3ayena, w kaywassaf '
                                                   'l7araka machi wara9a wa7da.',
                                         'key_points': ['N9ta l2assasiya: Mouachirat sou9.',
                                                        'Ta3allom machi daman dyal rbe7.'],
                                         'checkpoint': 'Ash kay9iss lmouachirs'},
                           'ary/arabic': {'title': 'المؤشرات',
                                          'objective': 'المؤشرات كتلخص أداء مجموعة ديال الأوراق. للمبتدئين.',
                                          'lesson': 'المؤشرات كتلخص أداء مجموعة ديال الأوراق.',
                                          'key_points': ['المؤشرات كتلخص أداء مجموعة ديال الأوراق.',
                                                         'التعلم ما كيضمن حتى ربح.'],
                                          'checkpoint': 'شنو كيقيس المؤشر؟'}}},
              {'module_id': 'beginner_07',
               'locales': {'fr/latin': {'title': 'Ordres et transactions',
                                        'objective': "Identifier le sens, la quantité et le prix éventuel d'un ordre. "
                                                     'À retenir pour ce module : Ordres et transactions.',
                                        'lesson': "Un ordre indique une intention d'achat ou de vente et ses "
                                                  'conditions; son exécution dépend des règles et de la liquidité.',
                                        'key_points': ['Point central : Ordres et transactions.',
                                                       "L'apprentissage ne garantit aucun profit."],
                                        'checkpoint': 'Quelles informations de base un ordre peut-il contenir ?'},
                           'en/latin': {'title': 'Orders and transactions',
                                        'objective': 'Identify direction, quantity and any price condition in an '
                                                     'order. Module takeaway: Orders and transactions.',
                                        'lesson': 'An order states an intention to buy or sell and its conditions; '
                                                  'execution depends on market rules and liquidity.',
                                        'key_points': ['Core point: Orders and transactions.',
                                                       'Learning does not guarantee profit.'],
                                        'checkpoint': 'What basic information can an order contain?'},
                           'ar/arabic': {'title': 'الأوامر',
                                         'objective': 'تحدد أوامر التداول السعر والكمية والتنفيذ. للمبتدئين.',
                                         'lesson': 'تحدد أوامر التداول السعر والكمية والتنفيذ.',
                                         'key_points': ['تحدد أوامر التداول السعر والكمية والتنفيذ.',
                                                        'التعلم لا يضمن أي ربح.'],
                                         'checkpoint': 'ماذا يحدد الأمر؟'},
                           'ary/latin': {'title': 'L2awamir w lmou3amalat',
                                         'objective': '3ref jihat l2amr w lkemya w taman ila kayn. Khlaa dyal had '
                                                      'lmodule: L2awamir w lmou3amalat.',
                                         'lesson': 'L2amr kaybayan chra wla lbi3 w chourout, w ttanfid kayt3alla9 b '
                                                   'sou9 w siyola.',
                                         'key_points': ['N9ta l2assasiya: L2awamir w lmou3amalat.',
                                                        'Ta3allom machi daman dyal rbe7.'],
                                         'checkpoint': 'Ashno lma3loumat l2assasiya f l2amrs'},
                           'ary/arabic': {'title': 'الأوامر',
                                          'objective': 'أوامر التداول كيتحددو فيها الثمن والكمية وشروط التنفيذ. '
                                                       'للمبتدئين.',
                                          'lesson': 'أوامر التداول كيتحددو فيها الثمن والكمية وشروط التنفيذ.',
                                          'key_points': ['أوامر التداول كيتحددو فيها الثمن والكمية وشروط التنفيذ.',
                                                         'التعلم ما كيضمن حتى ربح.'],
                                          'checkpoint': 'شنو كيتحدد فالأمر ديال التداول؟'}}},
              {'module_id': 'beginner_08',
               'locales': {'fr/latin': {'title': 'Bourse de Casablanca et acteurs',
                                        'objective': "Identifier les principaux acteurs de l'écosystème marocain. À "
                                                     'retenir pour ce module : Bourse de Casablanca et acteurs.',
                                        'lesson': 'La Bourse de Casablanca, les émetteurs, les intermédiaires et '
                                                  "l'autorité de marché ont des fonctions complémentaires.",
                                        'key_points': ['Point central : Bourse de Casablanca et acteurs.',
                                                       "L'apprentissage ne garantit aucun profit."],
                                        'checkpoint': 'Quels acteurs contribuent au fonctionnement du marché marocain '
                                                      '?'},
                           'en/latin': {'title': 'Casablanca exchange and market actors',
                                        'objective': 'Identify the main participants in the Moroccan market ecosystem. '
                                                     'Module takeaway: Casablanca exchange and market actors.',
                                        'lesson': 'The Casablanca Stock Exchange, issuers, intermediaries and the '
                                                  'market authority have complementary roles.',
                                        'key_points': ['Core point: Casablanca exchange and market actors.',
                                                       'Learning does not guarantee profit.'],
                                        'checkpoint': 'Which actors help the Moroccan market function?'},
                           'ar/arabic': {'title': 'السوق المغربي',
                                         'objective': 'يعمل السوق المغربي ضمن قواعد تنظم حماية المستثمرين. للمبتدئين.',
                                         'lesson': 'يعمل السوق المغربي ضمن قواعد تنظم حماية المستثمرين.',
                                         'key_points': ['يعمل السوق المغربي ضمن قواعد تنظم حماية المستثمرين.',
                                                        'التعلم لا يضمن أي ربح.'],
                                         'checkpoint': 'كيف تحمي القواعد المستثمر؟'},
                           'ary/latin': {'title': 'Borsa Casablanca w lfa3ilin',
                                         'objective': '3ref lfa3ilin l2assasiyin f sou9 lmghrib. Khlaa dyal had '
                                                      'lmodule: Borsa Casablanca w lfa3ilin.',
                                         'lesson': 'Borsa Casablanca w lmossdirin w lwosta w lhay2a lmounadima kol '
                                                   'wa7ed 3ndo dour.',
                                         'key_points': ['N9ta l2assasiya: Borsa Casablanca w lfa3ilin.',
                                                        'Ta3allom machi daman dyal rbe7.'],
                                         'checkpoint': 'Shkon kay3awen sou9 lmghrib ykhdems'},
                           'ary/arabic': {'title': 'السوق المغربي',
                                          'objective': 'السوق المغربي كيخدم بقواعد كتحمي المستثمرين. للمبتدئين.',
                                          'lesson': 'السوق المغربي كيخدم بقواعد كتحمي المستثمرين.',
                                          'key_points': ['السوق المغربي كيخدم بقواعد كتحمي المستثمرين.',
                                                         'التعلم ما كيضمن حتى ربح.'],
                                          'checkpoint': 'كيفاش كتعاون القواعد؟'}}}],
 'intermediate': [{'module_id': 'intermediate_01',
                   'locales': {'fr/latin': {'title': 'Organisation du marché',
                                            'objective': 'Analyser les fonctions respectives des participants et des '
                                                         'infrastructures. À retenir pour ce module : Organisation du '
                                                         'marché.',
                                            'lesson': "L'organisation du marché sépare émission, intermédiation, "
                                                      'négociation, compensation et règlement.',
                                            'key_points': ['Point central : Organisation du marché.',
                                                           "L'apprentissage ne garantit aucun profit."],
                                            'checkpoint': 'Comment ces fonctions réduisent-elles les risques '
                                                          'opérationnels ?'},
                               'en/latin': {'title': 'Market organization',
                                            'objective': 'Analyze the separate roles of participants and market '
                                                         'infrastructure. Module takeaway: Market organization.',
                                            'lesson': 'Market organization separates issuance, intermediation, '
                                                      'trading, clearing and settlement.',
                                            'key_points': ['Core point: Market organization.',
                                                           'Learning does not guarantee profit.'],
                                            'checkpoint': 'How do these functions reduce operational risk?'},
                               'ar/arabic': {'title': 'تنظيم السوق والمشاركين',
                                             'objective': 'فهم أدوار المصدرين والمستثمرين والوسطاء وكيف تتفاعل البنية '
                                                          'التحتية للسوق في تنفيذ المعاملات.',
                                             'lesson': 'تجمع السوق المالية بين الشركات التي تبحث عن التمويل '
                                                       'والمستثمرين الذين يملكون المدخرات والوسطاء الذين ينقلون '
                                                       'الأوامر. وتوفر البورصة وأنظمة التسوية قواعد مشتركة لتسجيل '
                                                       'التداول ونقل الملكية بطريقة منظمة.',
                                             'key_points': ['يصدر الطرف الباحث عن التمويل أوراقا مالية، بينما يقيّم '
                                                            'المستثمر المعلومات والمخاطر قبل اتخاذ القرار.',
                                                            'يساعد الوسيط في استقبال الأمر وتنفيذه، لكن مسؤولية القرار '
                                                            'المالي تبقى مرتبطة بهدف المستثمر وقدرته على تحمل الخطر.'],
                                             'checkpoint': 'كيف يمكن لتفاعل المصدر والمستثمر والوسيط أن يجعل عملية '
                                                           'التداول أكثر تنظيما؟'},
                               'ary/latin': {'title': 'Tartib sou9',
                                             'objective': 'Fhem dour kol fa3il w lbinya li katkhddem sou9. Khlaa dyal '
                                                          'had lmodule: Tartib sou9.',
                                             'lesson': 'Sou9 kay9sem lissdar w lwisata w ttdayol w taswiya f marahil '
                                                       'mfr9in.',
                                             'key_points': ['N9ta l2assasiya: Tartib sou9.',
                                                            'Ta3allom machi daman dyal rbe7.'],
                                             'checkpoint': 'Kifach had lmarahil kayna9so lmokhatra l3amaliyas'},
                               'ary/arabic': {'title': 'كيفاش كتتنظم البورصة',
                                              'objective': 'فهم شكون كيمول الشركات وشكون كيستثمر وكيفاش كيتعاونو '
                                                           'الوسطاء والبنية ديال السوق.',
                                              'lesson': 'البورصة كتجمع الشركات اللي محتاجة التمويل مع الناس اللي باغين '
                                                        'يستثمرو مدخراتهم، والوسيط كيوصل الأوامر للنظام. من بعد '
                                                        'التداول كتكمل التسوية ونقل الملكية بقواعد معروفة، باش تبقى '
                                                        'العملية منظمة.',
                                              'key_points': ['الشركة كتطرح الوراق باش تجمع التمويل، والمستثمر كيشوف '
                                                             'المعلومات والخطر قبل القرار.',
                                                             'الوسيط كيساعد فاستقبال وتنفيذ الأمر، ولكن قرار الاستثمار '
                                                             'ومسؤوليته كيبقاو عند صاحبه.'],
                                              'checkpoint': 'كيفاش كيساعد التعاون بين الشركة والمستثمر والوسيط باش '
                                                            'يدوز التداول منظم؟'}}},
                  {'module_id': 'intermediate_02',
                   'locales': {'fr/latin': {'title': "Types d'ordres et exécution",
                                            'objective': 'Comparer ordre au marché, ordre limité et conditions '
                                                         "d'exécution. À retenir pour ce module : Types d'ordres et "
                                                         'exécution.',
                                            'lesson': "Le type d'ordre modifie la priorité, le prix accepté et la "
                                                      "probabilité d'exécution dans le carnet.",
                                            'key_points': ["Point central : Types d'ordres et exécution.",
                                                           "L'apprentissage ne garantit aucun profit."],
                                            'checkpoint': "Comment une limite de prix influence-t-elle l'exécution ?"},
                               'en/latin': {'title': 'Order types and execution',
                                            'objective': 'Compare market orders, limit orders and their execution '
                                                         'conditions. Module takeaway: Order types and execution.',
                                            'lesson': 'Order type changes priority, accepted price and execution '
                                                      'probability in the order book.',
                                            'key_points': ['Core point: Order types and execution.',
                                                           'Learning does not guarantee profit.'],
                                            'checkpoint': 'How does a price limit affect execution?'},
                               'ar/arabic': {'title': 'أنواع الأوامر وتنفيذها',
                                             'objective': 'تحليل أثر خصائص أمر السوق والأمر المحدد ومدة الصلاحية في '
                                                          'احتمال التنفيذ والسعر النهائي.',
                                             'lesson': 'ينفذ أمر السوق بأفضل سعر متاح في لحظة وصوله، ولذلك قد يتغير '
                                                       'السعر أثناء تنفيذ كمية كبيرة. أما الأمر المحدد فيشترط سعرا '
                                                       'أقصى للشراء أو أدنى للبيع، وقد يبقى دون تنفيذ إذا لم تتحقق '
                                                       'الشروط.',
                                             'key_points': ['تمنح مدة الصلاحية الأمر المحدد إطارا زمنيا واضحا، لكنها '
                                                            'لا تضمن الحصول على الكمية المطلوبة.',
                                                            'ينبغي مقارنة سرعة التنفيذ مع التحكم في السعر بدلا من '
                                                            'اعتبار أحد النوعين مناسبا لكل حالة.'],
                                             'checkpoint': 'متى يمكن أن يفضل المستثمر التحكم في السعر على سرعة تنفيذ '
                                                           'الأمر؟'},
                               'ary/latin': {'title': 'Anwa3 l2awamir w ttanfid',
                                             'objective': '9aren bin amr sou9 w amr b taman m7edded. Khlaa dyal had '
                                                          'lmodule: Anwa3 l2awamir w ttanfid.',
                                             'lesson': 'Naw3 l2amr kaybdl l2awlawiya w taman w forsa ttanfid f daftar '
                                                       'l2awamir.',
                                             'key_points': ['N9ta l2assasiya: Anwa3 l2awamir w ttanfid.',
                                                            'Ta3allom machi daman dyal rbe7.'],
                                             'checkpoint': 'Kifach taman m7edded kay2etter 3la ttanfids'},
                               'ary/arabic': {'title': 'الأوامر وكيفاش كيتنفذو',
                                              'objective': 'فهم كيفاش نوع الأمر والثمن والمدة كيأثرو على سرعة التنفيذ '
                                                           'وعلى النتيجة النهائية.',
                                              'lesson': 'أمر السوق كيدوز بأحسن ثمن موجود فداك الوقت، ولكن الثمن يقدر '
                                                        'يتحرك إلا كانت الكمية كبيرة. الأمر المحدد كيربط الشرا بثمن '
                                                        'أقصى والبيع بثمن أدنى، وقد يبقى معلقا إلا ماوصلش السوق للشرط.',
                                              'key_points': ['المدة كتحدد شحال يبقى الأمر المحدد فعال، وماكتضمنش '
                                                             'الحصول على الكمية.',
                                                             'خاص نقارنو بين سرعة التنفيذ والتحكم فالثمن، وماشي نفترضو '
                                                             'أن نوعا واحدا مناسب دائما.'],
                                              'checkpoint': 'فاش يقدر المستثمر يفضل يتحكم فالثمن على أنه ينفذ '
                                                            'بسرعة؟'}}},
                  {'module_id': 'intermediate_03',
                   'locales': {'fr/latin': {'title': 'Liquidité et volatilité',
                                            'objective': 'Relier profondeur, volume et variation des prix. À retenir '
                                                         'pour ce module : Liquidité et volatilité.',
                                            'lesson': "Une liquidité faible peut amplifier l'effet d'un ordre; la "
                                                      "volatilité décrit l'amplitude des variations, pas leur "
                                                      'direction.',
                                            'key_points': ['Point central : Liquidité et volatilité.',
                                                           "L'apprentissage ne garantit aucun profit."],
                                            'checkpoint': 'Pourquoi liquidité et volatilité doivent-elles être '
                                                          'distinguées ?'},
                               'en/latin': {'title': 'Liquidity and volatility',
                                            'objective': 'Relate depth, trading activity and price variation. Module '
                                                         'takeaway: Liquidity and volatility.',
                                            'lesson': "Low liquidity can amplify an order's effect; volatility "
                                                      'describes variation size rather than direction.',
                                            'key_points': ['Core point: Liquidity and volatility.',
                                                           'Learning does not guarantee profit.'],
                                            'checkpoint': 'Why should liquidity and volatility be distinguished?'},
                               'ar/arabic': {'title': 'السيولة والتذبذب',
                                             'objective': 'فهم العلاقة بين سيولة الورقة المالية وتذبذب سعرها وتأثير '
                                                          'ذلك في سهولة تنفيذ الأوامر.',
                                             'lesson': 'تعني السيولة وجود مشترين وبائعين بما يكفي لتنفيذ الصفقة من دون '
                                                       'تغيير كبير في السعر. وقد يتسع نطاق حركة السعر عندما يقل عدد '
                                                       'المشاركين أو تصل أخبار جديدة، لذلك ينبغي قراءة السيولة '
                                                       'والتذبذب معا.',
                                             'key_points': ['يساعد ضيق الفرق بين سعري الشراء والبيع على تقدير سهولة '
                                                            'الدخول والخروج من الصفقة.',
                                                            'لا تعني السيولة المرتفعة غياب الخسارة، لأن الخبر المفاجئ '
                                                            'قد يغير السعر بسرعة.'],
                                             'checkpoint': 'كيف يمكن لانخفاض السيولة أن يزيد الأثر السعري لأمر كبير؟'},
                               'ary/latin': {'title': 'Siyola w tt9allob',
                                             'objective': 'Rbet bin 3om9 sou9 w 7araka dyal taman. Khlaa dyal had '
                                                          'lmodule: Siyola w tt9allob.',
                                             'lesson': 'Ila kant siyola 9lila, amr wa7ed y9der y7rek taman; tt9allob '
                                                       'kaywassaf 9owat l7araka.',
                                             'key_points': ['N9ta l2assasiya: Siyola w tt9allob.',
                                                            'Ta3allom machi daman dyal rbe7.'],
                                             'checkpoint': '3lach khasna nfr9o bin siyola w tt9allobs'},
                               'ary/arabic': {'title': 'السيولة وتقلب الثمن',
                                              'objective': 'شرح علاش السيولة والتقلب مهمين فالتنفيذ وكيفاش كيأثر نقص '
                                                           'المشترين على الثمن.',
                                              'lesson': 'السيولة كتعني كاينين شرا وبياعة كافيين باش تدوز الصفقة بلا '
                                                        'مايتبدل الثمن بزاف. ملي كيقلو المشاركين ولا كيخرج خبر جديد، '
                                                        'الحركة كتقدر تقوى، وداكشي علاش خاص نشوفو السيولة والتقلب '
                                                        'مجموعين.',
                                              'key_points': ['الفارق الصغير بين ثمن الشرا والبيع كيعطي فكرة على سهولة '
                                                             'الدخول والخروج.',
                                                             'السيولة القوية ماشي حماية من الخسارة، حيث الخبر المفاجئ '
                                                             'يقدر يقلب الثمن بسرعة.'],
                                              'checkpoint': 'كيفاش كيقدر نقص السيولة يكبر الأثر ديال أمر كبير على '
                                                            'الثمن؟'}}},
                  {'module_id': 'intermediate_04',
                   'locales': {'fr/latin': {'title': 'Risque, rendement et diversification appliqués',
                                            'objective': 'Évaluer les arbitrages entre exposition, corrélation et '
                                                         'perte possible. À retenir pour ce module : Risque, rendement '
                                                         'et diversification appliqués.',
                                            'lesson': "La combinaison d'actifs dépend de leurs comportements "
                                                      'conjoints; réduire une concentration ne supprime pas le risque '
                                                      'de marché.',
                                            'key_points': ['Point central : Risque, rendement et diversification '
                                                           'appliqués.',
                                                           "L'apprentissage ne garantit aucun profit."],
                                            'checkpoint': 'Pourquoi la corrélation compte-t-elle dans une combinaison '
                                                          "d'actifs ?"},
                               'en/latin': {'title': 'Applied risk, return and diversification',
                                            'objective': 'Assess trade-offs among exposure, correlation and possible '
                                                         'loss. Module takeaway: Applied risk, return and '
                                                         'diversification.',
                                            'lesson': 'Combining assets depends on joint behavior; reducing '
                                                      'concentration does not remove market risk.',
                                            'key_points': ['Core point: Applied risk, return and diversification.',
                                                           'Learning does not guarantee profit.'],
                                            'checkpoint': 'Why does correlation matter in an asset combination?'},
                               'ar/arabic': {'title': 'العائد والمخاطر والتنويع',
                                             'objective': 'تطبيق مفاهيم العائد المتوقع والمخاطر والتنويع عند مقارنة '
                                                          'خيارات استثمارية تعليمية مختلفة.',
                                             'lesson': 'العائد المتوقع هو نتيجة محتملة وليس وعدا، ويرتبط عادة بدرجة '
                                                       'عدم اليقين التي يقبلها المستثمر. ويساعد توزيع المال بين أصول '
                                                       'لا تتحرك بالطريقة نفسها على تقليل تركيز الخطر، من دون أن يلغي '
                                                       'تقلبات السوق.',
                                             'key_points': ['تتطلب المقارنة تحديد الهدف ومدة الاستثمار ومستوى الخسارة '
                                                            'المحتملة قبل النظر إلى العائد.',
                                                            'قد يقلل التنويع أثر مشكلة واحدة، لكنه لا يحمي المحفظة من '
                                                            'هبوط عام في السوق.'],
                                             'checkpoint': 'لماذا لا يكفي اختيار الأصل ذي العائد المتوقع الأعلى من دون '
                                                           'دراسة مخاطره؟'},
                               'ary/latin': {'title': 'Tatbi9 lmkhater w rbe7 w tnoui3',
                                             'objective': 'Fhem lmosawama bin lta3arrod w lirtibat w lkhssara. Khlaa '
                                                          'dyal had lmodule: Tatbi9 lmkhater w rbe7 w tnoui3.',
                                             'lesson': 'Jm3 l2osol kayt3alla9 b kifach kayt7erko m3a b3d, w tnoui3 ma '
                                                       'kay7yedch mkhatra sou9.',
                                             'key_points': ['N9ta l2assasiya: Tatbi9 lmkhater w rbe7 w tnoui3.',
                                                            'Ta3allom machi daman dyal rbe7.'],
                                             'checkpoint': '3lach lirtibat mohim f jm3 l2osols'},
                               'ary/arabic': {'title': 'الربح والخطر والتنويع',
                                              'objective': 'تطبيق العلاقة بين الربح الممكن والخطر والتنويع ملي كنقارنو '
                                                           'بين اختيارات مختلفة.',
                                              'lesson': 'الربح اللي كنتسناوه احتمال وماشي وعد، وغالبا كيكون مرتبط '
                                                        'بكمية عدم اليقين اللي قابلها المستثمر. توزيع الفلوس على أصول '
                                                        'ماكيتحركوش بنفس الطريقة كيقدر ينقص تركيز الخطر، ولكن ماكيلغيش '
                                                        'تقلبات السوق.',
                                              'key_points': ['قبل مقارنة الربح خاص نحددو الهدف والمدة وشحال من خسارة '
                                                             'ممكنة نقبلوها.',
                                                             'التنويع كيقدر ينقص أثر مشكل واحد، ولكن ماكيحميش من هبوط '
                                                             'عام فالسوق.'],
                                              'checkpoint': 'علاش ماكافيش نختارو الأصل اللي عندو ربح متوقع كبير بلا '
                                                            'ماندرسو الخطر ديالو؟'}}},
                  {'module_id': 'intermediate_05',
                   'locales': {'fr/latin': {'title': 'Dividendes et opérations sur titres',
                                            'objective': "Suivre l'effet pédagogique d'un dividende ou d'une opération "
                                                         'sur titres. À retenir pour ce module : Dividendes et '
                                                         'opérations sur titres.',
                                            'lesson': 'Un dividende distribue une partie du résultat; une opération '
                                                      'sur titres peut modifier les droits ou le nombre de titres.',
                                            'key_points': ['Point central : Dividendes et opérations sur titres.',
                                                           "L'apprentissage ne garantit aucun profit."],
                                            'checkpoint': 'Comment une opération sur titres peut-elle modifier la '
                                                          "position d'un investisseur ?"},
                               'en/latin': {'title': 'Dividends and corporate actions',
                                            'objective': 'Explain the educational effect of a dividend or corporate '
                                                         'action. Module takeaway: Dividends and corporate actions.',
                                            'lesson': 'A dividend distributes part of earnings; a corporate action can '
                                                      'change rights or the number of securities.',
                                            'key_points': ['Core point: Dividends and corporate actions.',
                                                           'Learning does not guarantee profit.'],
                                            'checkpoint': "How can a corporate action change an investor's position?"},
                               'ar/arabic': {'title': 'التوزيعات وحقوق المساهم',
                                             'objective': 'شرح أثر توزيعات الأرباح وتواريخها وحقوق المساهم في قيمة '
                                                          'السهم وقرار الشركة.',
                                             'lesson': 'تعلن الشركة شروط التوزيع وتحدد من يملك الحق في الاستفادة منه '
                                                       'حسب التواريخ المعلنة. وقد يتغير سعر السهم بعد انفصال الحق لأن '
                                                       'قيمة التوزيع تؤثر في توقعات المشترين والبائعين، بينما تظل '
                                                       'النتيجة مرتبطة بأداء الشركة.',
                                             'key_points': ['ينبغي التمييز بين إعلان التوزيع وتاريخ الاستحقاق وتاريخ '
                                                            'دفع المبلغ.',
                                                            'لا يمثل التوزيع وحده عائدا صافيا، لأن سعر السهم والنتائج '
                                                            'المستقبلية قد يتغيران.'],
                                             'checkpoint': 'كيف تفسر تغير سعر السهم بعد انفصال حق توزيع الأرباح؟'},
                               'ary/latin': {'title': 'Arba7 w 3amaliyat cherkat',
                                             'objective': 'Fhem ach kaytbedel mlli katwze3 cherka rbe7 wla katdir '
                                                          '3amaliya. Khlaa dyal had lmodule: Arba7 w 3amaliyat '
                                                          'cherkat.',
                                             'lesson': 'Tawzi3 kay9sem chi rbe7, w 3amaliya dyal cherka t9der tbdel '
                                                       'l7o9o9 wla 3adad l2awra9.',
                                             'key_points': ['N9ta l2assasiya: Arba7 w 3amaliyat cherkat.',
                                                            'Ta3allom machi daman dyal rbe7.'],
                                             'checkpoint': 'Kifach 3amaliya dyal cherka t9der tbdel lmo9ifs'},
                               'ary/arabic': {'title': 'الأرباح وحقوق المساهم',
                                              'objective': 'فهم شنو كتبدل توزيعات الأرباح فحقوق المساهم وفثمن السهم '
                                                           'وبقرارات الشركة.',
                                              'lesson': 'الشركة كتنشر شروط التوزيع وكتحدد شكون عندو الحق على حساب '
                                                        'التواريخ المعلنة. من بعد انفصال الحق يقدر يتحرك ثمن السهم حيث '
                                                        'التوزيع كيأثر فانتظارات الشرا والبيع، والنتيجة كتبقى مربوطة '
                                                        'بأداء الشركة.',
                                              'key_points': ['خاص نفرقو بين إعلان التوزيع وتاريخ الاستحقاق ونهار '
                                                             'الأداء.',
                                                             'التوزيع بوحدو ماشي ربح صاف، حيث ثمن السهم والنتائج '
                                                             'الجاية يقدرو يتبدلو.'],
                                              'checkpoint': 'كيفاش تفسر تبدل ثمن السهم من بعد انفصال حق توزيع '
                                                            'الأرباح؟'}}},
                  {'module_id': 'intermediate_06',
                   'locales': {'fr/latin': {'title': 'OPCVM et gestion collective',
                                            'objective': 'Comprendre la mutualisation, la valeur liquidative et les '
                                                         'frais. À retenir pour ce module : OPCVM et gestion '
                                                         'collective.',
                                            'lesson': 'Un OPCVM regroupe des souscriptions et applique une politique '
                                                      'documentée; la valeur liquidative évolue avec les actifs '
                                                      'détenus.',
                                            'key_points': ['Point central : OPCVM et gestion collective.',
                                                           "L'apprentissage ne garantit aucun profit."],
                                            'checkpoint': "Quelles informations faut-il examiner avant d'étudier un "
                                                          'OPCVM ?'},
                               'en/latin': {'title': 'UCITS and collective investment',
                                            'objective': 'Understand pooling, net asset value and fees. Module '
                                                         'takeaway: UCITS and collective investment.',
                                            'lesson': 'A collective fund pools subscriptions under a documented '
                                                      'policy; its net asset value changes with held assets.',
                                            'key_points': ['Core point: UCITS and collective investment.',
                                                           'Learning does not guarantee profit.'],
                                            'checkpoint': 'Which information should be examined when studying a fund?'},
                               'ar/arabic': {'title': 'الاستثمار الجماعي',
                                             'objective': 'فهم كيفية تجميع أموال المستثمرين وإدارتها داخل صناديق '
                                                          'الاستثمار مع تقييم الرسوم والتنويع.',
                                             'lesson': 'يجمع الصندوق أموال عدة مستثمرين ويستعملها لامتلاك مجموعة من '
                                                       'الأصول وفق سياسة معلنة. وتسمح الإدارة الجماعية بتوزيع '
                                                       'المتابعة، لكن المستثمر يحتاج إلى قراءة الرسوم وأهداف الصندوق '
                                                       'ومستوى المخاطر قبل المقارنة.',
                                             'key_points': ['تؤثر رسوم الإدارة والمعاملات في العائد الصافي الذي يصل '
                                                            'إلى المستثمر.',
                                                            'قد يوسع الصندوق التنويع، إلا أن نتائجه تظل مرتبطة بالأصول '
                                                            'التي يملكها وبطريقة إدارتها.'],
                                             'checkpoint': 'ما المعلومات التي تقارنها بين صندوقين يختلفان في الرسوم '
                                                           'والسياسة الاستثمارية؟'},
                               'ary/latin': {'title': 'Tadbir jama3i w OPCVM',
                                             'objective': 'Fhem kifach kaytjm3 lmal w kifach kat7seb l9ima ssafiya. '
                                                          'Khlaa dyal had lmodule: Tadbir jama3i w OPCVM.',
                                             'lesson': 'OPCVM kayjme3 lmosahamat b siyasa mktouba, w l9ima dyalo '
                                                       'katetbedel m3a l2osol.',
                                             'key_points': ['N9ta l2assasiya: Tadbir jama3i w OPCVM.',
                                                            'Ta3allom machi daman dyal rbe7.'],
                                             'checkpoint': 'Ash khassek t3ref 9bel ma t9ra 3la OPCVMs'},
                               'ary/arabic': {'title': 'الاستثمار فالصناديق',
                                              'objective': 'فهم كيفاش كتتجمع الفلوس فالصناديق وكيفاش كتتسير مع مقارنة '
                                                           'المصاريف والتنويع.',
                                              'lesson': 'الصندوق كيجمع فلوس ديال مستثمرين مختلفين وكيشري بها أصول على '
                                                        'حساب سياسة مكتوبة. التسيير الجماعي كيسهل التتبع، ولكن خاص '
                                                        'المستثمر يقرا المصاريف والهدف ودرجة الخطر قبل المقارنة.',
                                              'key_points': ['مصاريف التسيير والمعاملات كتأثر فالربح الصافي اللي كيوصل '
                                                             'للمستثمر.',
                                                             'الصندوق يقدر يوسع التنويع، ولكن النتيجة كتبقى مرتبطة '
                                                             'بالأصول وبطريقة التسيير.'],
                                              'checkpoint': 'شنو المعلومات اللي كتقارن بين جوج صناديق مختلفين '
                                                            'فالمصاريف والسياسة؟'}}},
                  {'module_id': 'intermediate_07',
                   'locales': {'fr/latin': {'title': 'IPO et information financière',
                                            'objective': 'Relier introduction en Bourse, prospectus et information '
                                                         'disponible. À retenir pour ce module : IPO et information '
                                                         'financière.',
                                            'lesson': 'Une IPO donne accès au marché selon un processus documenté; '
                                                      "l'information financière permet d'étudier l'activité et les "
                                                      'risques.',
                                            'key_points': ['Point central : IPO et information financière.',
                                                           "L'apprentissage ne garantit aucun profit."],
                                            'checkpoint': "Pourquoi l'information publiée est-elle centrale lors d'une "
                                                          'IPO ?'},
                               'en/latin': {'title': 'IPO and financial disclosure',
                                            'objective': 'Relate an IPO process to its prospectus and available '
                                                         'information. Module takeaway: IPO and financial disclosure.',
                                            'lesson': 'An IPO opens access to the market through a documented process; '
                                                      'financial information describes activity and risks.',
                                            'key_points': ['Core point: IPO and financial disclosure.',
                                                           'Learning does not guarantee profit.'],
                                            'checkpoint': 'Why is published information central to an IPO?'},
                               'ar/arabic': {'title': 'الإصدار الأولي والإفصاح',
                                             'objective': 'قراءة معلومات الإصدار الأولي لفهم نشاط الشركة ومخاطرها '
                                                          'وشروط الأوراق المعروضة.',
                                             'lesson': 'يقدم الإصدار الأولي فرصة للشركة لجمع التمويل من الجمهور مقابل '
                                                       'أوراق مالية، وتشرح نشرة الإصدار نشاطها وشروط العملية والمخاطر '
                                                       'المعروفة. تساعد هذه المعلومات المستثمر على طرح أسئلة أفضل، '
                                                       'لكنها لا تحول الاستثمار إلى نتيجة مضمونة.',
                                             'key_points': ['يجب التمييز بين الوقائع المنشورة والتوقعات التي تعتمد على '
                                                            'افتراضات الإدارة.',
                                                            'تشمل المراجعة المفيدة نموذج الأعمال والديون واستخدام '
                                                            'الأموال وشروط الاكتتاب.'],
                                             'checkpoint': 'كيف تساعد نشرة الإصدار في فهم المخاطر قبل اتخاذ قرار '
                                                           'تعليمي؟'},
                               'ary/latin': {'title': 'IPO w lma3louma lmaliya',
                                             'objective': 'Rbet bin l2idraj w lma3loumat li katban llmoustathmir. '
                                                          'Khlaa dyal had lmodule: IPO w lma3louma lmaliya.',
                                             'lesson': 'IPO kaydkhel cherka l sou9 b masar mwas9, w lma3louma lmaliya '
                                                       'katbayan nchat w lmkhater.',
                                             'key_points': ['N9ta l2assasiya: IPO w lma3louma lmaliya.',
                                                            'Ta3allom machi daman dyal rbe7.'],
                                             'checkpoint': '3lach lma3louma lm3lna mohimma f IPOs'},
                               'ary/arabic': {'title': 'الإصدار الأولي والنشرة',
                                              'objective': 'فهم شنو كتشرح نشرة الإصدار على نشاط الشركة والشروط '
                                                           'والمخاطر قبل الاكتتاب.',
                                              'lesson': 'الإصدار الأولي كيعطي للشركة إمكانية تجمع التمويل من الجمهور '
                                                        'مقابل وراق مالية، والنشرة كتشرح النشاط والشروط والمخاطر '
                                                        'المعروفة. هاد المعلومات كتعاون المستثمر يطرح أسئلة مزيانة، '
                                                        'ولكن ماكاتضمنش النتيجة.',
                                              'key_points': ['فرق بين الوقائع المنشورة والتوقعات اللي مبنية على '
                                                             'افتراضات الإدارة.',
                                                             'شوف نموذج الخدمة والديون واستعمال الفلوس وشروط الاكتتاب '
                                                             'قبل المقارنة.'],
                                              'checkpoint': 'كيفاش كتعاونك نشرة الإصدار تفهم الخطر قبل قرار تعليمي؟'}}},
                  {'module_id': 'intermediate_08',
                   'locales': {'fr/latin': {'title': "Lecture de l'information de marché",
                                            'objective': 'Distinguer prix, volume, variation et information '
                                                         'fondamentale. À retenir pour ce module : Lecture de '
                                                         "l'information de marché.",
                                            'lesson': 'Une lecture prudente confronte plusieurs indicateurs et leur '
                                                      'date; un mouvement de prix isolé ne suffit pas à conclure.',
                                            'key_points': ["Point central : Lecture de l'information de marché.",
                                                           "L'apprentissage ne garantit aucun profit."],
                                            'checkpoint': 'Pourquoi faut-il replacer un prix dans son contexte ?'},
                               'en/latin': {'title': 'Reading market information',
                                            'objective': 'Distinguish price, volume, change and fundamental '
                                                         'information. Module takeaway: Reading market information.',
                                            'lesson': 'Careful reading compares indicators and their dates; an '
                                                      'isolated price move is not enough for a conclusion.',
                                            'key_points': ['Core point: Reading market information.',
                                                           'Learning does not guarantee profit.'],
                                            'checkpoint': 'Why should a price be read in context?'},
                               'ar/arabic': {'title': 'تحليل المعلومات المالية',
                                             'objective': 'تطوير طريقة عملية لقراءة مصدر البيانات وتاريخها ومؤشرات '
                                                          'السوق قبل تفسير حركة السعر.',
                                             'lesson': 'تبدأ قراءة المعلومة المالية بتحديد مصدرها وتاريخها والسؤال '
                                                       'الذي تجيب عنه. ثم تقارن الأرقام بالسياق، مثل نتائج الشركة وحجم '
                                                       'التداول والأخبار ذات الصلة، حتى لا يتحول رقم منفرد إلى استنتاج '
                                                       'مبالغ فيه.',
                                             'key_points': ['قد يختلف معنى المؤشر نفسه باختلاف الفترة والشركات التي '
                                                            'تتم مقارنتها.',
                                                            'يساعد التحقق من المصدر ووحدة القياس في تجنب قراءة رقم '
                                                            'صحيح بطريقة خاطئة.'],
                                             'checkpoint': 'ما الخطوات التي تتبعها للتأكد من أن معلومة مالية قابلة '
                                                           'للمقارنة؟'},
                               'ary/latin': {'title': '9raya dyal ma3loumat sou9',
                                             'objective': 'Myez bin taman w l7ajm w ttbedel w lma3louma l2assasiya. '
                                                          'Khlaa dyal had lmodule: 9raya dyal ma3loumat sou9.',
                                             'lesson': 'L9raya lma3r9ola kat9aren lmo2achirat w tawarikh, w 7araka '
                                                       'wa7da ma kat3tich natija kamla.',
                                             'key_points': ['N9ta l2assasiya: 9raya dyal ma3loumat sou9.',
                                                            'Ta3allom machi daman dyal rbe7.'],
                                             'checkpoint': '3lach taman khaso y9ra m3a siy9os'},
                               'ary/arabic': {'title': 'قرا معلومات السوق',
                                              'objective': 'تعلم كيفاش تتحقق من المصدر والتاريخ والسياق قبل ماتفسر '
                                                           'حركة الثمن.',
                                              'lesson': 'بدا بتحديد شكون نشر المعلومة وفاش تنشرات وشنو السؤال اللي '
                                                        'كتجاوب عليه. من بعد قارن الأرقام مع نتائج الشركة وحجم التداول '
                                                        'والأخبار المرتبطة، باش مايتحولش رقم واحد لحكم سريع.',
                                              'key_points': ['نفس المؤشر يقدر يعطي معنى مختلف حسب الفترة والشركات اللي '
                                                             'كنقارنوها.',
                                                             'التأكد من المصدر ووحدة القياس كيحمي من فهم رقم صحيح '
                                                             'بطريقة غالطة.'],
                                              'checkpoint': 'شنو الخطوات اللي كتدير باش تتأكد أن المعلومة المالية '
                                                            'قابلة للمقارنة؟'}}}],
 'advanced': [{'module_id': 'advanced_01',
               'locales': {'fr/latin': {'title': 'Microstructure et formation des prix',
                                        'objective': 'Analyser comment le carnet et les règles de priorité participent '
                                                     'au prix. À retenir pour ce module : Microstructure et formation '
                                                     'des prix.',
                                        'lesson': 'La microstructure étudie la rencontre des ordres, la priorité et '
                                                  "l'information disponible dans le carnet.",
                                        'key_points': ['Point central : Microstructure et formation des prix.',
                                                       "L'apprentissage ne garantit aucun profit."],
                                        'checkpoint': 'Comment la priorité des ordres influence-t-elle le prix observé '
                                                      '?'},
                           'en/latin': {'title': 'Market microstructure and price formation',
                                        'objective': 'Analyze how the order book and priority rules contribute to '
                                                     'price formation. Module takeaway: Market microstructure and '
                                                     'price formation.',
                                        'lesson': 'Microstructure studies order interaction, priority and available '
                                                  'information inside the book.',
                                        'key_points': ['Core point: Market microstructure and price formation.',
                                                       'Learning does not guarantee profit.'],
                                        'checkpoint': 'How can order priority influence the observed price?'},
                           'ar/arabic': {'title': 'تشكل الأسعار وبنية السوق',
                                         'objective': 'تحليل تفاعل أوامر الشراء والبيع وفروق الأسعار والعرض والطلب في '
                                                      'تكوين السعر داخل السوق.',
                                         'lesson': 'يتشكل السعر عندما تتقابل أوامر شراء وبيع ذات شروط مختلفة داخل نظام '
                                                   'التداول، فتحدد الأولوية أي الأوامر يمكن أن تتطابق أولا. ويعكس فرق '
                                                   'سعري العرض والطلب تكلفة فورية للتنفيذ، بينما قد تغير الكميات '
                                                   'الكبيرة توازن السوق خلال فترة قصيرة.',
                                         'key_points': ['تؤثر أولوية السعر ثم الزمن في ترتيب الأوامر القابلة للتنفيذ.',
                                                        'لا يساوي السعر الأخير كل المعلومات المتاحة، لأن دفتر الأوامر '
                                                        'يكشف طلبا وعرضا لم يتحققا بعد.'],
                                         'checkpoint': 'كيف تفسر تغير السعر عندما تتراجع أوامر البيع القريبة ويصل أمر '
                                                       'شراء كبير؟'},
                           'ary/latin': {'title': 'Microstructure w kifach kaytchkel taman',
                                         'objective': 'Fhem kifach daftar l2awamir w l2awlawiya kay2etrou 3la taman. '
                                                      'Khlaa dyal had lmodule: Microstructure w kifach kaytchkel '
                                                      'taman.',
                                         'lesson': 'Microstructure katqra tfa3ol l2awamir w l2awlawiya w lma3louma li '
                                                   'f daftar.',
                                         'key_points': ['N9ta l2assasiya: Microstructure w kifach kaytchkel taman.',
                                                        'Ta3allom machi daman dyal rbe7.'],
                                         'checkpoint': 'Kifach l2awlawiya t9der tbdel taman li kanchoufos'},
                           'ary/arabic': {'title': 'كيفاش كيتشكل الثمن',
                                          'objective': 'تحليل كيفاش كيتلاقاو أوامر الشرا والبيع وكيفاش كيأثرو العرض '
                                                       'والطلب والفارق فالثمن.',
                                          'lesson': 'الثمن كيتشكل ملي كتلاقى أوامر الشرا والبيع بشروط مختلفة داخل نظام '
                                                    'التداول، والأولوية كتحدد شنو غادي يتطابق اللول. الفارق بين ثمن '
                                                    'الطلب والعرض كيبين كلفة فورية، والكمية الكبيرة تقدر تبدل توازن '
                                                    'السوق فمدة قصيرة.',
                                          'key_points': ['الأمر اللي عندو ثمن أحسن كيسبق، ومن بعد كيدخل عامل الوقت '
                                                         'فترتيب الأوامر.',
                                                         'الثمن الأخير ماكيشرحش كلشي، حيث دفتر الأوامر فيه طلبات وعروض '
                                                         'باقي ماوصلهاش التنفيذ.'],
                                          'checkpoint': 'كيفاش تفسر تبدل الثمن ملي كتنقص أوامر البيع القريبة وكيجي أمر '
                                                        'شرا كبير؟'}}},
              {'module_id': 'advanced_02',
               'locales': {'fr/latin': {'title': 'Profondeur, liquidité et carnet',
                                        'objective': "Interpréter les niveaux du carnet et leur capacité d'absorption. "
                                                     'À retenir pour ce module : Profondeur, liquidité et carnet.',
                                        'lesson': 'La profondeur montre les quantités disponibles à différents prix; '
                                                  'elle peut changer rapidement avec les annulations.',
                                        'key_points': ['Point central : Profondeur, liquidité et carnet.',
                                                       "L'apprentissage ne garantit aucun profit."],
                                        'checkpoint': "Que révèle la profondeur qu'un dernier prix ne révèle pas ?"},
                           'en/latin': {'title': 'Depth, liquidity and the order book',
                                        'objective': 'Interpret book levels and their capacity to absorb orders. '
                                                     'Module takeaway: Depth, liquidity and the order book.',
                                        'lesson': 'Depth shows available quantities at different prices and can change '
                                                  'quickly when orders are cancelled.',
                                        'key_points': ['Core point: Depth, liquidity and the order book.',
                                                       'Learning does not guarantee profit.'],
                                        'checkpoint': 'What can depth reveal that the last price cannot?'},
                           'ar/arabic': {'title': 'العمق والسيولة ودفتر الأوامر',
                                         'objective': 'تحليل مستويات العمق والإلغاءات وفارق السعر لتقدير الأثر السعري '
                                                      'المتوقع عند تنفيذ كمية.',
                                         'lesson': 'يعرض دفتر الأوامر كميات متاحة عند أسعار متتابعة، ولذلك يكشف العمق '
                                                   'مقدار المقاومة أمام أمر جديد. وقد يبدو السوق عميقا قبل الإلغاء ثم '
                                                   'يضعف بسرعة، كما يمكن لأمر كبير أن يستهلك مستويات متعددة ويرفع '
                                                   'تكلفة التنفيذ.',
                                         'key_points': ['يحتاج تقدير السيولة إلى مراقبة الاستمرارية والإلغاءات، لا إلى '
                                                        'عد الكمية الظاهرة في لحظة واحدة.',
                                                        'يقيس الأثر السعري مقدار ابتعاد سعر التنفيذ عن السعر المرجعي '
                                                        'بسبب حجم الأمر.'],
                                         'checkpoint': 'كيف تميز بين عمق حقيقي وكمية ظاهرة تختفي قبل تنفيذ أمر كبير؟'},
                           'ary/latin': {'title': '3om9 w siyola w daftar l2awamir',
                                         'objective': 'Fhem lmostawayat dyal daftar w ch7al y9der ystao3eb l2awamir. '
                                                      'Khlaa dyal had lmodule: 3om9 w siyola w daftar l2awamir.',
                                         'lesson': 'L3om9 kaybayan lkemyat 3la tamanat mkhtalfa, w y9der yetbedel '
                                                   'bser3a m3a lghaa.',
                                         'key_points': ['N9ta l2assasiya: 3om9 w siyola w daftar l2awamir.',
                                                        'Ta3allom machi daman dyal rbe7.'],
                                         'checkpoint': 'Ash kaybayan l3om9 w taman l2akhir ma kaybayan-chs'},
                           'ary/arabic': {'title': 'العمق ودفتر الأوامر',
                                          'objective': 'تحليل العمق والإلغاءات والفارق بين الشرا والبيع باش نقدر الأثر '
                                                       'ديال كمية كبيرة.',
                                          'lesson': 'دفتر الأوامر كيعرض الكميات فمستويات أثمنة متتابعة، وكيبين شحال '
                                                    'كاين من مقاومة قدام أمر جديد. السوق يقدر يبان عامر قبل الإلغاء '
                                                    'ومن بعد يضعف، والأمر الكبير يقدر ياكل بزاف ديال المستويات ويرفع '
                                                    'كلفة التنفيذ.',
                                          'key_points': ['تقدير السيولة خاصو يتبع الاستمرار والإلغاءات، وماشي غير '
                                                         'الكمية اللي باينة فواحد اللحظة.',
                                                         'الأثر السعري هو الفرق بين ثمن التنفيذ والثمن المرجعي بسبب '
                                                         'حجم الأمر.'],
                                          'checkpoint': 'كيفاش تفرق بين عمق حقيقي وكمية باينة كتختفي قبل تنفيذ أمر '
                                                        'كبير؟'}}},
              {'module_id': 'advanced_03',
               'locales': {'fr/latin': {'title': 'Mécanismes avancés des ordres',
                                        'objective': "Examiner les effets des conditions, délais et priorités d'un "
                                                     'ordre. À retenir pour ce module : Mécanismes avancés des ordres.',
                                        'lesson': "Les conditions d'exécution déterminent quand un ordre devient "
                                                  'négociable et comment il interagit avec les autres.',
                                        'key_points': ['Point central : Mécanismes avancés des ordres.',
                                                       "L'apprentissage ne garantit aucun profit."],
                                        'checkpoint': 'Quels mécanismes peuvent empêcher une exécution immédiate ?'},
                           'en/latin': {'title': 'Advanced order mechanics',
                                        'objective': 'Examine how conditions, timing and priority affect an order. '
                                                     'Module takeaway: Advanced order mechanics.',
                                        'lesson': 'Execution conditions determine when an order becomes tradable and '
                                                  'how it interacts with other orders.',
                                        'key_points': ['Core point: Advanced order mechanics.',
                                                       'Learning does not guarantee profit.'],
                                        'checkpoint': 'Which mechanics can prevent immediate execution?'},
                           'ar/arabic': {'title': 'آليات الأوامر المتقدمة',
                                         'objective': 'تحليل شروط التنفيذ والأولوية وتفاعل الأوامر المشروطة مع حالة '
                                                      'السوق وأسعارها المتغيرة.',
                                         'lesson': 'لا يدخل الأمر المشروط إلى التنفيذ الفعلي إلا بعد تحقق شرطه، ثم '
                                                   'يخضع لقواعد الأولوية والسيولة المتاحة في تلك اللحظة. ويمكن للأوامر '
                                                   'المتعاكسة أو أوامر الإيقاف أن تغير تدفق الطلبات عندما ينتقل السعر '
                                                   'عبر عتبة محددة.',
                                         'key_points': ['تتأثر نتيجة الأمر بالشرط والزمن والسعر والكمية، وليس باسم '
                                                        'الأمر وحده.',
                                                        'قد يتحقق شرط الأمر في سوق سريع ثم ينفذ بسعر مختلف عن السعر '
                                                        'الذي فعّل الشرط.'],
                                         'checkpoint': 'كيف يمكن لتغير حالة السوق بين تفعيل الشرط والتنفيذ أن يغير '
                                                       'النتيجة؟'},
                           'ary/latin': {'title': 'Mikanizmat mta9dmin dyal l2awamir',
                                         'objective': '7ll kifach chourout w wa9t w l2awlawiya kay2etrou 3la l2amr. '
                                                      'Khlaa dyal had lmodule: Mikanizmat mta9dmin dyal l2awamir.',
                                         'lesson': 'Chourout ttanfid kat7edded imta l2amr y9der yetnffed w kifach '
                                                   'kaytla9a m3a l2awamir.',
                                         'key_points': ['N9ta l2assasiya: Mikanizmat mta9dmin dyal l2awamir.',
                                                        'Ta3allom machi daman dyal rbe7.'],
                                         'checkpoint': 'Ash y9der y7bes ttanfid f l7ins'},
                           'ary/arabic': {'title': 'الأوامر المتقدمة',
                                          'objective': 'تحليل شروط التنفيذ والأولوية وكيفاش كيتفاعلو الأوامر المشروطة '
                                                       'مع حالة السوق.',
                                          'lesson': 'الأمر المشروط ماكيدخلش للتنفيذ حتى كيتحقق الشرط، ومن بعد كيتطبق '
                                                    'عليه ترتيب الأولوية والسيولة اللي كاينة فداك الوقت. أوامر الإيقاف '
                                                    'والأوامر المتعاكسة تقدر تبدل تدفق الطلبات ملي كيدوز الثمن من '
                                                    'العتبة.',
                                          'key_points': ['النتيجة كتتأثر بالشرط والوقت والثمن والكمية، وماشي غير باسم '
                                                         'الأمر.',
                                                         'فالسوق السريع يقدر الثمن يتبدل بين لحظة تحقق الشرط ولحظة '
                                                         'التنفيذ.'],
                                          'checkpoint': 'كيفاش يقدر تبدل حالة السوق بين التفعيل والتنفيذ يغير '
                                                        'النتيجة؟'}}},
              {'module_id': 'advanced_04',
               'locales': {'fr/latin': {'title': 'Financement par les marchés de capitaux',
                                        'objective': 'Relier besoins de financement, instruments et information '
                                                     'fournie. À retenir pour ce module : Financement par les marchés '
                                                     'de capitaux.',
                                        'lesson': "Le financement de marché expose l'entreprise aux exigences de "
                                                  "transparence et au choix d'un instrument adapté.",
                                        'key_points': ['Point central : Financement par les marchés de capitaux.',
                                                       "L'apprentissage ne garantit aucun profit."],
                                        'checkpoint': 'Pourquoi le financement de marché exige-t-il une information '
                                                      'détaillée ?'},
                           'en/latin': {'title': 'Corporate financing through capital markets',
                                        'objective': 'Relate funding needs, instruments and required disclosure. '
                                                     'Module takeaway: Corporate financing through capital markets.',
                                        'lesson': 'Market financing exposes a company to transparency requirements and '
                                                  'to choosing an appropriate instrument.',
                                        'key_points': ['Core point: Corporate financing through capital markets.',
                                                       'Learning does not guarantee profit.'],
                                        'checkpoint': 'Why does market financing require detailed information?'},
                           'ar/arabic': {'title': 'تمويل الشركات عبر السوق',
                                         'objective': 'مقارنة تمويل الشركات بالأسهم أو بالدين وتحليل تكلفة التمويل '
                                                      'والإفصاح والآثار المترتبة.',
                                         'lesson': 'يتيح إصدار الأسهم للشركة جمع رأسمال من دون التزام بفائدة ثابتة، '
                                                   'لكنه يوزع الملكية بين مساهمين جدد. أما إصدار الدين فيحافظ على نسب '
                                                   'الملكية لكنه يضيف التزامات بالسداد، ولذلك يجب تحليل الكلفة والقدرة '
                                                   'المالية والإفصاح معا.',
                                         'key_points': ['يعكس اختيار الأداة مفاضلة بين تخفيف الملكية وتحمل التزامات '
                                                        'مالية مستقبلية.',
                                                        'يحتاج المستثمر إلى فهم استخدام الأموال وشروط الإصدار قبل '
                                                        'مقارنة العائد المعلن.'],
                                         'checkpoint': 'ما المفاضلة التي تظهر عندما تختار الشركة بين إصدار أسهم وإصدار '
                                                       'سندات؟'},
                           'ary/latin': {'title': 'Tamwil cherkat b sou9 lmal',
                                         'objective': 'Rbet bin l7aja lttamwil w naw3 l2ada w lma3louma. Khlaa dyal '
                                                      'had lmodule: Tamwil cherkat b sou9 lmal.',
                                         'lesson': 'Tamwil b sou9 kay7taj chfafiya w ikhtiyar ada mnasba l7aja dyal '
                                                   'cherka.',
                                         'key_points': ['N9ta l2assasiya: Tamwil cherkat b sou9 lmal.',
                                                        'Ta3allom machi daman dyal rbe7.'],
                                         'checkpoint': '3lach sou9 lmal kay7taj ma3louma mfaslas'},
                           'ary/arabic': {'title': 'تمويل الشركات من السوق',
                                          'objective': 'مقارنة تمويل الشركة بالأسهم ولا بالدين وتحليل الكلفة والإفصاح '
                                                       'والآثار على المساهمين.',
                                          'lesson': 'إصدار الأسهم كيعاون الشركة تجمع الرأسمال بلا فائدة ثابتة، ولكن '
                                                    'كيدخل ملاك جدد وكيقسم الملكية. إصدار الدين كيحافظ على نسب الملكية '
                                                    'وكيزيد واجبات الأداء، وداكشي علاش خاص نقراو الكلفة والقدرة '
                                                    'المالية والإفصاح مجموعين.',
                                          'key_points': ['الاختيار كيبين المفاضلة بين نقصان نسبة الملكية وتحمل واجبات '
                                                         'مالية جاية.',
                                                         'قبل المقارنة خاص المستثمر يفهم فين غادي تمشي الفلوس وشنو '
                                                         'شروط الإصدار.'],
                                          'checkpoint': 'شنو المفاضلة اللي كتظهر ملي كتختار الشركة بين الأسهم '
                                                        'والسندات؟'}}},
              {'module_id': 'advanced_05',
               'locales': {'fr/latin': {'title': 'Augmentations de capital et opérations',
                                        'objective': "Comprendre droits préférentiels, dilution et calendrier d'une "
                                                     'opération. À retenir pour ce module : Augmentations de capital '
                                                     'et opérations.',
                                        'lesson': 'Une augmentation peut apporter des fonds mais modifier la part '
                                                  'relative des actionnaires selon les droits exercés.',
                                        'key_points': ['Point central : Augmentations de capital et opérations.',
                                                       "L'apprentissage ne garantit aucun profit."],
                                        'checkpoint': 'Comment une augmentation de capital peut-elle créer une '
                                                      'dilution ?'},
                           'en/latin': {'title': 'Capital increases and corporate actions',
                                        'objective': 'Understand pre-emption rights, dilution and transaction timing. '
                                                     'Module takeaway: Capital increases and corporate actions.',
                                        'lesson': "A capital increase can provide funds while changing shareholders' "
                                                  'relative ownership depending on exercised rights.',
                                        'key_points': ['Core point: Capital increases and corporate actions.',
                                                       'Learning does not guarantee profit.'],
                                        'checkpoint': 'How can a capital increase create dilution?'},
                           'ar/arabic': {'title': 'زيادة رأس المال وإعادة الهيكلة',
                                         'objective': 'تحليل أثر إصدار أسهم جديدة وحقوق الأولوية والتخفيف في حصة '
                                                      'المساهم وبنية الشركة.',
                                         'lesson': 'تزيد الشركة رأسمالها عندما تحتاج إلى تمويل مشروع أو تقوية '
                                                   'ميزانيتها، وقد تمنح المساهمين الحاليين حق الأولوية للمشاركة. إذا '
                                                   'لم يشارك المساهم فقد تنخفض نسبته من التصويت والأرباح، ويتوقف الأثر '
                                                   'الاقتصادي على سعر الإصدار واستخدام الأموال.',
                                         'key_points': ['يقيس التخفيف تغير نسبة الملكية وليس مجرد عدد الأسهم الجديدة.',
                                                        'تكشف شروط العملية إن كان التمويل موجها للنمو أو لتغطية '
                                                        'التزامات قائمة.'],
                                         'checkpoint': 'كيف تقارن أثر زيادة رأس المال على مساهم يشارك فيها مع أثرها '
                                                       'على مساهم لا يشارك؟'},
                           'ary/latin': {'title': 'Zyada f rass lmal w 3amaliyat',
                                         'objective': 'Fhem 7o9o9 l2awlawiya w ttakhfif w wa9t l3amaliya. Khlaa dyal '
                                                      'had lmodule: Zyada f rass lmal w 3amaliyat.',
                                         'lesson': 'Zyada t9der tjib flous w tbdel nssib dyal lmoulak 7sab l7o9o9 li '
                                                   'tsta3mlo.',
                                         'key_points': ['N9ta l2assasiya: Zyada f rass lmal w 3amaliyat.',
                                                        'Ta3allom machi daman dyal rbe7.'],
                                         'checkpoint': 'Kifach t9der zyadat rass lmal tdir tkhfifs'},
                           'ary/arabic': {'title': 'زيادة الرأسمال وإعادة الهيكلة',
                                          'objective': 'تحليل أثر الأسهم الجديدة وحق الأولوية والتخفيف على حصة المساهم '
                                                       'وبنية الشركة.',
                                          'lesson': 'الشركة كتزيد الرأسمال ملي كتحتاج تمول مشروع ولا تقوي الوضع '
                                                    'المالي، وقد تعطي للمساهمين القدامى حق الأولوية. إلا ماشاركش '
                                                    'المساهم، النسبة ديالو فالتصويت والأرباح تقدر تنقص، والأثر كيرتبط '
                                                    'بثمن الإصدار وباستعمال الفلوس.',
                                          'key_points': ['التخفيف كيقيس تبدل نسبة الملكية، وماشي غير عدد الأسهم اللي '
                                                         'تزادو.',
                                                         'شروط العملية كتعاون نعرفو واش التمويل للنمو ولا لتغطية '
                                                         'التزامات قديمة.'],
                                          'checkpoint': 'كيفاش تقارن أثر الزيادة على مساهم شارك فيها مع مساهم '
                                                        'ماشاركش؟'}}},
              {'module_id': 'advanced_06',
               'locales': {'fr/latin': {'title': "Analyse de l'information financière",
                                        'objective': "Évaluer cohérence, période et limites d'une information publiée. "
                                                     "À retenir pour ce module : Analyse de l'information financière.",
                                        'lesson': "L'analyse compare périodes, indicateurs et notes; elle distingue "
                                                  'donnée observée, hypothèse et incertitude.',
                                        'key_points': ["Point central : Analyse de l'information financière.",
                                                       "L'apprentissage ne garantit aucun profit."],
                                        'checkpoint': 'Pourquoi les notes financières complètent-elles les chiffres ?'},
                           'en/latin': {'title': 'Financial information and disclosure analysis',
                                        'objective': 'Assess consistency, period and limits of published information. '
                                                     'Module takeaway: Financial information and disclosure analysis.',
                                        'lesson': 'Analysis compares periods, indicators and notes while separating '
                                                  'observed data, assumptions and uncertainty.',
                                        'key_points': ['Core point: Financial information and disclosure analysis.',
                                                       'Learning does not guarantee profit.'],
                                        'checkpoint': 'Why do financial notes complement the numbers?'},
                           'ar/arabic': {'title': 'تحليل الإفصاح والقوائم المالية',
                                         'objective': 'تمييز الوقائع المفصح عنها عن الافتراضات وتحليل القوائم '
                                                      'والمؤشرات ضمن سياق الشركة.',
                                         'lesson': 'تقدم القوائم المالية بيانات عن الإيرادات والديون والتدفقات، لكن '
                                                   'تفسيرها يتطلب معرفة الفترة والسياسة المحاسبية والعوامل غير '
                                                   'المتكررة. ويقارن التحليل المتين بين ما أعلنته الشركة وما يمكن '
                                                   'استنتاجه، من دون تحويل التوقع إلى حقيقة.',
                                         'key_points': ['قد يخفي نمو الإيرادات تراجع الهامش أو ارتفاع الديون، لذلك '
                                                        'يلزم ربط المؤشرات ببعضها.',
                                                        'تساعد ملاحظات القوائم في فصل الحدث الاستثنائي عن الأداء '
                                                        'المتكرر.'],
                                         'checkpoint': 'كيف تفرق في تقرير مالي بين واقعة معلنة واستنتاج يعتمد على '
                                                       'افتراض؟'},
                           'ary/latin': {'title': 'T7lil lma3louma lmaliya',
                                         'objective': '9aren bin l2ar9am w lftrat w l2idahat w lya9in. Khlaa dyal had '
                                                      'lmodule: T7lil lma3louma lmaliya.',
                                         'lesson': 'T7lil kay9aren lmo2achirat w kayferr9 bin lma3louma w lfardiya w '
                                                   'chno ma mazal majhoul.',
                                         'key_points': ['N9ta l2assasiya: T7lil lma3louma lmaliya.',
                                                        'Ta3allom machi daman dyal rbe7.'],
                                         'checkpoint': '3lach l2idahat katzid tfasser l2ar9ams'},
                           'ary/arabic': {'title': 'تحليل التقارير والإفصاح',
                                          'objective': 'تمييز الوقائع المنشورة على الافتراضات وتحليل القوائم والمؤشرات '
                                                       'داخل سياق الشركة.',
                                          'lesson': 'القوائم المالية كتعطي أرقام على المداخيل والديون والتدفقات، ولكن '
                                                    'فهمها كيحتاج الفترة والسياسة المحاسبية والعوامل غير العادية. '
                                                    'التحليل المزيان كيفرق بين شنو قالت الشركة وشنو نقدر نستنتجو، '
                                                    'وماكيحولش التوقع لحقيقة.',
                                          'key_points': ['نمو المداخيل يقدر يخبي نقص الهامش ولا ارتفاع الدين، وخص '
                                                         'المؤشرات تتقرا مجموعين.',
                                                         'ملاحظات القوائم كتعاون نفرقو الحدث الاستثنائي على الأداء '
                                                         'اللي كيتعاود.'],
                                          'checkpoint': 'كيفاش تفرق فالتقرير بين واقعة معلنة واستنتاج مبني على '
                                                        'افتراض؟'}}},
              {'module_id': 'advanced_07',
               'locales': {'fr/latin': {'title': 'Risque de portefeuille',
                                        'objective': 'Analyser contribution, concentration et dépendance entre '
                                                     'positions. À retenir pour ce module : Risque de portefeuille.',
                                        'lesson': 'Le risque de portefeuille dépend des expositions et de leurs '
                                                  "relations; l'analyse reste éducative et ne prescrit pas "
                                                  "d'allocation.",
                                        'key_points': ['Point central : Risque de portefeuille.',
                                                       "L'apprentissage ne garantit aucun profit."],
                                        'checkpoint': "Pourquoi deux positions ne s'additionnent-elles pas toujours "
                                                      'simplement ?'},
                           'en/latin': {'title': 'Portfolio risk concepts',
                                        'objective': 'Analyze contribution, concentration and dependence among '
                                                     'positions. Module takeaway: Portfolio risk concepts.',
                                        'lesson': 'Portfolio risk depends on exposures and their relationships; this '
                                                  'educational analysis does not prescribe an allocation.',
                                        'key_points': ['Core point: Portfolio risk concepts.',
                                                       'Learning does not guarantee profit.'],
                                        'checkpoint': 'Why do two positions not always add up in a simple way?'},
                           'ar/arabic': {'title': 'مفاهيم مخاطر المحفظة',
                                         'objective': 'تحليل حدود التنويع والارتباط وتجميع المخاطر داخل محفظة من منظور '
                                                      'تعليمي غير شخصي.',
                                         'lesson': 'لا تتساوى مخاطر المحفظة مع مجموع مخاطر أصولها لأن العلاقة بينها قد '
                                                   'تخفف التقلب أو تزيده. ويقيس الارتباط كيف تتحرك الأصول معا في '
                                                   'بيانات تاريخية، لكنه لا يضمن استمرار النمط عندما تتغير ظروف السوق.',
                                         'key_points': ['قد يفشل التنويع إذا كانت الأصول ترتفع وتهبط معا أثناء ضغط '
                                                        'عام.',
                                                        'يجب التمييز بين مقياس تاريخي للمخاطر وبين نتيجة مستقبلية لا '
                                                        'يمكن ضمانها.'],
                                         'checkpoint': 'لماذا قد لا يحمي تنويع ظاهري محفظة من صدمة تؤثر في أصولها '
                                                       'كلها؟'},
                           'ary/latin': {'title': 'Mkhater dyal lma7fada',
                                         'objective': 'Fhem ta2tir ttarkiz w l3ala9at bin lmorakazat. Khlaa dyal had '
                                                      'lmodule: Mkhater dyal lma7fada.',
                                         'lesson': 'Mkhater lma7fada kayt3alla9o b lta3arrod w l3ala9a bin lmorakazat, '
                                                   'bla tawsiya ta9sim.',
                                         'key_points': ['N9ta l2assasiya: Mkhater dyal lma7fada.',
                                                        'Ta3allom machi daman dyal rbe7.'],
                                         'checkpoint': '3lach juj morakazat ma kaytjam3och dima b tari9a basitas'},
                           'ary/arabic': {'title': 'مخاطر المحفظة والارتباط',
                                          'objective': 'تحليل حدود التنويع والارتباط وتجميع الخطر فمحفظة بطريقة '
                                                       'تعليمية وماشي نصيحة شخصية.',
                                          'lesson': 'مخاطر المحفظة ماشي بالضرورة مجموع مخاطر الأصول، حيث العلاقة بينها '
                                                    'تقدر تنقص التقلب ولا تزيدو. الارتباط كيقيس كيفاش تحركو الأصول '
                                                    'فالماضي، ولكن ماكيضمنش يبقى نفس النمط ملي كتتبدل ظروف السوق.',
                                          'key_points': ['التنويع يقدر يفشل إلا كانت الأصول كلها كتطلع وتهبط مع نفس '
                                                         'الصدمة.',
                                                         'خاص نفرقو بين مقياس تاريخي للخطر وبين نتيجة مستقبلية مايمكنش '
                                                         'نضمنوها.'],
                                          'checkpoint': 'علاش التنويع اللي باين مزيان يقدر مايحميش من صدمة كتأثر '
                                                        'فالأصول كلها؟'}}},
              {'module_id': 'advanced_08',
               'locales': {'fr/latin': {'title': 'Écosystème avancé du marché marocain',
                                        'objective': 'Relier infrastructure, régulation, intermédiaires et émetteurs. '
                                                     'À retenir pour ce module : Écosystème avancé du marché marocain.',
                                        'lesson': "L'écosystème marocain fonctionne par des responsabilités "
                                                  'distribuées entre acteurs, règles de marché et dispositifs '
                                                  "d'information.",
                                        'key_points': ['Point central : Écosystème avancé du marché marocain.',
                                                       "L'apprentissage ne garantit aucun profit."],
                                        'checkpoint': 'Comment les responsabilités distribuées soutiennent-elles la '
                                                      'confiance du marché ?'},
                           'en/latin': {'title': 'Advanced Moroccan market ecosystem',
                                        'objective': 'Relate infrastructure, regulation, intermediaries and issuers. '
                                                     'Module takeaway: Advanced Moroccan market ecosystem.',
                                        'lesson': 'The Moroccan ecosystem distributes responsibilities among market '
                                                  'actors, rules and information systems.',
                                        'key_points': ['Core point: Advanced Moroccan market ecosystem.',
                                                       'Learning does not guarantee profit.'],
                                        'checkpoint': 'How do distributed responsibilities support market confidence?'},
                           'ar/arabic': {'title': 'منظومة سوق رأس المال المغربي',
                                         'objective': 'تحليل أدوار البورصة والهيئات والوسطاء والبنية التحتية في تنظيم '
                                                      'السوق المغربي.',
                                         'lesson': 'تتوزع مسؤوليات السوق بين مؤسسات تشرف على القواعد والرقابة، وبورصة '
                                                   'تنظم التداول، وشركات مدرجة ووسطاء وأنظمة تسوية تحفظ سجل الملكية. '
                                                   'ويساعد فهم هذه الأدوار على قراءة الإفصاح ومسار الأمر من دون اختزال '
                                                   'المنظومة في جهة واحدة.',
                                         'key_points': ['تختلف وظيفة وضع القواعد والرقابة عن وظيفة استقبال الأوامر '
                                                        'وتنفيذ التداول.',
                                                        'تربط البنية التحتية بين التداول والتسوية وحفظ الحقوق بعد '
                                                        'إتمام الصفقة.'],
                                         'checkpoint': 'كيف تشرح تفاعل المؤسسات والوسطاء والتسوية في حماية انتظام '
                                                       'السوق؟'},
                           'ary/latin': {'title': 'Manzomat sou9 lmghrib mta9dma',
                                         'objective': 'Rbet bin lbinya w tanzim w lwosta w lmossdirin. Khlasa dyal had '
                                                      'lmodule: Manzomat sou9 lmghrib mta9dma.',
                                         'lesson': 'Manzoma lmghrib kat9sem lmas2ouliya bin lfa3ilin w l9awanin w '
                                                   'nedom lma3louma.',
                                         'key_points': ['N9ta l2assasiya: Manzomat sou9 lmghrib mta9dma.',
                                                        'Ta3allom machi daman dyal rbe7.'],
                                         'checkpoint': 'Kifach had lmas2ouliya kat3awn tziid tti9as'},
                           'ary/arabic': {'title': 'منظومة السوق المالي المغربي',
                                          'objective': 'تحليل أدوار البورصة والهيئات والوسطاء والتسوية فتنظيم السوق '
                                                       'المالي المغربي.',
                                          'lesson': 'المسؤوليات كتتقسم بين هيئات كتراقب القواعد، وبورصة كتسير التداول، '
                                                    'وشركات ووسطاء وأنظمة تسوية كتحفظ الملكية. فهم هاد الأدوار كيساعد '
                                                    'نقراو الإفصاح ونتبعو مسار الأمر، وما نختزلوش السوق فجهة وحدة.',
                                          'key_points': ['وضع القواعد والرقابة ماشي هو نفس وظيفة استقبال الأمر وتنفيذ '
                                                         'التداول.',
                                                         'البنية التحتية كتربط التداول بالتسوية وحفظ الحقوق من بعد '
                                                         'الصفقة.'],
                                          'checkpoint': 'كيفاش كتشرح تفاعل الهيئات والوسطاء والتسوية باش يبقى السوق '
                                                        'منظم؟'}}}]}
