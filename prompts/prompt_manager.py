from typing import Dict, Any, Optional

class PromptRepositoryManager:
    def __init__(self):
        # In-memory prompt version registry
        self._templates: Dict[str, str] = {
            "credit_analysis_v1.0.0": (
                "System: You are an expert Commercial Credit Risk Analyst.\n"
                "Evaluate the loan request using strictly the provided context.\n"
                "As-Of Date: {as_of_date}\n"
                "Tenant ID: {tenant_id}\n\n"
                "Context:\n{retrieved_context}\n\n"
                "Query: {user_query}\n"
                "Provide a grounded assessment with explicit document citations."
            ),
            "credit_analysis_v1.1.0": (
                "System: You are a Lead Credit Officer approving enterprise facilities.\n"
                "Enforce strict policy compliance. Do not extrapolate beyond provided facts.\n"
                "As-Of Date: {as_of_date}\n"
                "Tenant ID: {tenant_id}\n\n"
                "Validated Context:\n{retrieved_context}\n\n"
                "Query: {user_query}\n"
                "Format: 1. Decision Summary, 2. Policy Citations, 3. Risk Factors."
            )
        }
        self.default_version = "credit_analysis_v1.0.0"

    def get_prompt_template(self, version: Optional[str] = None) -> str:
        """Retrieves a specific prompt version or falls back to default."""
        target_version = version or self.default_version
        return self._templates.get(target_version, self._templates[self.default_version])

    def render_prompt(
        self,
        user_query: str,
        retrieved_context: str,
        tenant_id: str,
        as_of_date: str,
        version: Optional[str] = None
    ) -> str:
        """Renders the final populated prompt with variable substitution."""
        template = self.get_prompt_template(version)
        return template.format(
            user_query=user_query,
            retrieved_context=retrieved_context,
            tenant_id=tenant_id,
            as_of_date=as_of_date
        )