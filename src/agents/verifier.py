import logging
import re
from typing import Dict, List, Any, Tuple

from src.config import Document, VerifiedAnswer, Citation, settings
from src.llm import chat_json, efficiency_stats

logger = logging.getLogger(__name__)


class Verifier:
    """Verifies draft answers against provided documents.
    
    Degradation levels:
      1. Full LLM verification (primary model)
      2. LLM verification (smaller model)
      3. Rule-based verification (no LLM)
      4. Unverified (draft answer returned as-is)
    """

    def verify(
        self,
        query: str,
        draft_answer: str,
        documents: List[Document],
        cited_clauses: List[str],
        is_follow_up: bool = False,
    ) -> Tuple[VerifiedAnswer, str]:
        """
        Verifies all claims in a draft answer.
        
        Returns:
            Tuple of (VerifiedAnswer, verification_level).
            verification_level is one of: "full", "small_model", "rule_based", "unverified".
        """
        docs_context = "\n".join(
            [f"Clause {d.metadata.get('clause_id', 'unknown')}: {d.content}" for d in documents]
        )

        follow_up_note = ""
        if is_follow_up:
            follow_up_note = (
                "\n\nIMPORTANT: This answer is part of a multi-turn conversation. "
                "The draft may reference or summarize information from a previous answer that was already verified. "
                "Do NOT penalize the confidence score for reusing previously verified information. "
                "Only flag claims that introduce NEW facts not found in the documents."
            )

        system_prompt = (
            "You are a verifier agent. Check EVERY claim in the draft answer against the provided documents. "
            "For each claim, find supporting text or flag it as unsupported. "
            "Assign a confidence score (0.0 to 1.0) based on evidence strength. "
            "If confidence < 0.4, set should_abstain=True and provide a reason. "
            "Strip any claims not supported by the documents from the verified answer. "
            "Return JSON with keys: 'verified_answer' (str), 'confidence' (float), 'should_abstain' (bool), "
            "'abstention_reason' (str or null), and 'verified_clauses' (List[str])."
            + follow_up_note
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Draft Answer:\n{draft_answer}\n\nDocuments:\n{docs_context}\n\nQuery: {query}"},
        ]

        # Level 1: Full LLM verification
        res = chat_json(messages)
        if "error" not in res:
            return self._parse_llm_result(res, draft_answer, cited_clauses, documents), "full"

        logger.warning(f"Primary verifier failed: {res['error']}. Trying smaller model.")

        # Level 2: Smaller/cheaper model
        res = chat_json(messages, model=settings.LLM_MODEL_SMALL)
        if "error" not in res:
            return self._parse_llm_result(res, draft_answer, cited_clauses, documents), "small_model"

        logger.warning(f"Small-model verifier also failed: {res['error']}. Falling back to rules.")

        # Level 3: Rule-based verification
        rule_result, rule_confidence = self._rule_based_verify(draft_answer, documents, cited_clauses)
        if rule_confidence >= 0.35:
            efficiency_stats.degraded_responses += 1
            citations = self._build_citations(rule_result["verified_clauses"], documents)
            return VerifiedAnswer(
                answer=draft_answer,
                citations=citations,
                confidence=rule_confidence,
                should_abstain=rule_confidence < 0.4,
                abstention_reason="Verified by rules only — LLM verifier unavailable." if rule_confidence < 0.4 else None,
            ), "rule_based"

        # Level 4: Unverified fallback
        logger.error("All verification methods failed. Returning unverified draft.")
        efficiency_stats.degraded_responses += 1
        fallback_citations = self._build_citations(cited_clauses, documents)
        return VerifiedAnswer(
            answer=draft_answer,
            citations=fallback_citations,
            confidence=0.3,
            should_abstain=False,
            abstention_reason=None,
        ), "unverified"

    def _parse_llm_result(
        self, res: dict, draft_answer: str, cited_clauses: List[str], documents: List[Document]
    ) -> VerifiedAnswer:
        """Parse a successful LLM verification response."""
        confidence = float(res.get("confidence", 0.0))
        should_abstain = bool(res.get("should_abstain", False))
        if confidence < 0.4:
            should_abstain = True

        verified_answer = res.get("verified_answer", draft_answer)
        verified_clauses = res.get("verified_clauses", cited_clauses)
        citations = self._build_citations(verified_clauses, documents)

        return VerifiedAnswer(
            answer=verified_answer,
            citations=citations,
            confidence=confidence,
            should_abstain=should_abstain,
            abstention_reason=res.get("abstention_reason", ""),
        )

    def _rule_based_verify(
        self, draft_answer: str, documents: List[Document], cited_clauses: List[str]
    ) -> Tuple[Dict[str, Any], float]:
        """Lightweight rule-based verification without any LLM call.
        
        Checks:
        1. Does the answer reference clause IDs that exist in the documents?
        2. Is the answer substantive (>20 words)?
        """
        # Extract clause IDs from the draft answer text
        clause_pattern = re.compile(r"[A-Z]{2,4}-[A-Z]{2,4}-\d{3}(?:\.\d+)?")
        found_in_answer = set(clause_pattern.findall(draft_answer))

        # Get all valid clause IDs from retrieved documents
        doc_clause_ids = set()
        for d in documents:
            cid = d.metadata.get("clause_id", "")
            if cid:
                doc_clause_ids.add(cid)

        # Also consider the specialist's cited_clauses
        all_cited = set(cited_clauses) | found_in_answer
        verified_clauses = [c for c in all_cited if c in doc_clause_ids]

        has_valid_citation = len(verified_clauses) > 0
        is_substantive = len(draft_answer.split()) > 20

        if has_valid_citation and is_substantive:
            confidence = 0.55
        elif has_valid_citation:
            confidence = 0.4
        else:
            confidence = 0.3

        return {
            "verified_clauses": verified_clauses if verified_clauses else cited_clauses,
        }, confidence

    def _build_citations(self, verified_clauses: List[str], documents: List[Document]) -> List[Citation]:
        """Build Citation objects for verified claims."""
        citations = []
        for clause in verified_clauses:
            for doc in documents:
                if doc.metadata.get("clause_id") == clause:
                    citations.append(Citation(
                        clause_id=clause,
                        source_file=doc.metadata.get("source_file", "unknown"),
                        relevant_text=doc.content[:150] + "...",
                        domain=doc.metadata.get("domain", "unknown"),
                    ))
                    break
        return citations
