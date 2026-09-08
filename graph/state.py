# graph/state.py
from typing import TypedDict, Optional, List, Dict, Any

class CreditState(TypedDict, total=False):
    borrower_id: str
    tenant_id: str
    amount: float
    risk_score: Optional[float]
    macro_benchmark_rate: Optional[float]
    review_reason: Optional[str]
    approved: bool
    audit_log: List[str]