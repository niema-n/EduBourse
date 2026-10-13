import pytest

from app.api.chat import process_text_message
from app.graph.core import build_graph
from app.schemas.chat import ChatRequest
from app.specialists.content import render_specialist_response


class FixedRouteSupervisor:
    def __init__(self, route):
        self.route = route

    def invoke_structured(self, request):
        status = 'out_of_domain' if self.route == 'out_of_domain' else 'in_domain'
        return {'domain_status': status, 'route': self.route}


CASES = {
    'cisi': [
        ('Comment préparer une certification CISI ?', 'fr', 'latin'),
        ('How should I prepare for CISI certification?', 'en', 'latin'),
        ('كيف أستعد لشهادة CISI؟', 'ar', 'arabic'),
        ('Kifach nwjed certification CISI?', 'ary', 'latin'),
        ('كيفاش نوجد شهادة CISI؟', 'ary', 'arabic'),
    ],
    'championnat': [
        ('Comment fonctionne le Championnat de la Bourse ?', 'fr', 'latin'),
        ('How does the stock market championship work?', 'en', 'latin'),
        ('كيف تعمل بطولة البورصة؟', 'ar', 'arabic'),
        ('Kifach kaykhdem Championnat dyal lBorsa?', 'ary', 'latin'),
        ('كيفاش كاتخدم بطولة البورصة؟', 'ary', 'arabic'),
    ],
    'support_ecole': [
        ("Comment accéder aux formations de l'École de la Bourse ?", 'fr', 'latin'),
        ('How can I access the learning paths?', 'en', 'latin'),
        ('كيف أصل إلى مسارات التعلم؟', 'ar', 'arabic'),
        ('Kifach nwsel l formations dyal Ecole de la Bourse?', 'ary', 'latin'),
        ('كيفاش نوصل للتكوين ديال مدرسة البورصة؟', 'ary', 'arabic'),
    ],
    'out_of_domain': [
        ('Donnez-moi une recette de gâteau.', 'fr', 'latin'),
        ('Give me a cake recipe.', 'en', 'latin'),
        ('أعطني وصفة كعكة.', 'ar', 'arabic'),
        ('3tini wasfa dyal gateau.', 'ary', 'latin'),
        ('عطيني وصفة ديال كيكة.', 'ary', 'arabic'),
    ],
}


@pytest.mark.parametrize('route', CASES)
def test_specialist_text_pipeline_preserves_localized_content(route):
    for index, (message, language, script) in enumerate(CASES[route]):
        thread = f'{route}-{index}'
        graph = build_graph(supervisor_provider=FixedRouteSupervisor(route))
        result = process_text_message(ChatRequest(message=message, thread_id=thread), graph)
        assert result.route == route
        assert result.language == language
        assert result.script == script
        assert result.answer == render_specialist_response(route, language, script)


@pytest.mark.parametrize('route', CASES)
def test_specialist_voice_mock_uses_same_pipeline(route):
    for index, (message, language, script) in enumerate(CASES[route]):
        graph = build_graph(supervisor_provider=FixedRouteSupervisor(route))
        result = process_text_message(
            ChatRequest(message=message, thread_id=f'voice-{route}-{index}'), graph
        )
        assert result.route == route
        assert result.answer == render_specialist_response(route, language, script)


def test_security_precedes_championnat_specialist():
    graph = build_graph(supervisor_provider=FixedRouteSupervisor('championnat'))
    result = process_text_message(
        ChatRequest(message='Quelle action dois-je acheter pour gagner ?', thread_id='safe'), graph
    )
    assert result.route == 'securite'
    assert result.blocked is True
