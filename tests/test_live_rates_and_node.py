import pytest
from api.rates_client import TreasuryRatesClient
from agents.macro_rate_node import MacroRateNode

def test_live_treasury_api_connection():
    client = TreasuryRatesClient(timeout_seconds=5)
    result = client.fetch_live_market_benchmarks()

    assert result["status"] in ["LIVE_FETCH_SUCCESS", "CIRCUIT_BREAKER_FALLBACK"]
    assert "sofr_benchmark_rate" in result
    assert isinstance(result["sofr_benchmark_rate"], float)
    assert result["sofr_benchmark_rate"] > 0.0

def test_macro_rate_node_state_update():
    node = MacroRateNode()
    initial_state = {
        "borrower_id": "BORROWER-GLOBAL-CORP",
        "audit_log": []
    }

    updated_state = node.fetch_macro_context(initial_state)

    assert "macro_benchmark_rate" in updated_state
    assert updated_state["macro_benchmark_rate"] > 0.0
    assert len(updated_state["audit_log"]) == 1
    assert "Fetched macro rate benchmark" in updated_state["audit_log"][0]