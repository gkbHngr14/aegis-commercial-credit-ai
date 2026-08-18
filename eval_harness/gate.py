from typing import Dict, Any, Tuple

class SafetyGate:
    def __init__(self, nli_threshold: float = 0.90):
        self.nli_threshold = nli_threshold  # Sub-150ms DeBERTa-v3 threshold

    def compute_nli_score(self, reasoning: str, context: str) -> float:
        # Simulates DeBERTa-v3 cross-encoder entailment scoring
        if "overrides" in context.lower() and "not_guaranteed" in reasoning.lower():
            return 0.95
        return 0.82

    def verify_numerical_variance(self, claim_val: float, expected_val: float, allowed_variance: float) -> bool:
        return abs(claim_val - expected_val) <= allowed_variance

    def evaluate(
        self,
        llm_payload: Dict[str, Any],
        retrieved_context: str,
        expected_verdict: str,
        expected_limit: float,
        allowed_variance: float = 500000.0
    ) -> Tuple[bool, str, Dict[str, Any]]:
        
        # Step 1: NLI Entailment Check
        reasoning = llm_payload.get("reasoning_summary", "")
        nli_score = self.compute_nli_score(reasoning, retrieved_context)
        
        # Step 2: Numerical Variance Check
        reported_val = llm_payload.get("reported_value", expected_limit)
        variance_valid = self.verify_numerical_variance(reported_val, expected_limit, allowed_variance)
        
        # Step 3: Verdict Match
        verdict_valid = (llm_payload.get("verdict") == expected_verdict)
        
        # Circuit Breaker Gate
        if nli_score >= self.nli_threshold and variance_valid and verdict_valid:
            return True, "PASSED_GATE", llm_payload
        
        # Fallback to direct raw RAG policy summary for human credit officer sign-off
        fallback_payload = {
            "verdict": "HUMAN_REVIEW_REQUIRED",
            "reasoning_summary": f"Safety gate tripped (NLI Score: {nli_score:.2f}, Variance Valid: {variance_valid}).",
            "raw_retrieved_context": retrieved_context
        }
        return False, "FALLBACK_TO_RAW_RAG", fallback_payload