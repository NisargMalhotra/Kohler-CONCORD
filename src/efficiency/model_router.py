import logging
from src.config import settings
from src.llm import efficiency_stats

logger = logging.getLogger(__name__)

class ModelRouter:
    """Routes queries to appropriate model sizes to save energy/tokens."""

    def select_model(self, query: str, complexity: str) -> str:
        """
        Selects the best LLM model based on complexity.
        """
        if complexity.lower() == "simple":
            tokens_saved = self.estimate_tokens_saved(query)
            efficiency_stats.tokens_saved_by_routing += tokens_saved
            return settings.LLM_MODEL_SMALL
        return settings.LLM_MODEL

    def estimate_tokens_saved(self, query: str) -> int:
        """Estimates tokens saved by routing to a smaller model."""
        estimated_input = len(query.split()) * 1.5
        return int(estimated_input + 200)
