import math
from typing import List, Dict, Any, Optional
from ingestion.graph_sync import GraphSyncEngine
from retrieval.qdrant_store import QdrantVectorStore

class HybridRetrievalEngine:
    def __init__(self, graph_sync: GraphSyncEngine, vector_size: int = 3):
        self.graph_sync = graph_sync
        self.qdrant = QdrantVectorStore(vector_size=vector_size)
        # Store for Sparse BM25 evaluation
        self.text_store: Dict[str, Dict[str, Any]] = {}

    def index_chunk(self, chunk_id: str, content: str, metadata: Dict[str, Any], vector: List[float]) -> None:
        """Indexes chunk into both Qdrant (dense) and text_store (sparse BM25)."""
        # 1. Upsert into Qdrant Vector Engine
        self.qdrant.upsert_chunk(chunk_id=chunk_id, vector=vector, content=content, metadata=metadata)
        
        # 2. Store in text_store for BM25 search
        self.text_store[chunk_id] = {
            "chunk_id": chunk_id,
            "content": content,
            "metadata": metadata
        }

    def _compute_bm25_score(self, query_text: str, doc_text: str) -> float:
        """BM25 term frequency calculation."""
        query_terms = query_text.lower().split()
        doc_terms = doc_text.lower().split()
        if not query_terms or not doc_terms:
            return 0.0

        score = 0.0
        doc_len = len(doc_terms)
        for term in query_terms:
            tf = doc_terms.count(term)
            if tf > 0:
                score += (tf * 2.2) / (tf + 1.2 * (1.0 - 0.75 + 0.75 * (doc_len / 50.0)))
        return score

    def hybrid_search(
        self,
        query_vector: List[float],
        query_text: str,
        tenant_id: str,
        as_of_date: str,
        top_k: int = 3,
        rrf_k: int = 60
    ) -> List[Dict[str, Any]]:
        # Security Pre-flight Guard
        if not tenant_id or not tenant_id.startswith("TENANT-"):
            raise ValueError(f"Security Violation: Unauthorized tenant_id '{tenant_id}'.")

        # --- Layer 1: Qdrant Engine Dense Search with Tenant Isolation ---
        qdrant_dense_hits = self.qdrant.search_tenant_isolated(
            query_vector=query_vector,
            tenant_id=tenant_id,
            limit=20
        )

        if not qdrant_dense_hits:
            return []

        # Dense Ranks mapping: chunk_id -> rank
        dense_ranks = {hit["chunk_id"]: rank for rank, hit in enumerate(qdrant_dense_hits, start=1)}

        # --- Layer 2: Sparse BM25 Keyword Search ---
        tenant_text_chunks = [
            doc for doc in self.text_store.values()
            if doc["metadata"].get("tenant_id") == tenant_id
        ]
        
        sparse_ranked = sorted(
            tenant_text_chunks,
            key=lambda doc: self._compute_bm25_score(query_text, doc["content"]),
            reverse=True
        )
        sparse_ranks = {doc["chunk_id"]: rank for rank, doc in enumerate(sparse_ranked, start=1)}

        # --- Layer 3 & 4: Temporal Graph Sync & RRF Fusion ---
        fused_results = []
        for hit in qdrant_dense_hits:
            cid = hit["chunk_id"]
            meta = hit["metadata"]
            doc_id = meta.get("document_id", "DOC-UNK")

            # Point-in-time temporal resolution against GraphSyncEngine
            graph_node_key = self.graph_sync.get_node_id(doc_id, cid)
            temporal_state = self.graph_sync.query_clause_as_of(graph_node_key, as_of_date)

            active_content = temporal_state.get("text") or hit["content"]

            r_dense = dense_ranks.get(cid, 999)
            r_sparse = sparse_ranks.get(cid, 999)
            rrf_score = (1.0 / (rrf_k + r_dense)) + (1.0 / (rrf_k + r_sparse))

            fused_results.append({
                "chunk_id": cid,
                "node_id": temporal_state["node_id"],
                "content": active_content,
                "is_amended": temporal_state["is_amended"],
                "rrf_score": round(rrf_score, 6),
                "metadata": meta
            })

        fused_results.sort(key=lambda x: x["rrf_score"], reverse=True)
        return fused_results[:top_k]