from typing import Dict, Any
from api.rates_client import TreasuryRatesClient

class MacroRateNode:
    """
    Dedicated worker node that queries external US Treasury / SOFR market rates.
    Decoupled from internal credit risk scoring for SRE resilience and circuit breaker safety.
    """
    def __init__(self):
        self.rates_client = TreasuryRatesClient(timeout_seconds=5)

    def fetch_macro_context(self, state: Dict[str, Any]) -> Dict[str, Any]:
        rate_data = self.rates_client.fetch_live_market_benchmarks()
        live_sofr = rate_data.get("sofr_benchmark_rate", 4.75)

        logs = state.get("audit_log", [])
        logs.append(f"Fetched macro rate benchmark: {live_sofr}% via {rate_data['source']}")

        return {
            "macro_benchmark_rate": live_sofr,
            "audit_log": logs
        }