import pytest
from ingestion.graph_sync import GraphSyncEngine
from retrieval.hybrid_engine_dict import HybridRetrievalEngine

@pytest.fixture
def populated_retrieval_setup():
    graph = GraphSyncEngine()
    retriever = HybridRetrievalEngine(graph_sync=graph)

    # Clause 1: TENANT-EMEA
    retriever.index_chunk(
        chunk_id="SEC-14.2",
        content="Section 14.2 European Subsidiary Liability active.",
        metadata={"document_id": "DOC-882", "tenant_id": "TENANT-EMEA", "section_id": "SEC-14.2"},
        vector=[0.1, 0.8, 0.3]
    )
    graph.nodes[graph.get_node_id("DOC-882", "SEC-14.2")] = {
        "text": "Section 14.2 European Subsidiary Liability active.",
        "tenant_id": "TENANT-EMEA",
        "is_amendment": False
    }

    # Clause 2: TENANT-US (Isolation boundary target)
    retriever.index_chunk(
        chunk_id="SEC-10.1",
        content="Section 10.1 US Subsidiary Guarantee active.",
        metadata={"document_id": "DOC-900", "tenant_id": "TENANT-US", "section_id": "SEC-10.1"},
        vector=[0.1, 0.85, 0.35]
    )

    # Ingest Amendment effective Aug 1, 2026 for TENANT-EMEA
    graph.sync_amendment_node(
        doc_id="DOC-882",
        chunk_id="SEC-14.2",
        source_id="SHAREPOINT-EMEA-01",
        amended_text="Section 14.2 Amendment 3 European Subsidiary Liability revoked.",
        effective_date="2026-08-01",
        tenant_id="TENANT-EMEA"
    )

    return retriever

def test_tenant_isolation(populated_retrieval_setup):
    retriever = populated_retrieval_setup
    query_vec = [0.1, 0.8, 0.3]

    results = retriever.hybrid_search(
        query_vector=query_vec,
        query_text="Section 14.2 European Liability",
        tenant_id="TENANT-EMEA",
        as_of_date="2026-06-15"
    )

    assert len(results) == 1
    assert results[0]["chunk_id"] == "SEC-14.2"
    assert results[0]["metadata"]["tenant_id"] == "TENANT-EMEA"

def test_temporal_graph_resolution(populated_retrieval_setup):
    retriever = populated_retrieval_setup
    query_vec = [0.1, 0.8, 0.3]

    # Query before amendment date returns original clause text
    pre_results = retriever.hybrid_search(
        query_vector=query_vec,
        query_text="Section 14.2 European Liability",
        tenant_id="TENANT-EMEA",
        as_of_date="2026-06-15"
    )
    assert pre_results[0]["is_amended"] is False
    assert "active" in pre_results[0]["content"]

    # Query after amendment date returns superseding amendment text
    post_results = retriever.hybrid_search(
        query_vector=query_vec,
        query_text="Section 14.2 European Liability",
        tenant_id="TENANT-EMEA",
        as_of_date="2026-08-15"
    )
    assert post_results[0]["is_amended"] is True
    assert "revoked" in post_results[0]["content"]