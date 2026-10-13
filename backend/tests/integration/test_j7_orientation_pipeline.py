# ruff: noqa
import pytest

from app.api.chat import process_text_message
from app.graph.core import build_graph
from app.learning.profile_service import LearningProfileService
from app.learning.store import InMemoryLearningProfileStore
from app.orientation.content import TOPIC_LABELS
from app.orientation.models import OrientationRecommendation
from app.schemas.chat import ChatRequest

class OrientationSupervisor:
    def invoke_structured(self, request):
        return {'domain_status': 'in_domain', 'route': 'orientation'}

@pytest.mark.parametrize('message,language,script', [
    ('Orientez-moi pour apprendre les marchés financiers.', 'fr', 'latin'),
    ('Guide me to my next financial learning step.', 'en', 'latin'),
    ('أرشدني إلى الخطوة التعليمية التالية.', 'ar', 'arabic'),
    ('Bghit t3ref chno nt3ellem mn ba3d.', 'ary', 'latin'),
    ('بغيت نعرف شنو نتعلم من بعد.', 'ary', 'arabic'),
])
def test_text_pipeline_orientation_all_locales(message, language, script):
    service = LearningProfileService(InMemoryLearningProfileStore())
    service.set_level('orientation-pipeline', 'beginner', 'manual')
    graph = build_graph(supervisor_provider=OrientationSupervisor(), learning_profile_service=service)
    result = process_text_message(ChatRequest(message=message, thread_id='orientation-pipeline'), graph)
    assert result.route == 'orientation'
    assert result.status == 'ok'
    assert result.language == language
    assert result.script == script
    assert 'stocks_bonds' not in result.answer
    assert 'investment' not in result.answer.casefold()

@pytest.mark.parametrize('message', [
    'Orientez-moi pour apprendre les marchés financiers.',
    'Guide me to my next financial learning step.',
    'أرشدني إلى الخطوة التعليمية التالية.',
    'Bghit t3ref chno nt3ellem mn ba3d.',
    'بغيت نعرف شنو نتعلم من بعد.',
])
def test_voice_mock_reuses_same_text_pipeline(message):
    service = LearningProfileService(InMemoryLearningProfileStore())
    service.set_level('voice-orientation', 'beginner', 'manual')
    service.mark_topic_to_review('voice-orientation', 'diversification')
    graph = build_graph(supervisor_provider=OrientationSupervisor(), learning_profile_service=service)
    transcript = message
    result = process_text_message(ChatRequest(message=transcript, thread_id='voice-orientation'), graph)
    assert result.route == 'orientation'
    assert result.status == 'ok'
    assert TOPIC_LABELS['diversification'][f'{result.language}/{result.script}'] in result.answer
    assert 'risk_return' not in result.answer

from app.graph.state import create_turn_input


def make_orientation_graph(thread_id='cross-modal'):
    service = LearningProfileService(InMemoryLearningProfileStore())
    service.set_level(thread_id, 'intermediate', 'manual')
    return build_graph(
        supervisor_provider=OrientationSupervisor(),
        learning_profile_service=service,
    ), service


def test_text_voice_structured_recommendation_is_equivalent():
    graph, service = make_orientation_graph('equivalent')
    service.mark_topic_to_review('equivalent', 'liquidity')
    text = graph.invoke(
        create_turn_input('Orient me', language='en', script='latin', thread_id='equivalent'),
        config={'configurable': {'thread_id': 'equivalent'}},
    )
    voice = graph.invoke(
        create_turn_input('Guide me', language='en', script='latin', thread_id='equivalent'),
        config={'configurable': {'thread_id': 'equivalent'}},
    )
    left = text['orientation_recommendation']
    right = voice['orientation_recommendation']
    assert left.model_dump() == right.model_dump()
    assert service.get_profile('equivalent').topics_to_review == ['liquidity']


def test_text_start_voice_continue_preserves_thread_profile_and_evidence():
    graph, service = make_orientation_graph('text-voice')
    first = process_text_message(
        ChatRequest(message='Guide my next learning step.', thread_id='text-voice'), graph
    )
    second = process_text_message(
        ChatRequest(message='Continue my learning path.', thread_id='text-voice'), graph
    )
    assert first.route == second.route == 'orientation'
    assert first.thread_id == second.thread_id == 'text-voice'
    assert service.get_profile('text-voice').learning_level == 'intermediate'
    assert 'learning' in second.answer.casefold()


def test_voice_start_text_continue_preserves_thread_profile_and_evidence():
    graph, service = make_orientation_graph('voice-text')
    first = process_text_message(
        ChatRequest(message='Bghit lkhoutwa jaya f ta3allom.', thread_id='voice-text'), graph
    )
    second = process_text_message(
        ChatRequest(message='Orientez-moi encore.', thread_id='voice-text'), graph
    )
    assert first.route == second.route == 'orientation'
    assert first.thread_id == second.thread_id == 'voice-text'
    assert service.get_profile('voice-text').learning_level == 'intermediate'


