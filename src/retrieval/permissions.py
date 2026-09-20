import logging
from typing import List, Dict, Any

from src.config import Document, Persona, PERSONA_DOMAIN_ACCESS, PERSONA_ACCESS_LEVELS

logger = logging.getLogger(__name__)

class PermissionFilter:
    def filter_for_persona(self, documents: List[Document], persona: Persona) -> List[Document]:
        allowed_domains = [d.value for d in PERSONA_DOMAIN_ACCESS.get(persona, [])]
        allowed_levels = PERSONA_ACCESS_LEVELS.get(persona, [])
        
        filtered_docs = []
        for doc in documents:
            doc_domain = doc.metadata.get("domain")
            doc_level = doc.metadata.get("access_level")
            
            if doc_domain in allowed_domains and doc_level in allowed_levels:
                filtered_docs.append(doc)
                
        return filtered_docs

    def build_chroma_filter(self, persona: Persona) -> dict:
        allowed_domains = [d.value for d in PERSONA_DOMAIN_ACCESS.get(persona, [])]
        allowed_levels = PERSONA_ACCESS_LEVELS.get(persona, [])
        
        if not allowed_domains or not allowed_levels:
            # If no permissions, return a filter that matches nothing
            return {"domain": {"$in": ["__NONE__"]}}
            
        return {
            "$and": [
                {"domain": {"$in": allowed_domains}},
                {"access_level": {"$in": allowed_levels}}
            ]
        }

    def explain_denial(self, persona: Persona, domain: str) -> str:
        allowed_domains = [d.value for d in PERSONA_DOMAIN_ACCESS.get(persona, [])]
        if domain not in allowed_domains:
            persona_name = persona.value.replace('_', ' ').title()
            return f"As a {persona_name}, you do not have permission to access documents in the {domain.upper()} domain."
        return ""
