# tests/test_data_guards.py
import pytest
from utils.data_guards import validate_credit_input_payload

def test_valid_payload():
    valid_state = {
        "borrower_id": "BORROWER-101",
        "tenant_id": "TENANT-US",
        "requested_amount": 5_000_000.0,
        "user_query": "Evaluate CRE loan term sheet"
    }
    is_valid, errors = validate_credit_input_payload(valid_state)
    assert is_valid is True
    assert len(errors) == 0

def test_invalid_negative_amount_and_missing_tenant():
    invalid_state = {
        "borrower_id": "BORROWER-102",
        "requested_amount": -500.0,
        "user_query": "Test query"
    }
    is_valid, errors = validate_credit_input_payload(invalid_state)
    assert is_valid is False
    assert any("Missing required input field: 'tenant_id'" in err for err in errors)
    assert any("Invalid requested_amount" in err for err in errors)