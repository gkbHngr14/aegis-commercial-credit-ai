from typing import Dict, Any, Optional
from utils.sanitizer import PayloadSanitizer, ValidationException

class GraphSyncEngine:
    def __init__(self, neptune_endpoint: str = "mock://localhost"):
        self.endpoint = neptune_endpoint
        # In-memory mock store for graph nodes and temporal edges
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: Dict[str, Dict[str, Any]] = {}

    def get_node_id(self, doc_id: str, chunk_id: str) -> str:
        return f"{doc_id}::{chunk_id}"

    def sync_amendment_node(
        self,
        doc_id: str,
        chunk_id: str,
        source_id: str,
        amended_text: str,
        effective_date: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        
        raw_payload = {
            "doc_id": doc_id, "chunk_id": chunk_id, "source_id": source_id,
            "amended_text": amended_text, "effective_date": effective_date, "tenant_id": tenant_id
        }

        try:
            clean_text = PayloadSanitizer.clean_and_sanitize(amended_text)
            PayloadSanitizer.validate_metadata(tenant_id, effective_date)

            target_node_id = self.get_node_id(doc_id, chunk_id)
            amendment_node_id = f"AMD-{doc_id}-{chunk_id}"

            # Create amendment node
            self.nodes[amendment_node_id] = {
                "text": clean_text,
                "tenant_id": tenant_id,
                "source_id": source_id,
                "effective_date": effective_date,
                "is_amendment": True
            }

            # Atomic temporal edge patch: expire old edge, link SUPERSEDES edge
            self.edges[target_node_id] = {
                "expiration_date": effective_date,
                "superseded_by": amendment_node_id
            }

            return {"status": "SUCCESS", "amendment_node_id": amendment_node_id, "superseded_node_id": target_node_id}

        except ValidationException as err:
            return {"status": "QUARANTINED", "error": str(err), "dlq_routed": True, "payload": raw_payload}

    def query_clause_as_of(self, clause_id: str, as_of_date: str) -> Dict[str, Any]:
        edge_info = self.edges.get(clause_id)
        if edge_info and as_of_date >= edge_info["expiration_date"]:
            amd_id = edge_info["superseded_by"]
            node_data = self.nodes.get(amd_id, {})
            return {"node_id": amd_id, "is_amended": True, "text": node_data.get("text")}
        
        return {"node_id": clause_id, "is_amended": False, "text": "Original Clause Content"}