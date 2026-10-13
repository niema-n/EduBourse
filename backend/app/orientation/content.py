# ruff: noqa
from types import MappingProxyType

LOCALES = ('fr/latin', 'en/latin', 'ar/arabic', 'ary/latin', 'ary/arabic')
TOPIC_LABELS = MappingProxyType({
 'market_basics': MappingProxyType({'fr/latin':'les bases des marchés financiers','en/latin':'financial-market fundamentals','ar/arabic':'أساسيات الأسواق المالية','ary/latin':'l2assassiyat dyal l aswa9 lmaliya','ary/arabic':'أساسيات الأسواق المالية'}),
 'stocks_bonds': MappingProxyType({'fr/latin':'les actions et les obligations','en/latin':'stocks and bonds','ar/arabic':'الأسهم والسندات','ary/latin':'s-siham w ssnadat','ary/arabic':'الأسهم والسندات'}),
 'orders': MappingProxyType({'fr/latin':'les ordres de marché','en/latin':'market orders','ar/arabic':'أوامر السوق','ary/latin':'l2awamir dyal sou9','ary/arabic':'أوامر السوق'}),
 'risk_return': MappingProxyType({'fr/latin':'le risque et le rendement','en/latin':'risk and return','ar/arabic':'المخاطر والعائد','ary/latin':'lkhatar w l3a2id','ary/arabic':'المخاطر والعائد'}),
 'bond': MappingProxyType({'fr/latin':'les obligations','en/latin':'bonds','ar/arabic':'السندات','ary/latin':'ssnadat','ary/arabic':'السندات'}),
 'corporate_action': MappingProxyType({'fr/latin':'les opérations sur titres','en/latin':'corporate actions','ar/arabic':'إجراءات الشركات','ary/latin':'l2ijra2at dyal cherkat','ary/arabic':'إجراءات الشركات'}),
 'disclosure': MappingProxyType({'fr/latin':'la communication financière','en/latin':'financial disclosure','ar/arabic':'الإفصاح المالي','ary/latin':'l ifsa7 lmali','ary/arabic':'الإفصاح المالي'}),
 'diversification': MappingProxyType({'fr/latin':'la diversification','en/latin':'diversification','ar/arabic':'التنويع','ary/latin':'t-tanwi3','ary/arabic':'التنويع'}),
 'diversification_application': MappingProxyType({'fr/latin':'la mise en pratique de la diversification','en/latin':'applied diversification','ar/arabic':'تطبيق التنويع','ary/latin':'tatbi9 t-tanwi3','ary/arabic':'تطبيق التنويع'}),
 'dividend': MappingProxyType({'fr/latin':'les dividendes','en/latin':'dividends','ar/arabic':'الأرباح الموزعة','ary/latin':'l arbah lmowazza3a','ary/arabic':'الأرباح الموزعة'}),
 'financial_analysis': MappingProxyType({'fr/latin':"l'analyse financière",'en/latin':'financial analysis','ar/arabic':'التحليل المالي','ary/latin':'t-tahlil lmali','ary/arabic':'التحليل المالي'}),
 'horizon': MappingProxyType({'fr/latin':"l'horizon d'apprentissage",'en/latin':'learning horizon','ar/arabic':'أفق التعلم','ary/latin':'of9 ta3allom','ary/arabic':'أفق التعلم'}),
 'index': MappingProxyType({'fr/latin':'les indices','en/latin':'indexes','ar/arabic':'المؤشرات','ary/latin':'lmo2achirat','ary/arabic':'المؤشرات'}),
 'investor': MappingProxyType({'fr/latin':'le rôle de l’investisseur','en/latin':'the investor role','ar/arabic':'دور المستثمر','ary/latin':'dawr lmoustathmir','ary/arabic':'دور المستثمر'}),
 'ipo': MappingProxyType({'fr/latin':"l'introduction en Bourse",'en/latin':'initial public offerings','ar/arabic':'الطرح العام الأولي','ary/latin':'ttar7 l3am l2awali','ary/arabic':'الطرح العام الأولي'}),
 'ipo_disclosure': MappingProxyType({'fr/latin':'la communication d’une introduction en Bourse','en/latin':'IPO disclosure','ar/arabic':'الإفصاح عن الطرح العام','ary/latin':'ifsa7 dyal ttar7 l3am','ary/arabic':'الإفصاح عن الطرح العام'}),
 'ipo_mechanism': MappingProxyType({'fr/latin':'le mécanisme d’introduction en Bourse','en/latin':'IPO mechanism','ar/arabic':'آلية الطرح العام','ary/latin':'kifach kaydouz ttar7 l3am','ary/arabic':'آلية الطرح العام'}),
 'limit_order': MappingProxyType({'fr/latin':'les ordres à cours limité','en/latin':'limit orders','ar/arabic':'الأوامر المحددة السعر','ary/latin':'l2awamir b taman m7added','ary/arabic':'الأوامر المحددة السعر'}),
 'liquidity_risk': MappingProxyType({'fr/latin':'le risque de liquidité','en/latin':'liquidity risk','ar/arabic':'مخاطر السيولة','ary/latin':'khatar dyal ssyoula','ary/arabic':'مخاطر السيولة'}),
 'market_order': MappingProxyType({'fr/latin':'les ordres au marché','en/latin':'market orders','ar/arabic':'أوامر السوق','ary/latin':'l2awamir dyal sou9','ary/arabic':'أوامر السوق'}),
 'market_rules': MappingProxyType({'fr/latin':'les règles du marché','en/latin':'market rules','ar/arabic':'قواعد السوق','ary/latin':'9awa3ed sou9','ary/arabic':'قواعد السوق'}),
 'market_structure': MappingProxyType({'fr/latin':'la structure du marché','en/latin':'market structure','ar/arabic':'هيكلة السوق','ary/latin':'haykal sou9','ary/arabic':'هيكلة السوق'}),
 'opcvm': MappingProxyType({'fr/latin':'les OPCVM','en/latin':'mutual funds','ar/arabic':'هيئات التوظيف الجماعي','ary/latin':'hay2at tawdif ljam3i','ary/arabic':'هيئات التوظيف الجماعي'}),
 'opcvm_value': MappingProxyType({'fr/latin':'la valeur d’un OPCVM','en/latin':'fund value','ar/arabic':'قيمة هيئة التوظيف الجماعي','ary/latin':'9imat hay2at tawdif ljam3i','ary/arabic':'قيمة هيئة التوظيف الجماعي'}),
 'participant_roles': MappingProxyType({'fr/latin':'les rôles des intervenants','en/latin':'participant roles','ar/arabic':'أدوار المتدخلين','ary/latin':'adwar lmoutadakhilin','ary/arabic':'أدوار المتدخلين'}),
 'participants': MappingProxyType({'fr/latin':'les participants du marché','en/latin':'market participants','ar/arabic':'المشاركون في السوق','ary/latin':'lmoutadakhilin f sou9','ary/arabic':'المشاركون في السوق'}),
 'primary_intro': MappingProxyType({'fr/latin':'le marché primaire','en/latin':'primary market introduction','ar/arabic':'السوق الأولية','ary/latin':'sou9 l2awaliya','ary/arabic':'السوق الأولية'}),
 'primary_secondary_markets': MappingProxyType({'fr/latin':'les marchés primaire et secondaire','en/latin':'primary and secondary markets','ar/arabic':'السوق الأولية والثانوية','ary/latin':'sou9 l2awaliya w t-tanawiya','ary/arabic':'السوق الأولية والثانوية'}),
 'return': MappingProxyType({'fr/latin':'le rendement','en/latin':'return','ar/arabic':'العائد','ary/latin':'l3a2id','ary/arabic':'العائد'}),
 'risk': MappingProxyType({'fr/latin':'le risque financier','en/latin':'financial risk','ar/arabic':'المخاطر المالية','ary/latin':'lmokhatara lmaliya','ary/arabic':'المخاطر المالية'}),
 'risk_return_application': MappingProxyType({'fr/latin':'la mise en pratique du risque et du rendement','en/latin':'applied risk and return','ar/arabic':'تطبيق المخاطر والعائد','ary/latin':'tatbi9 lkhatar w l3a2id','ary/arabic':'تطبيق المخاطر والعائد'}),
 'secondary_market': MappingProxyType({'fr/latin':'le marché secondaire','en/latin':'secondary market','ar/arabic':'السوق الثانوية','ary/latin':'sou9 t-tanawiya','ary/arabic':'السوق الثانوية'}),
 'securities_operation': MappingProxyType({'fr/latin':'les opérations sur valeurs mobilières','en/latin':'securities operations','ar/arabic':'عمليات الأوراق المالية','ary/latin':'l3amaliyat 3la l2awraq lmaliya','ary/arabic':'عمليات الأوراق المالية'}),
 'stock': MappingProxyType({'fr/latin':'les actions','en/latin':'stocks','ar/arabic':'الأسهم','ary/latin':'ssiham','ary/arabic':'الأسهم'}),
 'stock_bond_context': MappingProxyType({'fr/latin':'le contexte des actions et obligations','en/latin':'stock and bond context','ar/arabic':'سياق الأسهم والسندات','ary/latin':'s-siya9 dyal ssiham w ssnadat','ary/arabic':'سياق الأسهم والسندات'}),
 'stock_exchange': MappingProxyType({'fr/latin':'la Bourse','en/latin':'stock exchange','ar/arabic':'البورصة','ary/latin':'lborsa','ary/arabic':'البورصة'}),
 'stocks_bonds': MappingProxyType({'fr/latin':'les actions et obligations','en/latin':'stocks and bonds','ar/arabic':'الأسهم والسندات','ary/latin':'ssiham w ssnadat','ary/arabic':'الأسهم والسندات'}),
 'volatility': MappingProxyType({'fr/latin':'la volatilité','en/latin':'volatility','ar/arabic':'التقلب','ary/latin':'t-ta9allob','ary/arabic':'التقلب'}),
})
LEVEL_LABELS = MappingProxyType({
 'fr/latin': MappingProxyType({'beginner':'débutant','intermediate':'intermédiaire','advanced':'avancé'}),
 'en/latin': MappingProxyType({'beginner':'beginner','intermediate':'intermediate','advanced':'advanced'}),
 'ar/arabic': MappingProxyType({'beginner':'مبتدئ','intermediate':'متوسط','advanced':'متقدم'}),
 'ary/latin': MappingProxyType({'beginner':'moubtadi','intermediate':'moutawassit','advanced':'mouta9addem'}),
 'ary/arabic': MappingProxyType({'beginner':'مبتدئ','intermediate':'متوسط','advanced':'متقدم'}),
})
_UNKNOWN_TOPIC_LABELS = MappingProxyType({
    'fr/latin': 'ce sujet',
    'en/latin': 'this topic',
    'ar/arabic': 'هذا الموضوع',
    'ary/latin': 'had lmawdo3',
    'ary/arabic': 'هاد الموضوع',
})
_MESSAGES = MappingProxyType({
 'diagnostic': MappingProxyType({'fr/latin':"Votre niveau d'apprentissage n'est pas encore établi. Je propose le quiz diagnostique existant de six questions.",'en/latin':'Your learning level is not established yet. I recommend the existing six-question diagnostic quiz.','ar/arabic':'لم يتحدد مستوى تعلمك بعد. أقترح الاختبار التشخيصي الحالي المكون من ستة أسئلة.','ary/latin':'Mazal ma t7eddedch mostawa dyal ta3allom dyalk. Kan9ter7 lquiz t-tashkhisi li fih 6 dyal l2as2ila.','ary/arabic':'مازال ما تحددش المستوى ديال التعلم ديالك. كنقترح الاختبار التشخيصي الحالي فيه ستة ديال الأسئلة.'}),
 'review_topic': MappingProxyType({'fr/latin':'Votre historique montre un point à revoir: {topic}. Revoyez-le avant une nouvelle étape.','en/latin':'Your learning evidence shows a topic to review: {topic}. Review it before a new step.','ar/arabic':'تشير أدلة تعلمك إلى موضوع يحتاج إلى مراجعة: {topic}. راجعه قبل خطوة جديدة.','ary/latin':'L2adila dyal ta3allom dyalk katbayan belli khassek traje3: {topic}. Raje3o 9bel lkhotwa jaya.','ary/arabic':'الأدلة ديال التعلم ديالك كاتبين بلي خاصك تراجع: {topic}. راجعو قبل الخطوة الجاية.'}),
 'continue_formation': MappingProxyType({'fr/latin':'Votre parcours est encore en cours. Continuez la formation pour consolider les notions commencées.','en/latin':'Your learning path is still in progress. Continue the formation to consolidate the concepts you started.','ar/arabic':'ما زال مسارك التعليمي قيد الإنجاز. واصل التكوين لترسيخ المفاهيم التي بدأت بها.','ary/latin':'Massar ta3allom dyalk mazal ma salach. Kmel formation bach t9ewwi lmafahim li bditi bihom.','ary/arabic':'المسار التعليمي ديالك مازال ما سالاش. كمل التكوين باش تقوي المفاهيم اللي بديتي بيها.'}),
 'take_quiz': MappingProxyType({'fr/latin':'Vous avez terminé une partie de votre apprentissage sans pratique récente. Faites le quiz pour vérifier vos acquis.','en/latin':'You completed part of your learning without recent practice. Take the quiz to check your understanding.','ar/arabic':'أنجزت جزءا من تعلمك من دون ممارسة حديثة. أجر الاختبار للتحقق من استيعابك.','ary/latin':'Kmelti chi joz2 mn ta3allom dyalk bla tamrin 9rib. Dir lquiz bach tchek lmafahim dyalk.','ary/arabic':'كملتي جزء من التعلم ديالك بلا تدريب قريب. دير الاختبار باش تشيك الفهم ديالك.'}),
 'next_learning_topic': MappingProxyType({'fr/latin':'Vos résultats récents sont solides. Passez au prochain thème d’apprentissage.','en/latin':'Your recent results are strong. Move to the next learning topic.','ar/arabic':'نتائجك الأخيرة قوية. انتقل إلى موضوع التعلم التالي.','ary/latin':'Nta2ej dyalk l2akhira mzyana. Dwez lmawdo3 ta3allomi jay.','ary/arabic':'النتائج الأخيرة ديالك مزيانة. دوز للموضوع التعليمي الجاي.'}),
})
def locale_key(language, script):
    key = f'{language}/{script}'
    if key not in LOCALES: raise ValueError(f'unsupported orientation locale: {key}')
    return key
def render_recommendation(recommendation, language, script):
    locale = locale_key(language, script)
    message = _MESSAGES[recommendation.action][locale]
    topic_labels = TOPIC_LABELS.get(recommendation.recommended_topic, _UNKNOWN_TOPIC_LABELS)
    topic = topic_labels[locale] if recommendation.recommended_topic else ''
    return message.format(topic=topic)
