import logging
from typing import List, Tuple

from rank_bm25 import BM25Okapi

from src.config import Document, Persona, Domain
from src.knowledge_base.store import VectorStore
from src.retrieval.permissions import PermissionFilter

logger = logging.getLogger(__name__)

class HybridRetriever:
    def __init__(self, vector_store: VectorStore, permission_filter: PermissionFilter):
        self.vector_store = vector_store
        self.permission_filter = permission_filter

    def retrieve(self, query: str, persona: Persona, top_k: int = 8) -> Tuple[List[Document], List[str]]:
        denial_messages = []
        
        where_filter = self.permission_filter.build_chroma_filter(persona)
        
        try:
            # Fetch more candidates for reranking
            semantic_results = self.vector_store.search(query, top_k=top_k * 2, where_filter=where_filter)
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            semantic_results = []
            
        if not semantic_results:
            return [], denial_messages

        # BM25 Keyword Search
        try:
            corpus = [doc.content.lower().split() for doc in semantic_results]
            bm25 = BM25Okapi(corpus)
            tokenized_query = query.lower().split()
            bm25_scores = bm25.get_scores(tokenized_query)
        except Exception as e:
            logger.error(f"BM25 failed: {e}")
            bm25_scores = [0.0] * len(semantic_results)

        combined_results = []
        
        if semantic_results:
            # Normalize scores
            max_semantic_dist = max([d.score for d in semantic_results] + [1e-5])
            max_bm25_score = max(bm25_scores + [1e-5])
            
            for i, doc in enumerate(semantic_results):
                # Convert distance to a similarity score (assuming lower distance is better)
                semantic_score = 1.0 - (doc.score / max_semantic_dist) if max_semantic_dist > 0 else 0
                norm_bm25 = bm25_scores[i] / max_bm25_score if max_bm25_score > 0 else 0
                
                # Combined score
                combined_score = (semantic_score + norm_bm25) / 2
                
                new_doc = Document(content=doc.content, metadata=doc.metadata, score=combined_score)
                combined_results.append(new_doc)
                
        # Sort by score descending
        combined_results.sort(key=lambda x: x.score, reverse=True)
        
        # Deduplicate and limit to top_k
        seen = set()
        final_results = []
        for doc in combined_results:
            doc_id = doc.metadata.get("chunk_id")
            if doc_id not in seen:
                seen.add(doc_id)
                final_results.append(doc)
                if len(final_results) >= top_k:
                    break

        # Generate denial messages for unauthorized domains mentioned in query
        from src.config import PERSONA_DOMAIN_ACCESS
        allowed_domains = [d.value for d in PERSONA_DOMAIN_ACCESS.get(persona, [])]
        for d in Domain:
            if d.value in query.lower() and d.value not in allowed_domains:
                msg = self.permission_filter.explain_denial(persona, d.value)
                if msg:
                    denial_messages.append(msg)
                    
        return final_results, list(set(denial_messages))
