# utils/data_guards.py
from typing import Dict, Any, List, Tuple

class IngestionValidationError(ValueError):
    """Custom exception raised when credit evaluation payload fails schema/security checks."""
    pass

def validate_credit_input_payload(state: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validates incoming CreditState payload against business and security constraints.
    Returns (is_valid, list_of_errors).
    """
    errors = []

    # 1. Required Field Presence Checks
    required_fields = ["borrower_id", "tenant_id", "requested_amount", "user_query"]
    for field in required_fields:
        if field not in state or state[field] is None:
            errors.append(f"Missing required input field: '{field}'")

    #if errors:
    #    return False, errors

    # 2. Business Boundary Guards
    requested_amount = state.get("requested_amount", 0.0)
    if not isinstance(requested_amount, (int, float)) or requested_amount <= 0:
        errors.append(f"Invalid requested_amount: ${requested_amount}. Must be a positive number.")

    # Facility cap sanity check (e.g., $1B ceiling guard)
    if requested_amount > 1_000_000_000.0:
        errors.append(f"Requested amount ${requested_amount:,.2f} exceeds single-facility upper limit ($1B).")

    # 3. Multi-Tenant Format Guard
    tenant_id = str(state.get("tenant_id", ""))
    if not tenant_id.strip():
        errors.append("tenant_id cannot be empty or whitespace.")

    # 4. Input Sanitization / Query Length Guard
    user_query = str(state.get("user_query", ""))
    if len(user_query.strip()) < 3:
        errors.append("user_query is too short (minimum 3 characters required).")
    if len(user_query) > 2000:
        errors.append("user_query exceeds maximum allowed length (2000 characters).")

    return len(errors) == 0, errors