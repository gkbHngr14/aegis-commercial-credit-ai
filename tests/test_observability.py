import pytest
from observability.tracer import trace_span
from observability.token_counter import TokenCostManager

def test_opentelemetry_span_execution():
    """Verifies OpenTelemetry context manager executes without errors."""
    attributes = {"tenant_id": "TENANT-US", "borrower_id": "BORROWER-100"}
    with trace_span("test_node_execution", attributes) as span:
        assert span.is_recording() is True


def test_token_cost_calculation_and_budget_gate():
    """Verifies token billing math and budget cap enforcement."""
    manager = TokenCostManager(tenant_max_budget_usd=1.0) # $1.00 budget cap

    # 1. Normal usage within budget
    result1 = manager.record_usage(
        tenant_id="TENANT-US",
        model="gpt-4o",
        prompt_tokens=10_000,
        completion_tokens=2_000
    )
    assert result1["allowed"] is True
    assert result1["cost"] == 0.08  # (10 * 0.005) + (2 * 0.015) = $0.08
    assert result1["total_spend"] == 0.08

    # 2. Exceeding tenant budget cap
    result2 = manager.record_usage(
        tenant_id="TENANT-US",
        model="gpt-4o",
        prompt_tokens=200_000,
        completion_tokens=50_000
    )
    assert result2["allowed"] is False
    assert "exceeded budget cap" in result2["error"]