import math
from typing import List, Dict, Any, Optional
from ingestion.graph_sync import GraphSyncEngine

class HybridRetrievalEngine:
    def __init__(self, graph_sync: GraphSyncEngine):
        """
        Injects the GraphSyncEngine dependency so the retriever can 
        resolve active node versions based on as_of_date.
        """
        self.graph_sync = graph_sync
        # Simulated vector & text store mapping chunk_id -> {content, metadata, vector}
        self.vector_store: Dict[str, Dict[str, Any]] = {}

    def index_chunk(self, chunk_id: str, content: str, metadata: Dict[str, Any], vector: List[float]) -> None:
        """Stores a chunk and its dense embedding in the local index."""
        self.vector_store[chunk_id] = {
            "chunk_id": chunk_id,
            "content": content,
            "metadata": metadata,
            "vector": vector
        }

    def _cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        """Calculates normalized cosine similarity between two vector embeddings."""
        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        return dot_product / (norm_a * norm_b) if norm_a and norm_b else 0.0

    def _compute_bm25_score(self, query_text: str, doc_text: str) -> float:
        """
        Simplified BM25-style term frequency score for exact-match targeting
        (e.g., matching section IDs like 'SEC-14.2' or exact numbers).
        """
        query_terms = query_text.lower().split()
        doc_terms = doc_text.lower().split()
        if not query_terms or not doc_terms:
            return 0.0

        score = 0.0
        doc_len = len(doc_terms)
        for term in query_terms:
            tf = doc_terms.count(term)
            if tf > 0:
                # Saturation scoring formula for exact term hits
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
        """
        Executes hybrid retrieval:
        1. Layer 1 & 2: Dense Cosine & Sparse BM25 evaluation (Tenant Isolated).
        2. Layer 3: Temporal Graph resolution (as_of_date edge traversal).
        3. Layer 4: Reciprocal Rank Fusion (RRF) candidate merging.
        """
        # Pre-flight Tenant Security Guard
        if not tenant_id or not tenant_id.startswith("TENANT-"):
            raise ValueError(f"Security Violation: Unauthorized or invalid tenant_id '{tenant_id}'.")

        # --- Step 1: Filter Store strictly by validated tenant_id ---
        tenant_valid_chunks = [
            doc for doc in self.vector_store.values()
            if doc["metadata"].get("tenant_id") == tenant_id
        ]

        if not tenant_valid_chunks:
            return []

        # --- Step 2: Layer 1 - Dense Vector Ranking ---
        dense_ranked = sorted(
            tenant_valid_chunks,
            key=lambda doc: self._cosine_similarity(query_vector, doc["vector"]),
            reverse=True
        )
        dense_ranks = {doc["chunk_id"]: rank for rank, doc in enumerate(dense_ranked, start=1)}

        # --- Step 3: Layer 2 - Sparse BM25 Keyword Ranking ---
        sparse_ranked = sorted(
            tenant_valid_chunks,
            key=lambda doc: self._compute_bm25_score(query_text, doc["content"]),
            reverse=True
        )
        sparse_ranks = {doc["chunk_id"]: rank for rank, doc in enumerate(sparse_ranked, start=1)}

        # --- Step 4 & 5: Layer 3 & 4 - Temporal Graph Sync & RRF Fusion ---
        fused_results = []
        for doc in tenant_valid_chunks:
            cid = doc["chunk_id"]
            meta = doc["metadata"]
            doc_id = meta.get("document_id", "DOC-UNK")

            # Point-in-time temporal resolution against GraphSyncEngine
            graph_node_key = self.graph_sync.get_node_id(doc_id, cid)
            temporal_state = self.graph_sync.query_clause_as_of(graph_node_key, as_of_date)

            active_content = temporal_state.get("text") or doc["content"]

            # Calculate RRF Score combining Dense and Sparse rankings
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

        # Sort candidates by merged RRF score descending
        fused_results.sort(key=lambda x: x["rrf_score"], reverse=True)
        return fused_results[:top_k]