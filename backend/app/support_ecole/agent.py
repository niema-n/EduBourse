from app.agents.contracts import AGENT_CONTRACTS, SHARED_POLICY
from app.graph.state import GraphState
from app.specialists.content import render_specialist_response


def support_ecole_agent(state: GraphState) -> GraphState:
    answer = render_specialist_response(
        "support_ecole", state.get("language", "fr"), state.get("script", "latin")
    )
    return {
        "business_answer": answer,
        "response_key": "support_ecole",
        "status": "completed",
        "agent_contract": AGENT_CONTRACTS["support_ecole"],
        "policy_id": SHARED_POLICY.policy_id,
    }
