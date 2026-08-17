from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas import QueryRequest, QueryResponse, CitationSource
from app.services.rag_engine import RAGEngine
from app.services.observability import langfuse_client, is_langfuse_active

router = APIRouter(prefix="/rag", tags=["RAG Assistant"])

@router.post("/query", response_model=QueryResponse)
async def query_rag_assistant(
    request: QueryRequest,
    db: AsyncSession = Depends(get_db)
):
    trace = None
    if is_langfuse_active and langfuse_client:
        trace = langfuse_client.trace(
            name="rag-query",
            input={"query": request.query, "department": request.department}
        )

    # 1. Similarity Search with pgvector
    retrieval_span = None
    if trace:
        retrieval_span = trace.span(
            name="retrieval",
            input={"query": request.query, "department": request.department, "top_k": request.similarity_top_k}
        )

    retrieved_chunks = await RAGEngine.retrieve_similar_chunks(
        db=db,
        query=request.query,
        department=request.department,
        top_k=request.similarity_top_k
    )

    if retrieval_span:
        retrieval_span.end(
            output={"chunks_retrieved": [
                {"filename": c["filename"], "page": c["page"], "score": c["score"]} 
                for c in retrieved_chunks
            ]}
        )

    # 2. LLM Synthesis with Grounded Verification
    generation_span = None
    if trace:
        generation_span = trace.span(
            name="generation",
            input={"query": request.query, "context_chunks": [c["content"] for c in retrieved_chunks]}
        )

    answer = await RAGEngine.generate_grounded_answer(request.query, retrieved_chunks)

    if generation_span:
        generation_span.end(
            output={"answer": answer}
        )

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

    if trace:
        trace.end(
            output={"answer": answer, "sources": [c.document_name for c in citations]}
        )

    return QueryResponse(answer=answer, sources=citations)
