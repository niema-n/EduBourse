from app.agents.contracts import AGENT_CONTRACTS, SHARED_POLICY
from app.graph.state import GraphState
from app.specialists.content import render_specialist_response


def out_of_domain_agent(state: GraphState) -> GraphState:
    answer = render_specialist_response(
        "out_of_domain", state.get("language", "fr"), state.get("script", "latin")
    )
    return {
        "business_answer": answer,
        "response_key": "out_of_domain",
        "status": "completed",
        "agent_contract": AGENT_CONTRACTS["out_of_domain"],
        "policy_id": SHARED_POLICY.policy_id,
    }
