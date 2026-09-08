# graph/state.py
from typing import TypedDict, Optional, List, Dict, Any

class CreditState(TypedDict, total=False):
    borrower_id: str
    tenant_id: str
    as_of_date: str
    requested_amount: float
    user_query: str
    retrieved_chunks: List[Dict[str, Any]]
    formatted_context: str
    risk_score: Optional[float]
    risk_analysis: Optional[str]
    compliance_passed: Optional[bool]
    hitl_required: bool
    hitl_reason: Optional[str]
    human_approval_status: str  # "NONE", "PENDING", "APPROVED", "REJECTED"
    human_officer_notes: Optional[str]
    macro_benchmark_rate: Optional[float]
    macro_rate_source: Optional[str]
    audit_trail: Annotated[List[str], operator.add]