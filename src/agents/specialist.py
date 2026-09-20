import logging
from typing import Dict, List, Any

from src.config import Document
from src.llm import chat_json

logger = logging.getLogger(__name__)

_KOHLER_VALUES_ADDENDUM = (
    "\n\nKOHLER SUSTAINABILITY GUIDANCE (Customer Support domain only):\n"
    "When answering questions about products, installations, or fixtures, naturally highlight "
    "water-saving and sustainability features IF they are relevant to the customer's specific question "
    "and IF the information exists in the provided documents. For example:\n"
    "- WaterSense® certified products and what that means for water savings\n"
    "- Low-flow aerators, gallons-per-minute/flush ratings\n"
    "- Touchless/sensor technology that prevents water waste\n"
    "- Leak-prevention and smart water monitoring features\n"
    "Do NOT force sustainability mentions into unrelated topics (warranty claims, returns, account issues). "
    "Do NOT invent certifications or features not present in the documents. "
    "Keep the tone helpful and informative, not promotional."
)


class DomainSpecialist:
    """Generates domain-specific answers grounded in retrieved documents."""

    def answer(
        self,
        query: str,
        documents: List[Document],
        domain: str,
        history_block: str = "",
    ) -> Dict[str, Any]:
        """
        Answers a query using ONLY provided documents.

        Args:
            query: User's question.
            documents: List of retrieved documents.
            domain: The domain this specialist operates in.
            history_block: Condensed recent conversation for multi-turn context.

        Returns:
            Dict with 'answer', 'cited_clauses', and 'key_points'.
        """
        if not documents:
            return {
                "answer": f"I could not find relevant information in the {domain} domain.",
                "cited_clauses": [],
                "key_points": []
            }

        doc_texts = []
        for doc in documents:
            cid = doc.metadata.get('clause_id', 'unknown')
            doc_texts.append(f"Clause {cid}:\n{doc.content}")
        docs_str = "\n\n".join(doc_texts)

        system_prompt = (
            f"You are a domain specialist for {domain}. Answer the user query using ONLY the provided documents. "
            "Cite specific clause IDs for every claim. If information is insufficient, say so explicitly. "
            "Be precise and professional. Return a JSON with exactly these keys: "
            "'answer' (str), 'cited_clauses' (List[str]), and 'key_points' (List[str])."
        )

        # Add Kohler sustainability guidance for customer_support domain
        if domain == "customer_support":
            system_prompt += _KOHLER_VALUES_ADDENDUM

        # Add conversation history for multi-turn context
        if history_block:
            system_prompt += (
                "\n\nCONVERSATION HISTORY (for context on follow-up questions):\n"
                f"{history_block}\n"
                "Use this history to understand references like 'that', 'it', 'the previous answer', etc. "
                "Still ground all claims in the provided documents."
            )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Documents:\n{docs_str}\n\nQuery: {query}"}
        ]

        result = chat_json(messages)
        if "error" in result:
            logger.error(f"Specialist error for {domain}: {result['error']}")
            return {
                "answer": "An error occurred while generating the answer.",
                "cited_clauses": [],
                "key_points": []
            }

        return {
            "answer": result.get("answer", "No answer could be generated."),
            "cited_clauses": result.get("cited_clauses", []),
            "key_points": result.get("key_points", [])
        }
