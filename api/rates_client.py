import urllib.request
import json
from typing import Dict, Any

class TreasuryRatesClient:
    """
    Fetches real-time macro benchmark rates directly from the official 
    US Department of the Treasury Data API.
    """
    TREASURY_API_URL = (
        "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/"
        "v2/accounting/od/avg_interest_rates?filter=record_date:gte:2025-01-01"
        "&sort=-record_date&page[size]=5"
    )

    def __init__(self, timeout_seconds: int = 5):
        self.timeout = timeout_seconds

    def fetch_live_market_benchmarks(self) -> Dict[str, Any]:
        """
        Fetches official U.S. Treasury benchmark rates with circuit-breaker fallback.
        """
        try:
            # Query official US Treasury Fiscal Data endpoint
            response = requests.get(self.TREASURY_API_URL, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            if "data" in data and len(data["data"]) > 0:
                latest_record = data["data"][0]
                rate_val = float(latest_record.get("avg_interest_rate_amt", 4.75))
                return {
                    "treasury_avg_debt_rate": rate_val,
                    "benchmark_rate": rate_val,
                    "source": "US Fiscal Data Service API",
                    "status": "LIVE"
                }
        except Exception:
            # Circuit breaker fallback on network/timeout error
            pass

        return {
            "treasury_avg_debt_rate": 4.75,
            "benchmark_rate": 4.75,
            "source": "Circuit Breaker Fallback",
            "status": "FALLBACK"
        }