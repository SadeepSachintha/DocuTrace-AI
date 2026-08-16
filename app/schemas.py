from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from uuid import UUID

class DocumentUploadResponse(BaseModel):
    document_id: UUID
    filename: str
    chunks_indexed: int
    detected_language: str

class QueryRequest(BaseModel):
    query: str
    department: Optional[str] = None
    similarity_top_k: int = 4

class CitationSource(BaseModel):
    document_name: str
    page_number: int
    content_snippet: str
    similarity_score: float

class QueryResponse(BaseModel):
    answer: str
    sources: List[CitationSource]
