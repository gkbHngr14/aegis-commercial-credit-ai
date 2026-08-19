from typing import List, Dict, Any

class ContextAssembler:
    def __init__(self, max_context_chars: int = 4000):
        self.max_context_chars = max_context_chars

    def assemble_context(self, search_results: List[Dict[str, Any]]) -> str:
        """
        Formats hybrid search results into structured, cited context blocks.
        Enforces maximum character bounds to protect LLM context windows.
        """
        if not search_results:
            return "No relevant context retrieved."

        formatted_blocks = []
        total_length = 0

        for idx, result in enumerate(search_results, start=1):
            chunk_id = result.get("chunk_id", "UNK")
            doc_id = result.get("metadata", {}).get("document_id", "DOC")
            content = result.get("content", "").strip()
            is_amended = result.get("is_amended", False)

            status_tag = "[AMENDED]" if is_amended else "[ORIGINAL]"
            block = f"Source [{doc_id}::{chunk_id}] {status_tag}:\n{content}"

            # Check character budget before adding block
            if total_length + len(block) > self.max_context_chars:
                break

            formatted_blocks.append(block)
            total_length += len(block)

        return "\n\n---\n\n".join(formatted_blocks)