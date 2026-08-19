import uuid
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

class QdrantVectorStore:
    def __init__(self, collection_name: str = "aegis_chunks", vector_size: int = 3):
        """
        Initializes an in-memory Qdrant instance.
        In production, replace ':memory:' with host/port or Qdrant Cloud URL.
        """
        self.client = QdrantClient(":memory:")
        self.collection_name = collection_name
        self.vector_size = vector_size

        # Modern collection initialization (replaces deprecated recreate_collection)
        if self.client.collection_exists(self.collection_name):
            self.client.delete_collection(self.collection_name)

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
        )

    def upsert_chunk(self, chunk_id: str, vector: List[float], content: str, metadata: Dict[str, Any]) -> None:
        """
        Upserts a chunk into Qdrant.
        Stores raw content and lineage metadata inside the point payload.
        """
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_id))
        
        payload = {
            "chunk_id": chunk_id,
            "content": content,
            "tenant_id": metadata.get("tenant_id"),
            "document_id": metadata.get("document_id"),
            "section_id": metadata.get("section_id"),
            "metadata": metadata
        }

        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload
                )
            ]
        )

    def search_tenant_isolated(
        self,
        query_vector: List[float],
        tenant_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Executes dense vector search WITH hard payload filtering on tenant_id.
        Cross-tenant data is filtered at the DB engine layer before similarity evaluation.
        """
        tenant_filter = Filter(
            must=[
                FieldCondition(
                    key="tenant_id",
                    match=MatchValue(value=tenant_id)
                )
            ]
        )

        # Updated API: query_points replaces search()
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=tenant_filter,
            limit=limit
        )

        hits = []
        for point in response.points:
            hits.append({
                "chunk_id": point.payload["chunk_id"],
                "content": point.payload["content"],
                "score": point.score,
                "metadata": point.payload["metadata"]
            })

        return hits