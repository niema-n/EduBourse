# ruff: noqa
from app.agents.contracts import AGENT_CONTRACTS, SHARED_POLICY
from app.graph.workflow_context import ConversationWorkflowContext, WorkflowContextService
from app.learning.models import SharedLearningProfile
from app.learning.profile_service import LearningProfileService
from app.learning.level_resolution import clarify_level, resolve_level
from app.formation.agent import run_formation_agent
from app.orientation.content import render_recommendation
from app.orientation.models import OrientationRecommendation

_TOPIC_ALIASES = {'marches':'market_basics','market_basics':'market_basics','actions':'stocks_bonds','obligations':'stocks_bonds','orders':'orders','risques':'risk_return','risk_return':'risk_return'}
def _topic(value): return _TOPIC_ALIASES.get(value.casefold().strip(), value.casefold().strip())
def _weak_topic(profile):
    for value in [*profile.topics_to_review, *(a.topic for a in profile.quiz_history if a.score_percent < 50)]:
        topic = _topic(value)
        if topic: return topic
    return None
def decide(profile: SharedLearningProfile):
    if profile.learning_level is None:
        return OrientationRecommendation(action='diagnostic', reason='No learning level has been established yet.', next_agent='quiz', needs_diagnostic=True)
    weak = _weak_topic(profile)
    poor = [a for a in profile.quiz_history if a.score_percent < 50]
    if weak:
        return OrientationRecommendation(action='review_topic', current_level=profile.learning_level, recommended_topic=weak, reason='The shared profile contains evidence for a topic to review.', next_agent='formation_elearning', evidence=tuple(profile.topics_to_review) or tuple(f'quiz:{a.topic}:{a.score_percent:g}' for a in poor))
    if profile.current_learning_path and len(profile.completed_modules) < 8:
        return OrientationRecommendation(action='continue_formation', current_level=profile.learning_level, reason='The shared profile contains an incomplete learning path.', next_agent='formation_elearning', evidence=(profile.current_learning_path,))
    if profile.completed_topics or profile.completed_modules:
        if not profile.quiz_history:
            return OrientationRecommendation(action='take_quiz', current_level=profile.learning_level, reason='Learning material is complete but there is no recent quiz evidence.', next_agent='quiz', evidence=tuple(profile.completed_topics or profile.completed_modules))
        if all(a.score_percent >= 80 for a in profile.quiz_history[-2:]):
            return OrientationRecommendation(action='next_learning_topic', current_level=profile.learning_level, reason='Recent quiz results are strong and learning material is complete.', next_agent='formation_elearning', evidence=tuple(f'quiz:{a.score_percent:g}' for a in profile.quiz_history[-2:]))
    return OrientationRecommendation(action='continue_formation', current_level=profile.learning_level, reason='The shared profile has limited evidence; continue with an educational learning path.', next_agent='formation_elearning')
class OrientationAgent:
    def __init__(self, profile_service: LearningProfileService):
        self.contract = AGENT_CONTRACTS['orientation']; self.policy = SHARED_POLICY; self.profile_service = profile_service
    def __call__(self, state):
        profile, explicit_level, diagnostic = resolve_level(state, self.profile_service)
        if not diagnostic and profile.learning_level is None:
            return clarify_level(state, 'orientation') | {'orientation_recommendation': None}
        if explicit_level:
            return run_formation_agent(state, self.profile_service) | {'response_key': 'orientation', 'orientation_recommendation': None}
        recommendation = OrientationRecommendation(action='diagnostic', reason='The user explicitly requested a level assessment.', next_agent='quiz', needs_diagnostic=True) if diagnostic else decide(profile)
        updates = {'orientation_recommendation': recommendation, 'business_answer': render_recommendation(recommendation, state.get('language','fr'), state.get('script','latin')), 'response_key':'orientation', 'status':'completed'}
        if recommendation.needs_diagnostic:
            updates['assessment_required'] = True
            updates['workflow_context'] = WorkflowContextService().start_workflow(active_agent='orientation', active_workflow='orientation_diagnostic', workflow_step='awaiting_existing_quiz')
        else:
            updates['workflow_context'] = WorkflowContextService().complete_workflow(state.get('workflow_context', ConversationWorkflowContext()))
        return updates
def run_orientation_agent(state, profile_service): return OrientationAgent(profile_service)(state)
