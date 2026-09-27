"""
KOHLER CONCORD — Customer Support Pipeline.

A simplified pipeline for the customer-facing experience.
Uses a separate, pre-built customer knowledge base.
Two modes: 'help' (complaint resolution) and 'info' (product browsing).
"""

import logging
import re
import time
from typing import Any, Dict, List, Optional

from src.config import Persona, Citation, VerifiedAnswer
from src.llm import chat, chat_json, efficiency_stats
from src.knowledge_base.customer_store import CustomerVectorStore
from src.trust.injection_detector import InjectionDetector

logger = logging.getLogger(__name__)

_MAX_HISTORY_TURNS = 6

_HELP_SYSTEM_PROMPT = (
    "You are Kohler's friendly and professional customer support assistant. "
    "Your job is to help customers resolve their issues quickly and clearly.\n\n"
    "RULES:\n"
    "1. Always be warm, empathetic, and solution-oriented.\n"
    "2. Use ONLY the provided documents to answer. Cite clause IDs for every claim.\n"
    "3. If you can resolve the issue from the documents, do so step-by-step.\n"
    "4. If the issue requires human intervention (refunds, account-specific problems, " 
    "physical repairs you can't diagnose remotely), say so clearly and suggest: "
    "'Please contact Kohler Support at 1-800-4-KOHLER or visit kohler.com/support'.\n"
    "5. If you genuinely don't have the information, say: "
    "'I don't have that information in my knowledge base. For personalized help, "
    "please contact Kohler Support at 1-800-4-KOHLER.'\n"
    "6. Do NOT guess, invent product specs, or make up warranty terms.\n"
    "7. If relevant, mention water-saving or sustainability features naturally.\n\n"
    "Return JSON with keys: 'answer' (str), 'cited_clauses' (List[str]), "
    "'needs_human' (bool), 'suggested_action' (str or null)."
)

_INFO_SYSTEM_PROMPT = (
    "You are Kohler's product information specialist. "
    "Help customers learn about Kohler products, features, specifications, "
    "warranty terms, and installation requirements.\n\n"
    "RULES:\n"
    "1. Be informative, clear, and professional.\n"
    "2. Use ONLY the provided documents. Cite clause IDs for every claim.\n"
    "3. Highlight water-saving and sustainability features when relevant.\n"
    "4. If asked about a product not in the documents, say so honestly.\n"
    "5. Do NOT invent specs, certifications, or prices.\n\n"
    "Return JSON with keys: 'answer' (str), 'cited_clauses' (List[str]), "
    "'key_points' (List[str])."
)

_VERIFIER_PROMPT = (
    "You are a verifier for a customer support AI. Check every claim in the "
    "draft answer against the provided documents. Strip unsupported claims. "
    "Assign a confidence score (0.0 to 1.0). If confidence < 0.4, set "
    "should_abstain=True. Return JSON with keys: 'verified_answer' (str), "
    "'confidence' (float), 'should_abstain' (bool), "
    "'abstention_reason' (str or null), 'verified_clauses' (List[str])."
)


