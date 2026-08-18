import pytest
from eval_harness.gate import SafetyGate

def test_safety_gate_pass_scenario():
    gate = SafetyGate(nli_threshold=0.90)
    llm_payload = {
        "verdict": "NOT_GUARANTEED",
        "reasoning_summary": "Amendment 3 overrides Section 14.2; subsidiary is NOT_GUARANTEED.",
        "reported_value": 20000000.0
    }
    context = "Section 14.2 specifies recourse, but Amendment 3 explicitly overrides Section 14."
    
    passed, status, payload = gate.evaluate(
        llm_payload, context, expected_verdict="NOT_GUARANTEED", expected_limit=20000000.0
    )
    
    assert passed is True
    assert status == "PASSED_GATE"
    assert payload["verdict"] == "NOT_GUARANTEED"

def test_safety_gate_fallback_on_hallucination():
    gate = SafetyGate(nli_threshold=0.90)
    llm_payload = {
        "verdict": "GUARANTEED",
        "reasoning_summary": "Subsidiary is liable for default risk.",
        "reported_value": 20000000.0
    }
    context = "Amendment 3 explicitly overrides Section 14."
    
    passed, status, payload = gate.evaluate(
        llm_payload, context, expected_verdict="NOT_GUARANTEED", expected_limit=20000000.0
    )
    
    assert passed is False
    assert status == "FALLBACK_TO_RAW_RAG"
    assert payload["verdict"] == "HUMAN_REVIEW_REQUIRED"