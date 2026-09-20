import logging
from typing import Dict

from src.config import settings
from src.llm import chat_json

logger = logging.getLogger(__name__)

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
            logger.error(f"Routing failed: {result['error']}")
            return {"domains": ["hr"], "complexity": "moderate", "reasoning": "Fallback routing due to error."}
            
        return {
            "domains": result.get("domains", ["hr"]),
            "complexity": result.get("complexity", "moderate"),
            "reasoning": result.get("reasoning", "")
        }