def test_unknown_orientation_uses_real_quiz_diagnostic_on_same_thread():
    graph, service = make_orientation_graph('diagnostic')
    service.store._profiles.pop('diagnostic', None)
    first = process_text_message(
        ChatRequest(message='Je veux évaluer mon niveau en Bourse.', thread_id='diagnostic'), graph
    )
    assert first.route == 'orientation'
    assert service.get_profile('diagnostic').learning_level is None
    state = graph.get_state({'configurable': {'thread_id': 'diagnostic'}}).values
    assert state['quiz_session'].phase == 'diagnostic'
    assert len(state['quiz_session'].questions) == 6
    assert state['workflow_context'].active_agent == 'quiz'

    for answer in ['A', 'A', 'A', 'A', 'A', 'A']:
        process_text_message(ChatRequest(message=answer, thread_id='diagnostic'), graph)
    profile = service.get_profile('diagnostic')
    assert profile.learning_level in {'beginner', 'intermediate', 'advanced'}
    assert profile.level_source == 'diagnostic'
    assert profile.diagnostic_completed is True
    state = graph.get_state({'configurable': {'thread_id': 'diagnostic'}}).values
    assert state['quiz_session'].phase == 'quiz'
    assert state['quiz_session'].level == profile.learning_level

    resumed = process_text_message(
        ChatRequest(message='Oriente-moi encore dans mon apprentissage.', thread_id='diagnostic'), graph
    )
    assert resumed.route == 'orientation'
    assert 'diagnostic' not in resumed.answer.casefold()
    assert service.get_profile('diagnostic').level_source == 'diagnostic'


def test_unknown_orientation_reverse_modality_uses_same_quiz_session():
    graph, service = make_orientation_graph('reverse')
    service.store._profiles.pop('reverse', None)
    first = process_text_message(
        ChatRequest(message='Assess my level in financial learning.', thread_id='reverse'), graph
    )
    assert first.route == 'orientation'
    before = graph.get_state({'configurable': {'thread_id': 'reverse'}}).values['quiz_session']
    process_text_message(ChatRequest(message='A', thread_id='reverse'), graph)
    after = graph.get_state({'configurable': {'thread_id': 'reverse'}}).values['quiz_session']
    assert after.quiz_id == before.quiz_id
    assert after.current_question_index == before.current_question_index + 1
    assert service.get_profile('reverse').learning_level is None


@pytest.mark.parametrize('message,language,script', [
    ('Orientez-moi encore.', 'fr', 'latin'),
    ('Guide me again.', 'en', 'latin'),
    ('أرشدني مرة أخرى.', 'ar', 'arabic'),
    ('3awed wjheni.', 'ary', 'latin'),
    ('عاود وجهني.', 'ary', 'arabic'),
])
def test_final_pipeline_preserves_real_topic_recommendation(message, language, script):
    service = LearningProfileService(InMemoryLearningProfileStore())
    service.set_level('visible', 'intermediate', 'manual')
    service.mark_topic_to_review('visible', 'diversification')
    graph = build_graph(
        supervisor_provider=OrientationSupervisor(),
        learning_profile_service=service,
    )
    result = process_text_message(ChatRequest(message=message, thread_id='visible'), graph)
    assert result.route == 'orientation'
    assert TOPIC_LABELS['diversification'][f'{language}/{script}'] in result.answer
    assert 'risk_return' not in result.answer
    assert 'matches your goals' not in result.answer


@pytest.mark.parametrize('topic', [
    'bond', 'diversification', 'index', 'liquidity_risk', 'opcvm',
])
def test_representative_profile_topics_never_substitute_risk_return(topic):
    recommendation = OrientationRecommendation(
        action='review_topic',
        current_level='intermediate',
        recommended_topic=topic,
        reason='profile evidence',
        next_agent='formation_elearning',
    )
    for language, script in [('fr', 'latin'), ('en', 'latin'), ('ar', 'arabic'), ('ary', 'latin'), ('ary', 'arabic')]:
        from app.orientation.content import render_recommendation

        rendered = render_recommendation(recommendation, language, script)
        assert TOPIC_LABELS[topic][f'{language}/{script}'] in rendered
        assert 'le risque et le rendement' not in rendered
        assert 'risk and return' not in rendered


def test_unknown_future_topic_uses_neutral_label_without_slug_or_substitution():
    recommendation = OrientationRecommendation(
        action='review_topic',
        current_level='intermediate',
        recommended_topic='future_internal_topic',
        reason='profile evidence',
        next_agent='formation_elearning',
    )
    from app.orientation.content import render_recommendation

    for language, script in [('fr', 'latin'), ('en', 'latin'), ('ar', 'arabic'), ('ary', 'latin'), ('ary', 'arabic')]:
        rendered = render_recommendation(recommendation, language, script)
        assert 'future_internal_topic' not in rendered
        assert 'risk_return' not in rendered
