import pytest
from ingestion.graph_sync import GraphSyncEngine
from retrieval.hybrid_engine import HybridRetrievalEngine

def test_qdrant_hybrid_search_tenant_isolation():
    graph = GraphSyncEngine()
    retriever = HybridRetrievalEngine(graph_sync=graph, vector_size=3)

    # Tenant EMEA chunk
    retriever.index_chunk(
        chunk_id="SEC-100",
        content="European Credit Line active.",
        metadata={"document_id": "DOC-100", "tenant_id": "TENANT-EMEA"},
        vector=[0.1, 0.9, 0.2]
    )

    # Tenant US chunk
    retriever.index_chunk(
        chunk_id="SEC-200",
        content="US Credit Line active.",
        metadata={"document_id": "DOC-200", "tenant_id": "TENANT-US"},
        vector=[0.1, 0.95, 0.25]
    )

    # Search as TENANT-EMEA
    results = retriever.hybrid_search(
        query_vector=[0.1, 0.9, 0.2],
        query_text="European Credit Line",
        tenant_id="TENANT-EMEA",
        as_of_date="2026-08-01"
    )

    assert len(results) == 1
    assert results[0]["chunk_id"] == "SEC-100"
    assert results[0]["metadata"]["tenant_id"] == "TENANT-EMEA"