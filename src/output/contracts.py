import logging
from src.config import FormatSpec, settings
from src.llm import chat_json

logger = logging.getLogger(__name__)

class OutputContractParser:
    """Parses natural language formatting instructions into a FormatSpec."""

    def parse(self, instruction: str) -> FormatSpec:
        """Parse natural language instruction using LLM."""
        if instruction is None or not instruction.strip():
            return FormatSpec(format_type="plain")
            
        system_prompt = (
            "You are an output contract parser. Analyze the user's formatting instruction and return JSON with:\n"
            "'format_type' (str): One of ['json', 'xml', 'excel', 'email', 'plain'].\n"
            "'schema' (dict or null): If json, any requested schema structure.\n"
            "'instructions' (str or null): Additional details (like column names for excel).\n"
            "'email_to' (str or null): If email, the requested recipient.\n"
            "'email_subject' (str or null): If email, the requested subject.\n"
            "'email_tone' (str or null): If email, the requested tone (e.g., 'formal', 'casual').\n"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": instruction}
        ]
        
        result = chat_json(messages, model=settings.LLM_MODEL_SMALL)
        if "error" in result:
            logger.error(f"Format parser error: {result['error']}")
            return FormatSpec(format_type="plain")
            
        return FormatSpec(
            format_type=result.get("format_type", "plain"),
            schema=result.get("schema"),
            instructions=result.get("instructions"),
            email_to=result.get("email_to"),
            email_subject=result.get("email_subject"),
            email_tone=result.get("email_tone")
        )
