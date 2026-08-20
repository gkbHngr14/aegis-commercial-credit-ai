from typing import Dict, Any

# Standard pricing model ($ per 1,000 tokens)
MODEL_PRICING = {
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "claude-3-5-sonnet": {"input": 0.003, "output": 0.015},
    "default": {"input": 0.002, "output": 0.008}
}

class TokenCostManager:
    def __init__(self, tenant_max_budget_usd: float = 50.0):
        self.tenant_max_budget_usd = tenant_max_budget_usd
        self.tenant_spend: Dict[str, float] = {}

    def calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        pricing = MODEL_PRICING.get(model, MODEL_PRICING["default"])
        input_cost = (prompt_tokens / 1000.0) * pricing["input"]
        output_cost = (completion_tokens / 1000.0) * pricing["output"]
        return round(input_cost + output_cost, 6)

    def record_usage(
        self,
        tenant_id: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int
    ) -> Dict[str, Any]:
        cost = self.calculate_cost(model, prompt_tokens, completion_tokens)
        current_spend = self.tenant_spend.get(tenant_id, 0.0)
        new_spend = round(current_spend + cost, 6)

        if new_spend > self.tenant_max_budget_usd:
            return {
                "allowed": False,
                "cost": cost,
                "total_spend": current_spend,
                "error": f"Tenant {tenant_id} exceeded budget cap of ${self.tenant_max_budget_usd:.2f}"
            }

        self.tenant_spend[tenant_id] = new_spend
        return {
            "allowed": True,
            "cost": cost,
            "total_spend": new_spend,
            "error": None
        }