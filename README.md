# Aegis Commercial Credit AI (`aegis-commercial-credit-ai`)

> Enterprise-grade, agentic commercial credit evaluation platform built with LangGraph, Qdrant multi-tenant RAG, real-time macro-economic benchmark fetching, and Human-in-the-Loop (HITL) governance.

---

## 🏛 System Architecture Overview

Aegis orchestrates commercial credit risk evaluation using a state-directed DAG topology. It enforces strict input payload validation, tenant-isolated vector retrieval for credit policy compliance, real-time market benchmark ingestion, and dynamic policy routing for high-exposure facilities.

[START]
│
▼

[context_ingestion] ────> Validates input payload & sanitizes queries
│
▼

[qdrant_retrieval]  ────> Executes DB-layer tenant-isolated RAG search
│                         Populates retrieved_chunks & formatted_context
▼

[macro_rate_fetch]  ────> Ingests real-time US Treasury / market rates
│                         Includes circuit-breaker fallbacks
▼

[risk_assessment]   ────> Computes risk score using RAG context + macro rates
│
▼

[compliance]        ────> Verifies regulatory tenant rules
│
▼

[policy_router]     ────> Dynamic conditional edge routing
├──> [hitl_breakpoint] ──> Interrupts execution for Credit Officer override
└──> [final_decision]  ──> Automated terminal credit decisioning

---

## ✨ Key Features

- **State-Directed Graph Orchestration:** Deterministic LangGraph workflow preventing race conditions and unbounded execution loops.
- **Zero-Trust Multi-Tenancy:** Hard payload filtering at the Qdrant vector engine layer prevents cross-tenant data leakage.
- **Resilient Macro Benchmark Client:** Fetches live market benchmarks with circuit-breaker fallbacks to ensure $99.99\%$ pipeline availability.
- **Thread-Safe Audit Reducers:** Implements `Annotated[List[str], operator.add]` state reducers for immutable append-only audit logging.
- **HITL Breakpoint Governance:** Built-in breakpoint triggers for large facilities ($>\$5\text{M}$ or Risk Score $>7.0$) allowing credit officer override and seamless state resumption.
- **Fail-Fast Ingestion Guards:** Edge validation layer catching malformed amounts, missing tenant headers, or query injection attempts.

---

## 📁 Repository Structure

aegis-commercial-credit-ai/
├── agents/
│   ├── macro_rate_node.py        # Isolated macro benchmark worker
│   └── qdrant_retrieval_node.py  # Tenant-isolated RAG retrieval node
├── api/
│   └── rates_client.py           # US Treasury HTTP client with circuit breaker
├── graph/
│   ├── credit_graph.py           # Core LangGraph assembly & execution edges
│   └── state.py                  # CreditState TypedDict & state reducers
├── store/
│   └── qdrant_store.py           # Qdrant client wrapper & tenant query_points
├── utils/
│   └── data_guards.py            # Payload validation guards & boundary checks
└── tests/
├── test_credit_graph.py      # Graph integration & HITL resume tests
├── test_data_guard.py        # Fail-fast validation unit tests
├── test_live_rates_and_node.py # Benchmark client & node unit tests
└── test_qdrant_retrieval_node.py # Tenant-isolation RAG unit tests

---

## 🚀 Quickstart & Testing

### 1. Prerequisites & Installation
```bash
git clone [https://github.com/your-username/aegis-commercial-credit-ai.git](https://github.com/your-username/aegis-commercial-credit-ai.git)
cd aegis-commercial-credit-ai
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

2. Running Test Suite
Execute the full integration test suite (23+ tests):

pytest tests/ -p no:langsmith

