from dataclasses import dataclass, field
from typing import Dict, Any, List

@dataclass
class Chunk:
    chunk_id: str
    content: str
    chunk_type: str  # "NARRATIVE" or "TABLE"
    token_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)

class SectionAwareChunker:
    def __init__(self, max_tokens: int = 1000):
        self.max_tokens = max_tokens

    def chunk_document(self, elements: List[Dict[str, Any]]) -> List[Chunk]:
        chunks = []
        for idx, elem in enumerate(elements):
            text = elem.get("text", "").strip()
            metadata = elem.get("metadata", {})
            elem_type = elem.get("element_type", "NarrativeText")
            
            chunk_type = "TABLE" if elem_type == "Table" else "NARRATIVE"
            estimated_tokens = int(len(text.split()) * 1.3)
            
            chunks.append(
                Chunk(
                    chunk_id=f"CHK-{metadata.get('document_id', 'UNK')}-{idx:04d}",
                    content=text,
                    chunk_type=chunk_type,
                    token_count=estimated_tokens,
                    metadata=metadata
                )
            )
        return chunks