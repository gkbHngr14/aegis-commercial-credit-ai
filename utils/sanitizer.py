import re
from typing import Dict, Any

class ValidationException(Exception):
    pass

class PayloadSanitizer:
    @staticmethod
    def clean_and_sanitize(text: str) -> str:
        if not text:
            raise ValidationException("Text payload cannot be empty.")
        # Strip null bytes and non-printable control chars
        cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        return cleaned.strip()

    @staticmethod
    def validate_metadata(tenant_id: str, effective_date: str) -> None:
        if not tenant_id or not tenant_id.startswith("TENANT-"):
            raise ValidationException(f"Invalid tenant_id format: {tenant_id}")
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', effective_date):
            raise ValidationException(f"Invalid effective_date ISO format: {effective_date}")