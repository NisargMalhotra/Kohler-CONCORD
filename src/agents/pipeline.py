"""
KOHLER CONCORD — Agent Pipeline Orchestrator.

Orchestrates the full multi-agent pipeline:
  Injection Check → Query Rewriter (if follow-up) → Router →
  Permission-Aware Retrieval → Domain Specialist(s) →
  Tool Execution (if applicable) → Verifier/Critic →
  Conflict Detector → Formatter → Validated Output
"""

import json
import logging
import re
import time
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
from src.llm import chat, chat_json, efficiency_stats
from src.tools import build_tool_registry, log_tool_call

logger = logging.getLogger(__name__)

# Module-level singletons (re-created per import, but cheap)
_cache = ResponseCache()
_tool_registry = build_tool_registry()

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
    relevant = [
        m for m in conversation_history if m.get("role") in ("user", "assistant")
    ]
    trimmed = relevant[-(_MAX_HISTORY_TURNS * 2) :]
    if not trimmed:
        return ""
    lines = []
    for m in trimmed:
        role = "User" if m["role"] == "user" else "Assistant"
        content = m.get("content", m.get("answer", ""))
        if len(content) > 400:
            content = content[:400] + "…"
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _is_follow_up(query: str) -> bool:
    return bool(_REFORMULATION_RE.search(query))


def _is_answer_only_followup(query: str) -> bool:
    pattern = re.compile(
        r"(?i)^(?:format|convert|turn|show|put|rewrite|send|draft|email|table|json|xml|excel)\b"
    )
    return bool(pattern.match(query.strip()))


def _rewrite_query(query: str, history_block: str) -> str:
    """Use the LLM to rewrite a follow-up query into a standalone question."""
    messages = [
        {
            "role": "system",
            "content": (
                "Rewrite the follow-up question as a standalone question "
                "using the conversation history for context. "
                "Return ONLY the rewritten question as plain text, nothing else."
            ),
        },
        {
            "role": "user",
            "content": f"History:\n{history_block}\n\nFollow-up: {query}",
        },
    ]
    rewritten = chat(messages, model=settings.LLM_MODEL_SMALL, max_tokens=256)
    if rewritten.startswith("[Error"):
        return query
    return rewritten.strip() or query


# ── Tool execution helper ──────────────────────────────────────────────────────


def _execute_tool_and_synthesize(
    tool_call: Dict[str, Any],
    query: str,
    persona: Persona,
    documents: List,
) -> Dict[str, Any]:
    """Execute a tool call and synthesize a natural language response.

    Returns a dict with 'answer', 'cited_clauses', 'key_points',
    'tool_used' metadata.
    """
    tool_name = tool_call.get("name", "")
    tool_params = tool_call.get("parameters", {})

    # Execute the tool
    tool_result = _tool_registry.execute(tool_name, tool_params)

    # Log the tool call
    log_tool_call(
        tool_name=tool_name,
        parameters=tool_params,
        result=tool_result.result,
        success=tool_result.success,
        role=persona.value,
        error=tool_result.error,
    )

    if not tool_result.success:
        return {
            "answer": (
                f"I tried to {tool_name.replace('_', ' ')} but encountered an error: "
                f"{tool_result.error}. Please try again or contact support."
            ),
            "cited_clauses": [],
            "key_points": [],
            "tool_used": {
                "name": tool_name,
                "parameters": tool_params,
                "success": False,
                "error": tool_result.error,
            },
        }

    # Ask the LLM to synthesize a natural response from the tool result
    synthesis_messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful enterprise assistant. A tool was called to handle "
                "the user's request. Write a clear, professional response that explains "
                "what was done and any next steps. Be warm and informative. "
                "Return JSON with keys: 'answer' (str), 'cited_clauses' (List[str]), "
                "'key_points' (List[str])."
            ),
        },
        {
            "role": "user",
            "content": (
                f"User's request: {query}\n"
                f"Tool called: {tool_name}\n"
                f"Tool result: {json.dumps(tool_result.result)}\n\n"
                f"Write a helpful response."
            ),
        },
    ]
    synthesis = chat_json(synthesis_messages)

    if "error" in synthesis:
        # Fallback: use the tool result's message directly
        answer = tool_result.result.get("message", json.dumps(tool_result.result))
    else:
        answer = synthesis.get("answer", tool_result.result.get("message", ""))

    return {
        "answer": answer,
        "cited_clauses": synthesis.get("cited_clauses", []) if "error" not in synthesis else [],
        "key_points": synthesis.get("key_points", []) if "error" not in synthesis else [],
        "tool_used": {
            "name": tool_name,
            "parameters": tool_params,
            "success": True,
            "result_summary": tool_result.result.get("message", ""),
            "ticket_id": tool_result.result.get("ticket_id"),
            "registration_id": tool_result.result.get("registration_id"),
        },
    }


# ── Main pipeline ──────────────────────────────────────────────────────────────


def run_agent_pipeline(
    query: str,
    persona: Persona,
    format_instruction: str = "",
    vector_store=None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Full multi-agent pipeline with trust layer, now with tool calling.

    Returns:
        Dict with keys: answer, citations, confidence, conflicts,
        format_output, denied_domains, efficiency_stats, is_injection,
        should_abstain, abstention_reason, tool_used.
    """
    history = conversation_history or []
    start_time = time.time()
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

    # ── 4. Generate draft answers per domain (with tool support) ──────
    specialist = DomainSpecialist()
    drafts: List[str] = []
    all_cited: List[str] = []
    domains_used: List[str] = []
    tool_used: Optional[Dict[str, Any]] = None

    # Get tools prompt for this role
    tools_prompt = _tool_registry.get_tools_prompt(persona.value)

    for domain in domains:
        domain_docs = [
            d for d in documents if d.metadata.get("domain") == domain
        ]
        if not domain_docs:
            domain_docs = documents  # fallback: use all retrieved docs

        res = specialist.answer(
            query, domain_docs, domain,
            history_block=history_block,
            tools_prompt=tools_prompt,
        )

        # Check if the specialist wants to call a tool
        if res.get("tool_call") and tool_used is None:
            tool_result = _execute_tool_and_synthesize(
                res["tool_call"], query, persona, documents
            )
            tool_used = tool_result.get("tool_used")
            answer_text = tool_result.get("answer", "")
            if answer_text:
                drafts.append(answer_text)
                all_cited.extend(tool_result.get("cited_clauses", []))
                domains_used.append(domain)
            # Don't process more domains after a tool call
            break

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
    verified, verification_level = verifier.verify(
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
    elapsed_ms = (time.time() - start_time) * 1000
    efficiency_stats.total_response_time_ms += elapsed_ms
    efficiency_stats.total_responses += 1

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
        "verification_level": verification_level,
        "denied_domains": denied_domains,
        "should_abstain": verified.should_abstain,
        "abstention_reason": verified.abstention_reason,
        "domains_used": verified.domains_used,
        "tool_used": tool_used,
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
        "verification_level": "n/a",
        "denied_domains": denied_domains or [],
        "should_abstain": False,
        "abstention_reason": None,
        "domains_used": [],
        "tool_used": None,
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
