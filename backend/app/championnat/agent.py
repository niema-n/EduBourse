from app.agents.contracts import AGENT_CONTRACTS, SHARED_POLICY
from app.graph.state import GraphState
from app.specialists.content import render_specialist_response


def championnat_agent(state: GraphState) -> GraphState:
    answer = render_specialist_response(
        "championnat", state.get("language", "fr"), state.get("script", "latin")
    )
    return {
        "business_answer": answer,
        "response_key": "championnat",
        "status": "completed",
        "agent_contract": AGENT_CONTRACTS["championnat"],
        "policy_id": SHARED_POLICY.policy_id,
    }
