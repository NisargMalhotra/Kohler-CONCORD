import logging
from src.config import VerifiedAnswer, FormatSpec, FormattedOutput, settings
from src.llm import chat

logger = logging.getLogger(__name__)

def format_email(answer: VerifiedAnswer, spec: FormatSpec) -> FormattedOutput:
    """Formats answer as a draft email with the requested tone."""
    tone = spec.email_tone or "professional"
    recipient = spec.email_to or "[Recipient]"
    subject = spec.email_subject or "Policy Answer from KOHLER CONCORD"
    
    system_prompt = (
        f"You are an email formatting agent. Draft an email to {recipient}. "
        f"The tone should be {tone}. "
        f"Subject: {subject}\n"
        "Draft the body of the email summarizing the following answer and citations. "
        "Keep the formatting as a clean text email."
    )
    
    citations_text = "\n".join([f"- {c.clause_id}: {c.relevant_text}" for c in answer.citations])
    content = f"Answer:\n{answer.answer}\n\nCitations:\n{citations_text}"
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": content}
    ]
    
    draft_body = chat(messages, model=settings.LLM_MODEL)
    
    email_text = f"To: {recipient}\nSubject: {subject}\n\n{draft_body}"
    
    validation_passed = True
    validation_errors = []
    
    if not recipient or not subject or not draft_body:
        validation_passed = False
        validation_errors.append("Missing essential email fields.")
        
    return FormattedOutput(
        content=email_text,
        format_type="email",
        validation_passed=validation_passed,
        validation_errors=validation_errors
    )
