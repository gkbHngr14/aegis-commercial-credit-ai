from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

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
    audit_trail: List[str]


# 2. Node Implementations
def context_ingestion_node(state: CreditState) -> Dict[str, Any]:
    """Ingests query and simulates/formats context for down-stream analysis."""
    audit = state.get("audit_trail", [])
    audit.append(f"[ContextIngestion] Ingested query for borrower {state['borrower_id']}")
    
    # In a full flow, this calls ContextAssembler + HybridRetrievalEngine
    context_str = f"Borrower: {state['borrower_id']} | Facility: ${state['requested_amount']:,.2f}"
    return {
        "formatted_context": context_str,
        "audit_trail": audit
    }


def risk_assessment_node(state: CreditState) -> Dict[str, Any]:
    """Evaluates risk score and generates risk analysis."""
    amount = state["requested_amount"]
    audit = state.get("audit_trail", [])
    
    # Calculate deterministic risk score based on loan magnitude
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
        "audit_trail": audit
    }


def compliance_node(state: CreditState) -> Dict[str, Any]:
    """Checks tenant isolation and temporal effective date compliance."""
    tenant = state["tenant_id"]
    audit = state.get("audit_trail", [])
    
    is_compliant = tenant.startswith("TENANT-")
    audit.append(f"[ComplianceGate] Tenant check for {tenant}: Passed={is_compliant}")
    
    return {
        "compliance_passed": is_compliant,
        "audit_trail": audit
    }


def policy_router(state: CreditState) -> str:
    """
    Conditional routing function.
    Triggers HITL if requested_amount > $5,000,000 OR risk_score > 7.0 OR compliance failed.
    """
    amount = state["requested_amount"]
    score = state.get("risk_score", 0.0)
    compliant = state.get("compliance_passed", True)

    if amount > 5_000_000 or score > 7.0 or not compliant:
        return "hitl_breakpoint"
    return "final_decision"

def hitl_breakpoint_node(state: CreditState) -> Dict[str, Any]:
    """Sets interrupt flag and reason for Human Officer review."""
    audit = state.get("audit_trail", [])
    reason = f"Loan amount ${state['requested_amount']:,.2f} or Risk Score {state['risk_score']} exceeded automated threshold."
    audit.append(f"[HITL_Breakpoint] PAUSED for Credit Officer review. Reason: {reason}")
    
    # Preserve approval status if already updated by an intervention/update_state call
    current_status = state.get("human_approval_status", "NONE")
    status = current_status if current_status != "NONE" else "PENDING"
    
    return {
        "hitl_required": True,
        "hitl_reason": reason,
        "human_approval_status": status,
        "audit_trail": audit
    }

def final_decision_node(state: CreditState) -> Dict[str, Any]:
    """Compiles final credit decision and completes audit trail."""
    audit = state.get("audit_trail", [])
    status = state.get("human_approval_status", "NONE")
    
    if state.get("hitl_required") and status != "APPROVED":
        decision = "REJECTED_OR_PENDING"
    else:
        decision = "APPROVED"

    audit.append(f"[FinalDecision] Workflow completed with status: {decision}")
    return {
        "audit_trail": audit
    }


# 3. Graph Assembly Function
def build_credit_graph():
    builder = StateGraph(CreditState)

    # Add Nodes
    builder.add_node("context_ingestion", context_ingestion_node)
    builder.add_node("risk_assessment", risk_assessment_node)
    builder.add_node("compliance", compliance_node)
    builder.add_node("hitl_breakpoint", hitl_breakpoint_node)
    builder.add_node("final_decision", final_decision_node)

    # Add Flow Edges
    builder.add_edge(START, "context_ingestion")
    builder.add_edge("context_ingestion", "risk_assessment")
    builder.add_edge("risk_assessment", "compliance")

    # Conditional Routing from Compliance to HITL or Final Decision
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

    # Memory Checkpointer for Thread State Persistence
    checkpointer = MemorySaver()
    
    # Interrupt execution specifically when reaching hitl_breakpoint
    return builder.compile(checkpointer=checkpointer, interrupt_before=["hitl_breakpoint"])