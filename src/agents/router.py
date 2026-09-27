import logging
import re
from typing import Dict, List

from src.config import settings
from src.llm import chat_json

logger = logging.getLogger(__name__)

# Keyword patterns for rule-based routing fallback
_DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "hr": [
        "employee", "leave", "vacation", "salary", "hiring", "onboarding",
        "termination", "benefits", "disciplin", "handbook", "performance",
        "remote work", "work from home", "contractor", "payroll", "pto",
        "address", "hr ", "human resource",
    ],
    "finance": [
        "expense", "budget", "procurement", "invoice", "audit", "revenue",
        "financial", "tax", "cost", "reimburs", "fiscal", "accounting",
        "purchase order", "payment",
    ],
    "customer_support": [
        "faucet", "toilet", "shower", "warranty", "return", "product",
        "install", "repair", "troubleshoot", "kohler", "generator",
        "smart home", "konnect", "water", "plumbing", "fixture",
        "customer", "support", "defective",
    ],
    "privacy": [
        "privacy", "data retention", "gdpr", "ccpa", "personal data",
        "consent", "data protection", "data handling", "pii",
    ],
    "legal": [
        "legal", "compliance", "regulation", "contract", "liability",
        "litigation", "intellectual property", "patent", "license",
        "environmental compliance",
    ],
}


class Router:
    """Classifies queries into relevant domains and determines complexity."""

    def route(self, query: str) -> Dict[str, str | list[str]]:
        """
        Routes the query to appropriate domains and complexity.

        Args:
            query: The user query string.

        Returns:
            Dict containing 'domains', 'complexity', and 'reasoning'.
        """
        system_prompt = (
            "You are a routing agent for KOHLER CONCORD. "
            "Analyze the query and assign 1 to 3 most relevant domains from: "
            "[hr, finance, customer_support, privacy, legal]. "
            "Also classify complexity as 'simple', 'moderate', or 'complex'. "
            "Return JSON format with keys: domains (List[str]), complexity (str), and reasoning (str)."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]
        
        result = chat_json(messages, model=settings.LLM_MODEL_SMALL)
        if "error" in result:
            logger.warning(f"LLM routing failed, using keyword fallback: {result['error']}")
            return self._keyword_route(query)
            
        return {
            "domains": result.get("domains", ["hr"]),
            "complexity": result.get("complexity", "moderate"),
            "reasoning": result.get("reasoning", "")
        }

    def _keyword_route(self, query: str) -> Dict[str, str | list[str]]:
        """Rule-based routing using keyword matching (no LLM call)."""
        query_lower = query.lower()
        scores: Dict[str, int] = {}

        for domain, keywords in _DOMAIN_KEYWORDS.items():
            count = sum(1 for kw in keywords if kw in query_lower)
            if count > 0:
                scores[domain] = count

        if not scores:
            # Default fallback
            return {
                "domains": ["hr", "customer_support"],
                "complexity": "moderate",
                "reasoning": "Keyword fallback: no strong domain match, using defaults.",
            }

        # Sort by match count, take top 2
        sorted_domains = sorted(scores, key=scores.get, reverse=True)[:2]
        complexity = "simple" if len(sorted_domains) == 1 else "moderate"

        return {
            "domains": sorted_domains,
            "complexity": complexity,
            "reasoning": f"Keyword fallback: matched {sorted_domains}.",
        }

