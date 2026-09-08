import operator
from typing import Annotated, TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
try:
    from langgraph.checkpoint.postgres import PostgresSaver
    from psycopg_pool import ConnectionPool
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False

from agents.macro_rate_node import MacroRateNode

_macro_worker = MacroRateNode()

# 1. Centralized Shared State Schema
class CreditState(TypedDict):
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


# 2. Node Implementations
def context_ingestion_node(state: CreditState) -> Dict[str, Any]:
    audit = state.get("audit_trail", [])
    audit.append(f"[ContextIngestion] Ingested query for borrower {state['borrower_id']}")
    context_str = f"Borrower: {state['borrower_id']} | Facility: ${state['requested_amount']:,.2f}"
    return {
        "formatted_context": context_str,
        "audit_trail": [f"[ContextIngestion] Ingested query for borrower {state['borrower_id']}"]
    }

def macro_rate_step_node(state: CreditState) -> Dict[str, Any]:
    audit = state.get("audit_trail", [])
    # Call decoupled Treasury rates worker
    rate_data = _macro_worker.rates_client.fetch_live_market_benchmarks()
    live_sofr = rate_data.get("sofr_benchmark_rate", 4.75)
    source = rate_data.get("source", "Unknown")
    
    audit.append(f"[MacroRateNode] Fetched rate benchmark: {live_sofr}% via {source}")
    return {
        "macro_benchmark_rate": live_sofr,
        "macro_rate_source": source,
        "audit_trail": [f"[MacroRateNode] Fetched rate benchmark: {live_sofr}% via {source}"]
    }

def risk_assessment_node(state: CreditState) -> Dict[str, Any]:
    amount = state["requested_amount"]
    audit = state.get("audit_trail", [])
    
    if amount > 10_000_000:
        score = 8.5
        analysis = "High exposure facility requiring tier-1 credit committee approval."
    elif amount > 5_000_000:
        score = 6.2
        analysis = "Moderate-high exposure facility requiring senior officer review."
    else:
        score = 3.1
        analysis = "Standard exposure within automated delegation limit."

    audit.append(f"[RiskAssessment] Assessed Risk Score: {score}")
    return {
        "risk_score": score,
        "risk_analysis": analysis,
        "audit_trail": [f"[RiskAssessment] Assessed Risk Score: {score}"]
    }


def compliance_node(state: CreditState) -> Dict[str, Any]:
    tenant = state["tenant_id"]
    audit = state.get("audit_trail", [])
    is_compliant = tenant.startswith("TENANT-")
    audit.append(f"[ComplianceGate] Tenant check for {tenant}: Passed={is_compliant}")
    return {
        "compliance_passed": is_compliant,
        "audit_trail": [f"[ComplianceGate] Tenant check for {tenant}: Passed={is_compliant}"]
    }


def policy_router(state: CreditState) -> str:
    amount = state["requested_amount"]
    score = state.get("risk_score", 0.0)
    compliant = state.get("compliance_passed", True)

    if amount > 5_000_000 or score > 7.0 or not compliant:
        return "hitl_breakpoint"
    return "final_decision"


def hitl_breakpoint_node(state: CreditState) -> Dict[str, Any]:
    audit = state.get("audit_trail", [])
    reason = f"Loan amount ${state['requested_amount']:,.2f} or Risk Score {state['risk_score']} exceeded automated threshold."
    audit.append(f"[HITL_Breakpoint] PAUSED for Credit Officer review. Reason: {reason}")
    
    # Preserve human_approval_status if already set via update_state
    current_status = state.get("human_approval_status", "NONE")
    status = current_status if current_status != "NONE" else "PENDING"

    return {
        "hitl_required": True,
        "hitl_reason": reason,
        "human_approval_status": status,
        "audit_trail": [f"[HITL_Breakpoint] PAUSED for Credit Officer review. Reason: {reason}"]
    }


def final_decision_node(state: CreditState) -> Dict[str, Any]:
    audit = state.get("audit_trail", [])
    status = state.get("human_approval_status", "NONE")
    
    if state.get("hitl_required") and status != "APPROVED":
        decision = "REJECTED_OR_PENDING"
    else:
        decision = "APPROVED"

    audit.append(f"[FinalDecision] Workflow completed with status: {decision}")
    return {
        "audit_trail": [f"[FinalDecision] Workflow completed with status: {decision}"]
    }


# 3. Graph Assembly with Flexible Checkpointer
def build_credit_graph(checkpointer=None):
    builder = StateGraph(CreditState)

    builder.add_node("context_ingestion", context_ingestion_node)
    builder.add_node("macro_rate_fetch", macro_rate_step_node) # <--- NEW NODE
    builder.add_node("risk_assessment", risk_assessment_node)
    builder.add_node("compliance", compliance_node)
    builder.add_node("hitl_breakpoint", hitl_breakpoint_node)
    builder.add_node("final_decision", final_decision_node)

    builder.add_edge(START, "context_ingestion")
    builder.add_edge("context_ingestion", "macro_rate_fetch")  # <--- NEW EDGE
    builder.add_edge("macro_rate_fetch", "risk_assessment")    # <--- NEW EDGE
    builder.add_edge("context_ingestion", "risk_assessment")
    builder.add_edge("risk_assessment", "compliance")

    builder.add_conditional_edges(
        "compliance",
        policy_router,
        {
            "hitl_breakpoint": "hitl_breakpoint",
            "final_decision": "final_decision"
        }
    )

    builder.add_edge("hitl_breakpoint", "final_decision")
    builder.add_edge("final_decision", END)

    # Use provided checkpointer or fallback to MemorySaver for local tests
    active_checkpointer = checkpointer if checkpointer is not None else MemorySaver()
    
    return builder.compile(
        checkpointer=active_checkpointer,
        interrupt_before=["hitl_breakpoint"]
    )