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
        tools_prompt: str = "",
    ) -> Dict[str, Any]:
        """
        Answers a query using ONLY provided documents, or invokes a tool.

        Args:
            query: User's question.
            documents: List of retrieved documents.
            domain: The domain this specialist operates in.
            history_block: Condensed recent conversation for multi-turn context.
            tools_prompt: Optional tool descriptions to append to system prompt.

        Returns:
            Dict with 'answer', 'cited_clauses', 'key_points', and
            optionally 'tool_call'.
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

        # Add tool descriptions if available for this role
        if tools_prompt:
            system_prompt += tools_prompt

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
            logger.warning(f"Specialist LLM unavailable for {domain}: {result['error']}")
            # Fallback: build an answer directly from the top retrieved documents
            # so the user still gets useful information even when the API is down
            return self._build_fallback_answer(query, documents, domain)

        # Check if the LLM decided to call a tool instead of answering
        if "tool_call" in result:
            return {
                "tool_call": result["tool_call"],
                "answer": None,
                "cited_clauses": [],
                "key_points": [],
            }

        return {
            "answer": result.get("answer", "No answer could be generated."),
            "cited_clauses": result.get("cited_clauses", []),
            "key_points": result.get("key_points", [])
        }

    def _build_fallback_answer(
        self, query: str, documents: List[Document], domain: str
    ) -> Dict[str, Any]:
        """Build an answer directly from retrieved document chunks (no LLM).

        Used when the LLM API is unavailable (rate-limited). Returns the
        top-3 most relevant document sections verbatim with clause citations.
        """
        if not documents:
            return {
                "answer": (
                    "The AI assistant is temporarily unavailable due to API limits. "
                    "Please try again in a few moments."
                ),
                "cited_clauses": [],
                "key_points": [],
            }

        # Take the top 3 documents (already ranked by relevance from retrieval)
        top_docs = documents[:3]
        cited_clauses = []
        sections = []

        for doc in top_docs:
            cid = doc.metadata.get("clause_id", "unknown")
            title = doc.metadata.get("title", "")
            cited_clauses.append(cid)
            header = f"**{title}** (Clause {cid}):" if title else f"**Clause {cid}:**"
            # Trim to keep the answer reasonable
            content = doc.content[:500] + ("…" if len(doc.content) > 500 else "")
            sections.append(f"{header}\n{content}")

        answer = (
            f"*Based on {domain} documents (AI summarisation temporarily unavailable due to API limits):*\n\n"
            + "\n\n".join(sections)
            + "\n\n---\n*For a fully synthesised answer, please try again in a few moments.*"
        )

        return {
            "answer": answer,
            "cited_clauses": cited_clauses,
            "key_points": [f"Source: {domain} knowledge base"],
        }