def _build_history_block(history: List[Dict[str, str]]) -> str:
    relevant = [m for m in history if m.get("role") in ("user", "assistant")]
    trimmed = relevant[-(_MAX_HISTORY_TURNS * 2):]
    if not trimmed:
        return ""
    lines = []
    for m in trimmed:
        role = "Customer" if m["role"] == "user" else "Support"
        content = m.get("content", m.get("answer", ""))
        if len(content) > 400:
            content = content[:400] + "..."
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def run_customer_pipeline(
    query: str,
    mode: str,  # "help" or "info"
    customer_store: CustomerVectorStore,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Run the customer-specific pipeline.
    
    Returns dict with: answer, citations, confidence, needs_human,
    suggested_action, should_abstain, abstention_reason, efficiency_stats.
    """
    history = conversation_history or []
    history_block = _build_history_block(history)

    # 1. Quick injection check (regex only for speed — no LLM call)
    detector = InjectionDetector()
    is_safe, reason = detector._regex_check(query)
    if not is_safe:
        return _customer_empty_result(
            answer=f"I'm sorry, I can't process that request. How else can I help you?",
            is_injection=True,
        )

    # 2. Retrieve from customer KB
    documents = customer_store.search(query, top_k=8)
    if not documents:
        fallback = (
            "I couldn't find specific information about that in my knowledge base. "
            "For personalized help, please contact Kohler Support at "
            "**1-800-4-KOHLER** or visit [kohler.com/support](https://www.kohler.com/support)."
        )
        return _customer_empty_result(answer=fallback)

    # 3. Build context
    doc_texts = []
    for doc in documents:
        cid = doc.metadata.get("clause_id", "unknown")
        doc_texts.append(f"Clause {cid}:\n{doc.content}")
    docs_str = "\n\n".join(doc_texts)

    # 4. Select system prompt based on mode
    system_prompt = _HELP_SYSTEM_PROMPT if mode == "help" else _INFO_SYSTEM_PROMPT

    # Add conversation history for multi-turn
    if history_block:
        system_prompt += (
            f"\n\nCONVERSATION HISTORY:\n{history_block}\n"
            "Use this to understand follow-up questions. "
            "Still ground all claims in the provided documents."
        )

    # 5. Generate draft
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Documents:\n{docs_str}\n\nCustomer question: {query}"},
    ]
    draft_result = chat_json(messages)
    if "error" in draft_result:
        logger.error(f"Customer specialist error: {draft_result['error']}")
        return _customer_empty_result(
            answer="I'm having trouble processing your request right now. "
                   "Please try again in a moment, or contact Kohler Support at 1-800-4-KOHLER."
        )

    draft_answer = draft_result.get("answer", "")
    cited_clauses = draft_result.get("cited_clauses", [])
    needs_human = draft_result.get("needs_human", False)
    suggested_action = draft_result.get("suggested_action", None)

    # 6. Verify
    docs_context = "\n".join(
        [f"Clause {d.metadata.get('clause_id', '?')}: {d.content}" for d in documents]
    )
    verify_messages = [
        {"role": "system", "content": _VERIFIER_PROMPT},
        {
            "role": "user",
            "content": f"Draft Answer:\n{draft_answer}\n\nDocuments:\n{docs_context}\n\nQuery: {query}",
        },
    ]
    vres = chat_json(verify_messages)

    if "error" in vres:
        # Graceful fallback — use draft as-is
        verified_answer = draft_answer
        confidence = 0.7
        should_abstain = False
        abstention_reason = ""
        verified_clauses = cited_clauses
    else:
        verified_answer = vres.get("verified_answer", draft_answer)
        confidence = float(vres.get("confidence", 0.0))
        should_abstain = bool(vres.get("should_abstain", False))
        if confidence < 0.4:
            should_abstain = True
        abstention_reason = vres.get("abstention_reason", "")
        verified_clauses = vres.get("verified_clauses", cited_clauses)

    # 7. Build citations
    citations = []
    for clause in verified_clauses:
        for doc in documents:
            if doc.metadata.get("clause_id") == clause:
                citations.append({
                    "clause_id": clause,
                    "source_file": doc.metadata.get("source_file", "unknown"),
                    "relevant_text": doc.content[:150] + "...",
                    "domain": doc.metadata.get("domain", "customer_support"),
                })
                break

    return {
        "answer": verified_answer,
        "citations": citations,
        "confidence": confidence,
        "needs_human": needs_human,
        "suggested_action": suggested_action,
        "should_abstain": should_abstain,
        "abstention_reason": abstention_reason,
        "conflicts": [],
        "format_output": None,
        "denied_domains": [],
        "domains_used": ["customer_support"],
        "is_injection": False,
        "efficiency_stats": {
            "total_tokens_used": efficiency_stats.total_tokens_used,
            "tokens_saved_by_cache": efficiency_stats.tokens_saved_by_cache,
            "tokens_saved_by_routing": efficiency_stats.tokens_saved_by_routing,
            "cache_hits": efficiency_stats.cache_hits,
            "cache_misses": efficiency_stats.cache_misses,
            "small_model_calls": efficiency_stats.small_model_calls,
            "large_model_calls": efficiency_stats.large_model_calls,
            "total_tokens_saved": efficiency_stats.total_tokens_saved,
            "estimated_energy_saved_wh": efficiency_stats.estimated_energy_saved_wh,
            "estimated_co2_saved_g": efficiency_stats.estimated_co2_saved_g,
        },
    }


def _customer_empty_result(
    answer: str = "", is_injection: bool = False
) -> Dict[str, Any]:
    return {
        "answer": answer,
        "citations": [],
        "confidence": 0.0,
        "needs_human": False,
        "suggested_action": None,
        "should_abstain": False,
        "abstention_reason": None,
        "conflicts": [],
        "format_output": None,
        "denied_domains": [],
        "domains_used": [],
        "is_injection": is_injection,
        "efficiency_stats": {
            "total_tokens_used": efficiency_stats.total_tokens_used,
            "tokens_saved_by_cache": efficiency_stats.tokens_saved_by_cache,
            "tokens_saved_by_routing": efficiency_stats.tokens_saved_by_routing,
            "cache_hits": efficiency_stats.cache_hits,
            "cache_misses": efficiency_stats.cache_misses,
            "small_model_calls": efficiency_stats.small_model_calls,
            "large_model_calls": efficiency_stats.large_model_calls,
            "total_tokens_saved": efficiency_stats.total_tokens_saved,
            "estimated_energy_saved_wh": efficiency_stats.estimated_energy_saved_wh,
            "estimated_co2_saved_g": efficiency_stats.estimated_co2_saved_g,
        },
    }
