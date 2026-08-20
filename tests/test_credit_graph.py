import pytest
from agents.credit_graph import build_credit_graph

def test_automated_approval_for_small_loan():
    app = build_credit_graph()
    thread_config = {"configurable": {"thread_id": "thread-small-loan-1"}}

    initial_state = {
        "borrower_id": "BORROWER-101",
        "tenant_id": "TENANT-EMEA",
        "as_of_date": "2026-08-01",
        "requested_amount": 1_000_000.0,
        "user_query": "Evaluate $1M facility",
        "retrieved_chunks": [],
        "formatted_context": "",
        "risk_score": None,
        "risk_analysis": None,
        "compliance_passed": None,
        "hitl_required": False,
        "hitl_reason": None,
        "human_approval_status": "NONE",
        "human_officer_notes": None,
        "audit_trail": []
    }

    # Execute workflow
    for _ in app.stream(initial_state, thread_config):
        pass

    final_state = app.get_state(thread_config).values
    assert final_state["requested_amount"] == 1_000_000.0
    assert final_state["hitl_required"] is False
    assert final_state["risk_score"] == 3.1
    assert any("[FinalDecision]" in item for item in final_state["audit_trail"])


def test_hitl_breakpoint_trigger_and_resume_approval():
    app = build_credit_graph()
    thread_config = {"configurable": {"thread_id": "thread-large-loan-99"}}

    large_loan_state = {
        "borrower_id": "BORROWER-999",
        "tenant_id": "TENANT-US",
        "as_of_date": "2026-08-01",
        "requested_amount": 12_000_000.0,
        "user_query": "Evaluate $12M credit line",
        "retrieved_chunks": [],
        "formatted_context": "",
        "risk_score": None,
        "risk_analysis": None,
        "compliance_passed": None,
        "hitl_required": False,
        "hitl_reason": None,
        "human_approval_status": "NONE",
        "human_officer_notes": None,
        "audit_trail": []
    }

    # 1. Stream execution - must pause BEFORE 'hitl_breakpoint'
    for _ in app.stream(large_loan_state, thread_config):
        pass

    paused_state = app.get_state(thread_config)
    assert paused_state.next == ("hitl_breakpoint",)
    assert paused_state.values["risk_score"] == 8.5

    # 2. Simulate Credit Officer intervention & resume state
    app.update_state(
        thread_config,
        {
            "human_approval_status": "APPROVED",
            "human_officer_notes": "Override approved based on secondary collateral audit."
        }
    )

    # 3. Resume graph execution from pause
    for _ in app.stream(None, thread_config):
        pass

    resumed_final = app.get_state(thread_config).values
    assert resumed_final["human_approval_status"] == "APPROVED"
    assert resumed_final["hitl_required"] is True
    assert any("[HITL_Breakpoint]" in item for item in resumed_final["audit_trail"])