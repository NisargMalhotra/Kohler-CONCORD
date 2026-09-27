import json
import logging
import jsonschema
from src.config import VerifiedAnswer, FormatSpec, FormattedOutput

logger = logging.getLogger(__name__)

def format_json(answer: VerifiedAnswer, spec: FormatSpec) -> FormattedOutput:
    """Formats answer as JSON, validates against schema if provided."""
    data = {
        "query_response": answer.answer,
        "citations": [
            {
                "clause_id": c.clause_id,
                "source_file": c.source_file,
                "relevant_text": c.relevant_text,
                "domain": c.domain
            } for c in answer.citations
        ],
        "confidence": answer.confidence,
        "conflicts": [
            {
                "clause_a": getattr(c, 'clause_a_id', ''),
                "clause_b": getattr(c, 'clause_b_id', ''),
                "description": getattr(c, 'description', '')
            } for c in answer.conflicts
        ]
    }
    
    validation_passed = True
    validation_errors = []
    
    if spec.schema:
        try:
            jsonschema.validate(instance=data, schema=spec.schema)
        except jsonschema.ValidationError as e:
            validation_passed = False
            validation_errors.append(str(e))
            logger.warning(f"JSON validation failed: {e}")
            
    try:
        content_str = json.dumps(data, indent=2)
    except TypeError as e:
        validation_passed = False
        validation_errors.append(f"Serialization error: {e}")
        content_str = "{}"
        
    return FormattedOutput(
        content=content_str,
        format_type="json",
        validation_passed=validation_passed,
        validation_errors=validation_errors
    )
