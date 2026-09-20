import logging
from src.config import VerifiedAnswer, FormatSpec, FormattedOutput
from src.output import format_json, format_xml, format_excel, format_email

logger = logging.getLogger(__name__)

class Formatter:
    """Formats the VerifiedAnswer into the requested output contract."""

    def format_output(self, answer: VerifiedAnswer, format_spec: FormatSpec) -> FormattedOutput:
        """
        Dispatches to the appropriate output handler based on format_type.

        Args:
            answer: The verified answer.
            format_spec: The requested format specification.

        Returns:
            A FormattedOutput object.
        """
        fmt = format_spec.format_type.lower()
        if fmt == "json":
            return format_json(answer, format_spec)
        elif fmt == "xml":
            return format_xml(answer, format_spec)
        elif fmt == "excel":
            return format_excel(answer, format_spec)
        elif fmt == "email":
            return format_email(answer, format_spec)
        
        # Default plain text
        citations_text = "\n\nCitations:\n"
        if answer.citations:
            citations_text += "\n".join(
                [f"- {c.clause_id} ({c.source_file}): {c.relevant_text}" for c in answer.citations]
            )
        else:
            citations_text += "None"
            
        return FormattedOutput(
            content=answer.answer + citations_text,
            format_type="plain",
            validation_passed=True
        )
