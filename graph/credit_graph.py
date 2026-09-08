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
from agents.qdrant_retrieval_node import QdrantRetrievalNode
from retrieval.qdrant_store import QdrantVectorStore

# 1. Instantiate Shared Worker Singletons
_macro_worker = MacroRateNode()

# Initialize Qdrant store and seed baseline policy document
_qdrant_store = QdrantVectorStore(vector_size=3)
_qdrant_store.upsert_chunk(
    chunk_id="policy-default-001",
    vector=[0.1, 0.2, 0.3],
    content="Commercial facilities exceeding $10M require tier-1 committee approval and secondary collateral.",
    metadata={"tenant_id": "TENANT-US", "document_id": "CREDIT-POLICY-2026", "section_id": "SEC-4"}
)
_retrieval_worker = QdrantRetrievalNode(vector_store=_qdrant_store)


# 2. Shared State Schema
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


# 3. Graph Node Functions
def context_ingestion_node(state: CreditState) -> Dict[str, Any]:
    context_str = f"Borrower: {state['borrower_id']} | Facility: ${state['requested_amount']:,.2f}"
    return {
        "formatted_context": context_str,
        "audit_trail": [f"[ContextIngestion] Ingested query for borrower {state['borrower_id']}"]
    }

def qdrant_retrieval_step_node(state: CreditState) -> Dict[str, Any]:
    return _retrieval_worker.retrieve_context(state)

def macro_rate_step_node(state: CreditState) -> Dict[str, Any]:
    rate_data = _macro_worker.rates_client.fetch_live_market_benchmarks()
    live_sofr = rate_data.get("sofr_benchmark_rate", 4.75)
    source = rate_data.get("source", "Unknown")
    
    return {
        "macro_benchmark_rate": live_sofr,
        "macro_rate_source": source,
        "audit_trail": [f"[MacroRateNode] Fetched rate benchmark: {live_sofr}% via {source}"]
    }

def risk_assessment_node(state: CreditState) -> Dict[str, Any]:
    amount = state["requested_amount"]
    if amount > 10_000_000:
        score = 8.5
        analysis = "High exposure facility requiring tier-1 credit committee approval."
    elif amount > 5_000_000:
        score = 6.2
        analysis = "Moderate-high exposure facility requiring senior officer review."
    else:
        score = 3.1
        analysis = "Standard exposure within automated delegation limit."

    return {
        "risk_score": score,
        "risk_analysis": analysis,
        "audit_trail": [f"[RiskAssessment] Assessed Risk Score: {score}"]
    }

def compliance_node(state: CreditState) -> Dict[str, Any]:
    tenant = state["tenant_id"]
    is_compliant = tenant.startswith("TENANT-")
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
    reason = f"Loan amount ${state['requested_amount']:,.2f} or Risk Score {state['risk_score']} exceeded automated threshold."
    current_status = state.get("human_approval_status", "NONE")
    status = current_status if current_status != "NONE" else "PENDING"

    return {
        "hitl_required": True,
        "hitl_reason": reason,
        "human_approval_status": status,
        "audit_trail": [f"[HITL_Breakpoint] PAUSED for Credit Officer review. Reason: {reason}"]
    }

def final_decision_node(state: CreditState) -> Dict[str, Any]:
    status = state.get("human_approval_status", "NONE")
    if state.get("hitl_required") and status != "APPROVED":
        decision = "REJECTED_OR_PENDING"
    else:
        decision = "APPROVED"

    return {
        "audit_trail": [f"[FinalDecision] Workflow completed with status: {decision}"]
    }


# 4. Graph Assembly
def build_credit_graph(checkpointer=None):
    builder = StateGraph(CreditState)

    builder.add_node("context_ingestion", context_ingestion_node)
    builder.add_node("qdrant_retrieval", qdrant_retrieval_step_node)
    builder.add_node("macro_rate_fetch", macro_rate_step_node)
    builder.add_node("risk_assessment", risk_assessment_node)
    builder.add_node("compliance", compliance_node)
    builder.add_node("hitl_breakpoint", hitl_breakpoint_node)
    builder.add_node("final_decision", final_decision_node)

    # Sequential Edge Chain
    builder.add_edge(START, "context_ingestion")
    builder.add_edge("context_ingestion", "qdrant_retrieval")
    builder.add_edge("qdrant_retrieval", "macro_rate_fetch")
    builder.add_edge("macro_rate_fetch", "risk_assessment")
    builder.add_edge("risk_assessment", "compliance")

    # Dynamic Routing
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

    active_checkpointer = checkpointer if checkpointer is not None else MemorySaver()
    
    return builder.compile(
        checkpointer=active_checkpointer,
        interrupt_before=["hitl_breakpoint"]
    )