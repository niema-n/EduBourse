# ruff: noqa
import re

import pytest

from app.graph.state import create_turn_input
from app.learning.profile_service import LearningProfileService
from app.learning.store import InMemoryLearningProfileStore
from app.orientation.agent import OrientationAgent, decide
from app.orientation.content import LOCALES, render_recommendation


def service_with(level=None):
    service = LearningProfileService(InMemoryLearningProfileStore())
    if level:
        service.set_level('t', level, 'manual')
    return service


def attempt(service, score, topic='orders'):
    service.record_quiz_attempt('t', quiz_id='q'+str(score), topic=topic, level='intermediate', score_percent=score, correct_count=int(score / 20), total_questions=5)


def test_unknown_level_uses_existing_diagnostic_contract():
    recommendation = decide(service_with().get_profile('t'))
    assert recommendation.action == 'diagnostic'
    assert recommendation.next_agent == 'quiz'
    assert recommendation.needs_diagnostic is True


def test_known_weak_topic_reviews_before_quiz():
    service = service_with('beginner')
    service.mark_topic_to_review('t', 'orders')
    result = decide(service.get_profile('t'))
    assert result.action == 'review_topic'
    assert result.recommended_topic == 'orders'
    assert result.next_agent == 'formation_elearning'


def test_decision_matrix_uses_shared_profile_evidence():
    service = service_with('intermediate')
    service.set_learning_path('t', 'intermediate_financial_learning')
    assert decide(service.get_profile('t')).action == 'continue_formation'
    service.mark_module_completed('t', 'intermediate_market_basics')
    service.set_learning_path('t', None)
    assert decide(service.get_profile('t')).action == 'take_quiz'
    attempt(service, 90)
    assert decide(service.get_profile('t')).action == 'next_learning_topic'


def test_repeated_poor_performance_is_review():
    service = service_with('advanced')
    attempt(service, 20, 'liquidity')
    attempt(service, 40, 'liquidity')
    result = decide(service.get_profile('t'))
    assert result.action == 'review_topic'
    assert result.recommended_topic == 'liquidity'


@pytest.mark.parametrize('language,script', [('fr','latin'),('en','latin'),('ar','arabic'),('ary','latin'),('ary','arabic')])
def test_all_locales_render_without_internal_slugs(language, script):
    result = OrientationAgent(service_with('beginner'))(create_turn_input('orient', language=language, script=script, thread_id='t'))
    text = result['business_answer']
    assert result['orientation_recommendation'].action == 'continue_formation'
    assert 'risk_return' not in text
    assert 'stocks_bonds' not in text
    assert '\ufffd' not in text
    if script == 'arabic':
        assert re.search(r'[\u0600-\u06ff]', text)
    else:
        assert not re.search(r'[\u0600-\u06ff]', text)


def test_unknown_level_asks_for_manual_level():
    service = service_with()
    result = OrientationAgent(service)(create_turn_input('orient', language='fr', script='latin', thread_id='t'))
    assert result['assessment_required'] is False
    assert result['workflow_context'].active_agent == 'orientation'
    assert result['workflow_context'].workflow_step == 'learning_level'
    assert result['orientation_recommendation'] is None


def test_static_content_is_not_mutable_and_msa_differs_from_darija():
    recommendation = decide(service_with('beginner').get_profile('t'))
    msa = render_recommendation(recommendation, 'ar', 'arabic')
    darija = render_recommendation(recommendation, 'ary', 'arabic')
    assert msa != darija
    assert 'م' in msa and 'ديال' in darija
    assert tuple(LOCALES) == ('fr/latin','en/latin','ar/arabic','ary/latin','ary/arabic')


def test_orientation_never_adds_investor_profile_fields():
    fields = set(OrientationAgent(service_with('beginner')).__dict__)
    forbidden = {'risk_tolerance','investment_horizon','investment_amount','portfolio','asset_allocation'}
    assert not fields & forbidden
