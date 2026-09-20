import re
import logging
from typing import Tuple
from src.config import Persona

logger = logging.getLogger(__name__)

class ResponseGuard:
    """Guards responses to ensure sensitive info isn't leaked based on persona."""

    def check_response(self, response: str, persona: Persona) -> Tuple[bool, str]:
        """
        Validates and cleans a response.
        Returns (is_safe, cleaned_response)
        """
        is_safe = True
        cleaned = response
        
        if persona == Persona.CUSTOMER:
            if re.search(r"\$\d{1,3}(,\d{3})+(\.\d{2})?", response) or re.search(r"\b\d{3}-\d{2}-\d{4}\b", response):
                is_safe = False
                cleaned = self._redact_sensitive(cleaned, persona)
                
        return is_safe, cleaned

    def _redact_sensitive(self, text: str, persona: Persona) -> str:
        if persona == Persona.CUSTOMER:
            text = re.sub(r"\$\d{1,3}(,\d{3})+(\.\d{2})?", "[REDACTED FINANCIAL INFO]", text)
            text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED SSN]", text)
        return text
