"""
KOHLER CONCORD — Agent Pipeline Orchestrator.

Orchestrates the full multi-agent pipeline:
  Injection Check → Query Rewriter (if follow-up) → Router →
  Permission-Aware Retrieval → Domain Specialist(s) →
  Verifier/Critic → Conflict Detector → Formatter → Validated Output
"""

import logging
import re
from typing import Any, Dict, List, Optional

from src.config import Persona, FormatSpec, settings
from src.agents.router import Router
from src.agents.specialist import DomainSpecialist
from src.agents.verifier import Verifier
from src.agents.formatter import Formatter
from src.trust.injection_detector import InjectionDetector
from src.trust.guard import ResponseGuard
from src.efficiency.model_router import ModelRouter
from src.efficiency.cache import ResponseCache
from src.output.contracts import OutputContractParser
from src.retrieval.permissions import PermissionFilter
from src.retrieval.hybrid import HybridRetriever
from src.retrieval.conflict_detector import ConflictDetector
from src.llm import chat, efficiency_stats

logger = logging.getLogger(__name__)

# Module-level singletons (re-created per import, but cheap)
_cache = ResponseCache()

# ── Multi-turn helpers ────────────────────────────────────────────────────────

_MAX_HISTORY_TURNS = 4  # last N user/assistant pairs
_REFORMULATION_RE = re.compile(
    r"(?:"
    r"\b(?:that|this|it|those|these|previous|above|earlier|last answer|same|again"
    r"|more detail|summarize|summarise|put that|format that|also|too|instead"
    r"|tell me more|can you also|what else|anything else)\b"
    r"|^what about\b|^how about\b|^and (?:for|what|how|if)\b|^what if\b"
    r")",
    re.IGNORECASE,
)


def _build_history_block(conversation_history: List[Dict[str, str]]) -> str:
    """Condense the last N exchanges into a compact text block for prompts."""
    if not conversation_history:
        return ""
    # Keep only user/assistant pairs, skip system messages
    relevant = [
        m for m in conversation_history
        if m.get("role") in ("user", "assistant")
    ]
    # Take last N*2 messages (N turns = N user + N assistant)
    trimmed = relevant[-(_MAX_HISTORY_TURNS * 2):]
    if not trimmed:
        return ""
    lines = []
    for m in trimmed:
        role = "User" if m["role"] == "user" else "Assistant"
        content = m.get("content", m.get("answer", ""))
        # Truncate long responses to save tokens
        if len(content) > 400:
            content = content[:400] + "…"
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _is_follow_up(query: str) -> bool:
    """Heuristic: does the query reference prior context?"""
    return bool(_REFORMULATION_RE.search(query))


def _is_answer_only_followup(query: str) -> bool:
    """True if the user is only asking about the *previous answer* (no new retrieval needed)."""
    answer_only = re.compile(
        r"^(summarize|summarise|put that|format that|repeat that|say that again|shorter|in a table|as json|as xml|as email|translate that)",
        re.IGNORECASE,
    )
    return bool(answer_only.match(query.strip()))


def _rewrite_query(query: str, history_block: str) -> str:
    """Use the LLM to rewrite a follow-up into a standalone question."""
    if not history_block:
        return query
    prompt = (
        "Rewrite the follow-up question into a fully standalone question that can be understood "
        "without any conversation history. Keep it concise. Do NOT answer the question.\n\n"
        f"Conversation so far:\n{history_block}\n\n"
        f"Follow-up question: {query}\n\n"
        "Standalone question:"
    )
    rewritten = chat(
        [{"role": "user", "content": prompt}],
        model=settings.LLM_MODEL_SMALL,
        temperature=0.0,
        max_tokens=150,
    )
    # If the LLM returned an error, fall back to the original
    if rewritten.startswith("[Error:") or rewritten.startswith("[LLM"):
        return query
    return rewritten.strip().strip('"')


# ── Main pipeline ─────────────────────────────────────────────────────────────


