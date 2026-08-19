import pytest
from prompts.prompt_manager import PromptRepositoryManager
from eval_harness.context_assembler import ContextAssembler

def test_prompt_repository_rendering_and_fallback():
    manager = PromptRepositoryManager()

    # Test Version 1.0.0 rendering
    prompt_v1 = manager.render_prompt(
        user_query="Check drawdown limits",
        retrieved_context="[DOC-1::SEC-1.1]: Limit $10M",
        tenant_id="TENANT-EMEA",
        as_of_date="2026-08-01",
        version="credit_analysis_v1.0.0"
    )
    assert "TENANT-EMEA" in prompt_v1
    assert "Limit $10M" in prompt_v1

    # Test missing version fallback
    prompt_fallback = manager.render_prompt(
        user_query="Check drawdown limits",
        retrieved_context="[DOC-1::SEC-1.1]: Limit $10M",
        tenant_id="TENANT-EMEA",
        as_of_date="2026-08-01",
        version="credit_analysis_v9.9.9" # Non-existent version
    )
    assert "You are an expert Commercial Credit Risk Analyst" in prompt_fallback

def test_context_assembler_citation_formatting():
    assembler = ContextAssembler(max_context_chars=1000)

    mock_results = [
        {
            "chunk_id": "SEC-14.2",
            "content": "European Subsidiary Liability active.",
            "is_amended": False,
            "metadata": {"document_id": "DOC-882"}
        },
        {
            "chunk_id": "SEC-14.2-AMD",
            "content": "European Subsidiary Liability revoked.",
            "is_amended": True,
            "metadata": {"document_id": "DOC-882"}
        }
    ]

    context = assembler.assemble_context(mock_results)

    assert "Source [DOC-882::SEC-14.2] [ORIGINAL]:" in context
    assert "Source [DOC-882::SEC-14.2-AMD] [AMENDED]:" in context
    assert "European Subsidiary Liability revoked." in context