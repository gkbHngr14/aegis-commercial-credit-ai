from typing import Dict, Any, List
from graph.state import CreditState

class QdrantRetrievalNode:
    """
    Agentic retrieval worker node that interfaces with QdrantVectorStore.
    Executes tenant-isolated vector searches to populate CreditState.
    """
    def __init__(self, vector_store=None):
        # Uses provided QdrantVectorStore or instantiates a fresh local instance
        if vector_store is None:
            from store.qdrant_store import QdrantVectorStore
            self.store = QdrantVectorStore()
        else:
            self.store = vector_store

    def retrieve_context(self, state: CreditState) -> Dict[str, Any]:
        """
        Retrieves tenant-isolated chunks and formats them for downstream LLM prompts.
        """
        tenant_id = state.get("tenant_id", "DEFAULT_TENANT")
        user_query = state.get("user_query", "")
        
        # Mock/deterministic query vector matching store dimensionality (3 dimensions)
        # In production: query_vector = self.embedding_model.embed(user_query)
        query_vector = [0.1, 0.2, 0.3]

        # Execute tenant-isolated search
        hits = self.store.search_tenant_isolated(
            query_vector=query_vector,
            tenant_id=tenant_id,
            limit=3
        )

        formatted_chunks = []
        for hit in hits:
            doc_id = hit["metadata"].get("document_id", "Doc")
            sec_id = hit["metadata"].get("section_id", "Section")
            formatted_chunks.append(f"[{doc_id} - {sec_id}]: {hit['content']}")

        formatted_context = "\n".join(formatted_chunks) if formatted_chunks else "No relevant context found."

        audit_msg = f"[QdrantRetrievalNode] Retrieved {len(hits)} chunks for tenant '{tenant_id}'"

        return {
            "retrieved_chunks": hits,
            "formatted_context": formatted_context,
            "audit_trail": [audit_msg]
        }