import re
from typing import List, Dict, Any

class FaithfulnessEvalHarness:
    def __init__(self, groundedness_threshold: float = 0.75):
        self.groundedness_threshold = groundedness_threshold

    def evaluate_numerical_accuracy(self, output_text: str, context_text: str) -> bool:
        """
        Extracts monetary figures (e.g., $5,000,000 or $5M) from generated output
        and verifies that every number exists in the raw context.
        """
        # Find monetary amounts in output
        output_numbers = re.findall(r'\$\d+(?:,\d{3})*(?:\.\d+)?', output_text)
        if not output_numbers:
            return True

        # Ensure every dollar amount cited in output appears anywhere in raw context
        for num in output_numbers:
            if num not in context_text:
                return False
        return True

    def evaluate_groundedness(self, response_claims: List[str], context_text: str) -> float:
        """
        Calculates the ratio of claim statements directly backed by retrieved context words.
        """
        if not response_claims:
            return 1.0

        supported_claims = 0
        context_lower = context_text.lower()

        for claim in response_claims:
            # Check key term overlap between claim and context
            claim_words = [w.lower() for w in claim.split() if len(w) > 3]
            if not claim_words:
                supported_claims += 1
                continue
            
            matches = sum(1 for word in claim_words if word in context_lower)
            if (matches / len(claim_words)) >= 0.5:
                supported_claims += 1

        return round(supported_claims / len(response_claims), 2)

    def run_eval_gate(
        self,
        output_text: str,
        response_claims: List[str],
        context_text: str
    ) -> Dict[str, Any]:
        """
        Executes full evaluation gate. Returns PASS/FAIL status.
        """
        groundedness = self.evaluate_groundedness(response_claims, context_text)
        numerical_valid = self.evaluate_numerical_accuracy(output_text, context_text)

        passed = (groundedness >= self.groundedness_threshold) and numerical_valid

        return {
            "passed": passed,
            "groundedness_score": groundedness,
            "numerical_accuracy": numerical_valid,
            "threshold": self.groundedness_threshold
        }