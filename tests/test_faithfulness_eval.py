import pytest
from eval_harness.faithfulness_eval import FaithfulnessEvalHarness

def test_eval_gate_passes_for_valid_response():
    evaluator = FaithfulnessEvalHarness(groundedness_threshold=0.70)

    context = "European Subsidiary drawdown limit is set at $5,000,000 as of 2026."
    output = "The requested European Subsidiary drawdown is $5,000,000."
    claims = ["Drawdown limit is $5,000,000", "Facility applies to European Subsidiary"]

    result = evaluator.run_eval_gate(output, claims, context)

    assert result["passed"] is True
    assert result["groundedness_score"] >= 0.70
    assert result["numerical_accuracy"] is True


def test_eval_gate_fails_on_numerical_drift():
    evaluator = FaithfulnessEvalHarness(groundedness_threshold=0.70)

    context = "European Subsidiary drawdown limit is set at $5,000,000 as of 2026."
    # Output hallucinates $12,000,000 instead of $5,000,000
    output = "The requested European Subsidiary drawdown is $12,000,000."
    claims = ["Drawdown limit is $12,000,000"]

    result = evaluator.run_eval_gate(output, claims, context)

    assert result["passed"] is False
    assert result["numerical_accuracy"] is False