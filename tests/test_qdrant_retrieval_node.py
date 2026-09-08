import pytest
from retrieval.qdrant_store import QdrantVectorStore
from agents.qdrant_retrieval_node import QdrantRetrievalNode
from graph.state import CreditState

def test_qdrant_node_tenant_isolated_retrieval():
    # 1. Instantiate Store and Seed Multi-Tenant Data
    store = QdrantVectorStore(vector_size=3)
    
    # Ingest Tenant A Chunk
    store.upsert_chunk(
        chunk_id="chunk-101",
        vector=[0.1, 0.2, 0.3],
        content="Tenant A credit policy: Facility limit is $20M.",
        metadata={"tenant_id": "TENANT-A", "document_id": "POLICY-A", "section_id": "SEC-1"}
    )
    
    # Ingest Tenant B Chunk
    store.upsert_chunk(
        chunk_id="chunk-202",
        vector=[0.1, 0.2, 0.3],
        content="Tenant B credit policy: Facility limit is $5M.",
        metadata={"tenant_id": "TENANT-B", "document_id": "POLICY-B", "section_id": "SEC-2"}
    )

    # 2. Instantiate Retrieval Node with Seeded Store
    node = QdrantRetrievalNode(vector_store=store)

    # 3. Query for Tenant A
    state_a: CreditState = {
        "tenant_id": "TENANT-A",
        "user_query": "What is the facility limit?",
        "audit_trail": []
    }
    
    result_a = node.retrieve_context(state_a)

    # Assert Tenant A receives ONLY Tenant A data
    assert len(result_a["retrieved_chunks"]) == 1
    assert result_a["retrieved_chunks"][0]["chunk_id"] == "chunk-101"
    assert "Tenant A credit policy" in result_a["formatted_context"]
    assert "TENANT-A" in result_a["audit_trail"][0]