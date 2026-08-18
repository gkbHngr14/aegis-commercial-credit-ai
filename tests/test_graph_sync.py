import pytest
from ingestion.graph_sync import GraphSyncEngine

def test_temporal_edge_expiration():
    engine = GraphSyncEngine()
    orig_clause_id = "SEC-14.2"
    doc_id = "DOC-882"
    target_node_key = engine.get_node_id(doc_id, orig_clause_id)
    
    # Ingest amendment effective Aug 1, 2026
    res = engine.sync_amendment_node(
        doc_id=doc_id,
        chunk_id=orig_clause_id,
        source_id="SHAREPOINT-EMEA-01",
        amended_text="Section 14.2 Amendment 3: European subsidiary liability revoked.",
        effective_date="2026-08-01",
        tenant_id="TENANT-EMEA"
    )
    assert res["status"] == "SUCCESS"

    # Query before amendment date returns original clause
    pre_state = engine.query_clause_as_of(clause_id=target_node_key, as_of_date="2026-06-15")
    assert pre_state["is_amended"] is False
    assert pre_state["node_id"] == target_node_key

    # Query on or after amendment date returns amended clause
    post_state = engine.query_clause_as_of(clause_id=target_node_key, as_of_date="2026-08-17")
    assert post_state["is_amended"] is True
    assert post_state["node_id"] != target_node_key

def test_sanitization_and_quarantine_dlq():
    engine = GraphSyncEngine()
    
    # Corrupted tenant_id format triggers quarantine DLQ path
    bad_res = engine.sync_amendment_node(
        doc_id="DOC-882",
        chunk_id="SEC-14.2",
        source_id="SHAREPOINT-EMEA-01",
        amended_text="Some valid text",
        effective_date="2026-08-01",
        tenant_id="INVALID_TENANT"
    )
    assert bad_res["status"] == "QUARANTINED"
    assert bad_res["dlq_routed"] is True