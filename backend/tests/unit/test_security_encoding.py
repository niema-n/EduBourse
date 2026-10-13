from app.graph.agents import securite_agent


def test_security_refusal_has_valid_french_encoding():
    answer = securite_agent({})["business_answer"]

    assert "Ãƒ" not in answer
    assert "Ã‚" not in answer
    assert "�" not in answer
    assert "répartir" in answer
    assert "critères généraux" in answer
