from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas import QueryRequest, QueryResponse, CitationSource
from app.services.rag_engine import RAGEngine

router = APIRouter(prefix="/rag", tags=["RAG Assistant"])

@router.post("/query", response_model=QueryResponse)
async def query_rag_assistant(
    request: QueryRequest,
    db: AsyncSession = Depends(get_db)
):
    # 1. Similarity Search with pgvector
    retrieved_chunks = await RAGEngine.retrieve_similar_chunks(
        db=db,
        query=request.query,
        department=request.department,
        top_k=request.similarity_top_k
    )

    # 2. LLM Synthesis with Grounded Verification
    answer = await RAGEngine.generate_grounded_answer(request.query, retrieved_chunks)

    # 3. Format Source Citations
    citations = [
        CitationSource(
            document_name=chunk["filename"],
            page_number=chunk["page"],
            content_snippet=chunk.get("child_content", chunk["content"])[:200] + "...",
            similarity_score=round(chunk["score"], 4)
        )
        for chunk in retrieved_chunks
    ]

    return QueryResponse(answer=answer, sources=citations)