def run_agent_pipeline(
    query: str,
    persona: Persona,
    format_instruction: str = "",
    vector_store: Any = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Orchestrate the full Kohler CONCORD agent pipeline.

    Args:
        query: User's natural-language question.
        persona: The active user persona (controls document access).
        format_instruction: Free-text description of desired output format.
        vector_store: Initialised VectorStore instance.
        conversation_history: Recent chat messages for multi-turn context.

    Returns:
        Dict with keys: answer, citations, confidence, conflicts,
        format_output, denied_domains, efficiency_stats, is_injection,
        should_abstain, abstention_reason.
    """
    history = conversation_history or []
    history_block = _build_history_block(history)

    # ── 0. Cache check ────────────────────────────────────────────────
    cached = _cache.get(query, persona.value)
    if cached is not None:
        return cached

    # ── 1. Injection check ────────────────────────────────────────────
    detector = InjectionDetector()
    is_safe, reason = detector.check(query)
    if not is_safe:
        result = _empty_result(
            answer=f"🛡️ Request blocked for security reasons: {reason}",
            is_injection=True,
        )
        return result

    # ── 1b. Follow-up detection & query rewriting ─────────────────────
    retrieval_query = query
    skip_retrieval = False

    if history_block and _is_follow_up(query):
        if _is_answer_only_followup(query):
            # User just wants reformatting — reuse previous answer, skip retrieval
            skip_retrieval = True
        else:
            rewritten = _rewrite_query(query, history_block)
            logger.info(f"Rewrote follow-up: '{query}' -> '{rewritten}'")
            # Enrich retrieval with the prior question's key terms so the
            # vector search ranks the right chunks higher.
            prior_user_msgs = [
                m.get("content", "") for m in history
                if m.get("role") == "user"
            ]
            if prior_user_msgs:
                retrieval_query = f"{rewritten} {prior_user_msgs[-1]}"
            else:
                retrieval_query = rewritten

    # ── 2. Route query ────────────────────────────────────────────────
    router = Router()
    route_info = router.route(retrieval_query)
    domains: List[str] = route_info.get("domains", [])
    complexity: str = route_info.get("complexity", "simple")

    model_router = ModelRouter()
    model = model_router.select_model(retrieval_query, complexity)

    # ── 3. Permission-aware retrieval ─────────────────────────────────
    documents = []
    denied_domains: List[str] = []

    if not skip_retrieval and vector_store is not None:
        try:
            pf = PermissionFilter()
            retriever = HybridRetriever(vector_store, pf)
            documents, denied_domains = retriever.retrieve(
                retrieval_query, persona, top_k=10
            )
        except Exception as e:
            logger.error(f"Retrieval error: {e}")

    if not skip_retrieval and not documents:
        result = _empty_result(
            answer=(
                "I could not find relevant information in the knowledge base "
                "for your query with your current access level."
            ),
            denied_domains=denied_domains,
        )
        return result

    # ── 4. Generate draft answers per domain ──────────────────────────
    specialist = DomainSpecialist()
    drafts: List[str] = []
    all_cited: List[str] = []
    domains_used: List[str] = []

    for domain in domains:
        domain_docs = [
            d for d in documents if d.metadata.get("domain") == domain
        ]
        if not domain_docs:
            domain_docs = documents  # fallback: use all retrieved docs

        res = specialist.answer(
            query, domain_docs, domain, history_block=history_block
        )
        answer_text = res.get("answer", "")
        if answer_text:
            drafts.append(answer_text)
            all_cited.extend(res.get("cited_clauses", []))
            domains_used.append(domain)

    if not drafts:
        # Fallback — try with all documents regardless of domain
        res = specialist.answer(
            query, documents, "general", history_block=history_block
        )
        answer_text = res.get("answer", "")
        if answer_text:
            drafts.append(answer_text)
            all_cited.extend(res.get("cited_clauses", []))

    combined_draft = "\n\n".join(drafts) if drafts else "No relevant information found."

    # ── 5. Verify and cite ────────────────────────────────────────────
    verifier = Verifier()
    verified = verifier.verify(
        query, combined_draft, documents, list(set(all_cited)),
        is_follow_up=bool(history_block and _is_follow_up(query)),
    )
    verified.domains_used = domains_used

    # ── 6. Conflict detection ─────────────────────────────────────────
    try:
        conflict_detector = ConflictDetector()
        conflicts = conflict_detector.detect(documents)
        verified.conflicts = conflicts
    except Exception as e:
        logger.error(f"Conflict detection error: {e}")

    # ── 7. Response guard (trust layer) ───────────────────────────────
    guard = ResponseGuard()
    _, safe_answer = guard.check_response(verified.answer, persona)
    verified.answer = safe_answer

    # ── 8. Format output ──────────────────────────────────────────────
    format_output = None
    if format_instruction and format_instruction.strip():
        try:
            contract_parser = OutputContractParser()
            spec = contract_parser.parse(format_instruction)
            formatter = Formatter()
            format_output = formatter.format_output(verified, spec)
        except Exception as e:
            logger.error(f"Formatting error: {e}")

    # ── 9. Build result dict ──────────────────────────────────────────
    result: Dict[str, Any] = {
        "answer": verified.answer,
        "citations": [
            {
                "clause_id": c.clause_id,
                "source_file": c.source_file,
                "relevant_text": c.relevant_text,
                "domain": c.domain,
            }
            for c in verified.citations
        ],
        "confidence": verified.confidence,
        "conflicts": [
            {
                "clause_a_id": c.clause_a_id,
                "clause_b_id": c.clause_b_id,
                "domain_a": c.domain_a,
                "domain_b": c.domain_b,
                "text_a": c.text_a,
                "text_b": c.text_b,
                "description": c.description,
                "recommendation": c.recommendation,
                "severity": c.severity,
            }
            for c in verified.conflicts
        ],
        "format_output": (
            {
                "content": format_output.content,
                "format_type": format_output.format_type,
                "validation_passed": format_output.validation_passed,
                "validation_errors": format_output.validation_errors,
                "file_path": format_output.file_path,
                "file_bytes": format_output.file_bytes,
            }
            if format_output
            else None
        ),
        "denied_domains": denied_domains,
        "should_abstain": verified.should_abstain,
        "abstention_reason": verified.abstention_reason,
        "domains_used": verified.domains_used,
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
        "is_injection": False,
    }

    _cache.set(query, persona.value, result)
    return result


def _empty_result(
    answer: str = "",
    is_injection: bool = False,
    denied_domains: List[str] | None = None,
) -> Dict[str, Any]:
    """Build an empty pipeline result with the given answer."""
    return {
        "answer": answer,
        "citations": [],
        "confidence": 0.0,
        "conflicts": [],
        "format_output": None,
        "denied_domains": denied_domains or [],
        "should_abstain": False,
        "abstention_reason": None,
        "domains_used": [],
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
        "is_injection": is_injection,
    }
