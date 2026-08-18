import pytest
from ingestion.chunker import SectionAwareChunker

@pytest.fixture
def sample_document_elements():
    return [
        {
            "element_type": "NarrativeText",
            "text": "Section 14.2: European Subsidiary Liability. The parent company provides secondary recourse.",
            "metadata": {"document_id": "DOC-882", "section_id": "SEC-14.2", "effective_date": "2026-01-01", "tenant_id": "TENANT-EMEA"}
        },
        {
            "element_type": "Table",
            "text": "<table><tr><td>Facility</td><td>Limit</td></tr><tr><td>Draw</td><td>$15M</td></tr></table>",
            "metadata": {"document_id": "DOC-882", "section_id": "SEC-14.2-TAB", "effective_date": "2026-01-01", "tenant_id": "TENANT-EMEA"}
        }
    ]

def test_metadata_lineage(sample_document_elements):
    chunker = SectionAwareChunker()
    chunks = chunker.chunk_document(sample_document_elements)
    
    required_keys = {"tenant_id", "document_id", "section_id", "effective_date"}
    
    for chunk in chunks:
        assert chunk is not None
        assert required_keys.issubset(chunk.metadata.keys()), f"Chunk {chunk.chunk_id} missing mandatory metadata!"

def test_no_mid_sentence_splits(sample_document_elements):
    chunker = SectionAwareChunker()
    chunks = chunker.chunk_document(sample_document_elements)
    
    for chunk in chunks:
        if chunk.chunk_type == "NARRATIVE":
            assert chunk.content.endswith(('.', ';', ':')), f"Chunk {chunk.chunk_id} split mid-sentence!"

def test_table_integrity(sample_document_elements):
    chunker = SectionAwareChunker()
    chunks = chunker.chunk_document(sample_document_elements)
    
    table_chunks = [c for c in chunks if c.chunk_type == "TABLE"]
    for t_chunk in table_chunks:
        assert t_chunk.content.startswith("<table>") and t_chunk.content.endswith("</table>")