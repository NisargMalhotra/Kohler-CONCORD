import logging
from typing import List

from src.config import Document, Conflict
from src.llm import chat_json

logger = logging.getLogger(__name__)

class ConflictDetector:
    KNOWN_CONFLICTS = [
        {
            "pair": ("HR-POL-005", "FIN-GL-003"),
            "description": "Expense approval thresholds differ between HR and Finance.",
            "recommendation": "Follow the more restrictive Finance guidelines (FIN-GL-003)."
        },
        {
            "pair": ("PRV-POL-003", "LGL-CMP-004"),
            "description": "Data retention periods contradict between Privacy and Legal.",
            "recommendation": "Legal compliance (LGL-CMP-004) takes precedence for retention."
        },
        {
            "pair": ("HR-POL-008", "LGL-CMP-006"),
            "description": "Remote work jurisdiction rules conflict.",
            "recommendation": "Consult Legal before approving cross-border remote work."
        }
    ]

    def detect(self, documents: List[Document]) -> List[Conflict]:
        conflicts = []
        conflicts.extend(self._check_known_conflicts(documents))
        
        try:
            llm_conflicts = self._check_llm_conflicts(documents)
            conflicts.extend(llm_conflicts)
        except Exception as e:
            logger.error(f"Error detecting LLM conflicts: {e}")
            
        return conflicts

    def _check_known_conflicts(self, documents: List[Document]) -> List[Conflict]:
        conflicts = []
        doc_map = {doc.metadata.get("clause_id"): doc for doc in documents if doc.metadata.get("clause_id")}
        
        for known in self.KNOWN_CONFLICTS:
            id1, id2 = known["pair"]
            
            doc1 = None
            doc2 = None
            for clause_id, doc in doc_map.items():
                if clause_id.startswith(id1):
                    doc1 = doc
                if clause_id.startswith(id2):
                    doc2 = doc
                    
            if doc1 and doc2 and doc1.metadata.get("domain") != doc2.metadata.get("domain"):
                conflict = Conflict(
                    clause_a_id=doc1.metadata.get("clause_id", id1),
                    clause_b_id=doc2.metadata.get("clause_id", id2),
                    domain_a=doc1.metadata.get("domain", "unknown"),
                    domain_b=doc2.metadata.get("domain", "unknown"),
                    text_a=doc1.content[:100] + "...",
                    text_b=doc2.content[:100] + "...",
                    description=known["description"],
                    recommendation=known["recommendation"],
                    severity="high"
                )
                conflicts.append(conflict)
                
        return conflicts

    def _check_llm_conflicts(self, documents: List[Document]) -> List[Conflict]:
        conflicts = []
        
        # Only check if we have docs from multiple domains
        domains = set(doc.metadata.get("domain") for doc in documents if doc.metadata.get("domain"))
        if len(domains) < 2:
            return conflicts
            
        context = []
        for i, doc in enumerate(documents):
            clause_id = doc.metadata.get("clause_id", f"doc_{i}")
            domain = doc.metadata.get("domain", "unknown")
            context.append(f"[{domain}] {clause_id}:\n{doc.content}\n")
            
        context_str = "\n".join(context)
        
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a policy conflict detector. Compare policy clauses from different domains "
                    "and identify contradictions. Return a JSON object with a 'conflicts' key containing "
                    "a list of conflicts. Each conflict should have 'clause_a_id', 'clause_b_id', "
                    "'description', and 'recommendation'."
                )
            },
            {
                "role": "user",
                "content": f"Analyze these documents for cross-domain conflicts:\n\n{context_str}"
            }
        ]
        
        response = chat_json(messages)
        
        if "error" in response:
            logger.warning(f"LLM conflict detection failed: {response['error']}")
            return conflicts
            
        llm_found = response.get("conflicts", [])
        doc_map = {doc.metadata.get("clause_id"): doc for doc in documents if doc.metadata.get("clause_id")}
        
        for item in llm_found:
            id_a = item.get("clause_a_id")
            id_b = item.get("clause_b_id")
            
            doc_a = doc_map.get(id_a)
            doc_b = doc_map.get(id_b)
            
            if doc_a and doc_b and doc_a.metadata.get("domain") != doc_b.metadata.get("domain"):
                conflicts.append(Conflict(
                    clause_a_id=id_a,
                    clause_b_id=id_b,
                    domain_a=doc_a.metadata.get("domain", "unknown"),
                    domain_b=doc_b.metadata.get("domain", "unknown"),
                    text_a=doc_a.content[:100] + "...",
                    text_b=doc_b.content[:100] + "...",
                    description=item.get("description", "Potential conflict detected by LLM."),
                    recommendation=item.get("recommendation", "Review and reconcile policies."),
                    severity="medium"
                ))
                
        return conflicts
