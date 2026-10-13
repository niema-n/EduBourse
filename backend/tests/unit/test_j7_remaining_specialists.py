import re

import pytest

from app.agents.contracts import AGENT_CONTRACTS, SHARED_POLICY
from app.orientation.content import TOPIC_LABELS
from app.specialists.content import LOCALES, render_specialist_response

CANONICAL_TOPICS = {
    'bond', 'corporate_action', 'disclosure', 'diversification',
    'diversification_application', 'dividend', 'financial_analysis', 'horizon',
    'index', 'investor', 'ipo', 'ipo_disclosure', 'ipo_mechanism', 'limit_order',
    'liquidity_risk', 'market_order', 'market_rules', 'market_structure', 'opcvm',
    'opcvm_value', 'participant_roles', 'participants', 'primary_intro',
    'primary_secondary_markets', 'return', 'risk', 'risk_return',
    'risk_return_application', 'secondary_market', 'securities_operation', 'stock',
    'stock_bond_context', 'stock_exchange', 'stocks_bonds', 'volatility',
}


def test_all_quiz_topics_have_orientation_labels():
    assert CANONICAL_TOPICS <= set(TOPIC_LABELS)


@pytest.mark.parametrize('route', ['cisi', 'championnat', 'support_ecole', 'out_of_domain'])
@pytest.mark.parametrize(
    'language,script',
    [('fr', 'latin'), ('en', 'latin'), ('ar', 'arabic'), ('ary', 'latin'), ('ary', 'arabic')],
)
def test_specialist_content_covers_all_locales(route, language, script):
    text = render_specialist_response(route, language, script)
    assert text.strip()
    assert not re.search(r'Ã|Â|Ø|Ù|�', text)
    if script == 'latin':
        assert not re.search(r'[\u0600-\u06ff]', text)
    else:
        assert re.search(r'[\u0600-\u06ff]', text)


def test_specialists_use_existing_contracts_and_policy():
    assert SHARED_POLICY.policy_id == 'SENIOR_FINANCIAL_AGENT_POLICY_V1'
    assert AGENT_CONTRACTS['cisi'].specialization_id == 'CISI_EXPERT_V1'
    assert AGENT_CONTRACTS['championnat'].specialization_id == 'CHAMPIONNAT_EXPERT_V1'
    assert AGENT_CONTRACTS['support_ecole'].specialization_id == 'SUPPORT_ECOLE_EXPERT_V1'
    assert AGENT_CONTRACTS['out_of_domain'].specialization_id == 'OUT_OF_DOMAIN_SCOPE_V1'
    assert LOCALES == ('fr/latin', 'en/latin', 'ar/arabic', 'ary/latin', 'ary/arabic')
