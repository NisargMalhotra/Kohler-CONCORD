import logging
from xml.etree import ElementTree as ET
from src.config import VerifiedAnswer, FormatSpec, FormattedOutput

logger = logging.getLogger(__name__)

def format_xml(answer: VerifiedAnswer, spec: FormatSpec) -> FormattedOutput:
    """Formats the answer as XML."""
    root = ET.Element("response")
    
    ans_elem = ET.SubElement(root, "answer")
    ans_elem.text = str(answer.answer)
    
    citations_elem = ET.SubElement(root, "citations")
    for c in answer.citations:
        c_elem = ET.SubElement(citations_elem, "citation")
        
        ET.SubElement(c_elem, "clause_id").text = str(c.clause_id)
        ET.SubElement(c_elem, "source_file").text = str(c.source_file)
        ET.SubElement(c_elem, "relevant_text").text = str(c.relevant_text)
        ET.SubElement(c_elem, "domain").text = str(c.domain)
        
    conf_elem = ET.SubElement(root, "confidence")
    conf_elem.text = str(answer.confidence)
    
    validation_passed = True
    validation_errors = []
    content_str = ""
    
    try:
        content_str = ET.tostring(root, encoding="unicode")
        # Validate well-formedness
        ET.fromstring(content_str)
    except ET.ParseError as e:
        validation_passed = False
        validation_errors.append(f"XML parsing failed: {e}")
    except Exception as e:
        validation_passed = False
        validation_errors.append(f"XML generation failed: {e}")
        
    return FormattedOutput(
        content=content_str,
        format_type="xml",
        validation_passed=validation_passed,
        validation_errors=validation_errors
    )
