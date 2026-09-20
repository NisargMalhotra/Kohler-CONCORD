import logging
from typing import List
from src.config import Document

logger = logging.getLogger(__name__)

class DocumentChunker:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_documents(self, documents: List[Document]) -> List[Document]:
        chunked_docs = []
        for doc in documents:
            if not doc.content or len(doc.content) <= self.chunk_size:
                chunked_docs.append(doc)
                continue
            
            content = doc.content
            start = 0
            chunk_index = 0
            while start < len(content):
                end = min(start + self.chunk_size, len(content))
                chunk_text = content[start:end]
                
                new_metadata = doc.metadata.copy()
                new_metadata["chunk_id"] = f"{doc.metadata.get('chunk_id', 'doc')}_{chunk_index}"
                
                chunked_docs.append(Document(content=chunk_text, metadata=new_metadata))
                
                chunk_index += 1
                start += self.chunk_size - self.chunk_overlap
                
        return chunked_docs
