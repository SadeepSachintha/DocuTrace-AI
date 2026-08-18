import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import ChatSession, ChatMessage
from app.schemas import QueryRequest, QueryResponse, CitationSource
from app.services.rag_engine import RAGEngine
from app.services.observability import langfuse_client, is_langfuse_active

router = APIRouter(prefix="/rag", tags=["RAG Assistant"])

@router.post("/query", response_model=QueryResponse)
async def query_rag_assistant(
    request: QueryRequest,
    db: AsyncSession = Depends(get_db)
):
    # 1. Resolve Chat Session
    session_id = request.session_id
    if not session_id:
        session_id = uuid.uuid4()
        session_obj = ChatSession(id=session_id)
        db.add(session_obj)
        await db.flush()
    else:
        # Verify session exists, otherwise create it
        session_stmt = select(ChatSession).where(ChatSession.id == session_id)
        session_res = await db.execute(session_stmt)
        session_obj = session_res.scalar_one_or_none()
        if not session_obj:
            session_obj = ChatSession(id=session_id)
            db.add(session_obj)
            await db.flush()

    # 2. Retrieve Chat History
    history_stmt = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    history_res = await db.execute(history_stmt)
    history_messages = history_res.scalars().all()

    chat_history = ""
    for msg in history_messages:
        role_label = "User" if msg.role == "user" else "Assistant"
        chat_history += f"{role_label}: {msg.content}\n"

    # 3. Re-contextualize query if there is history
    search_query = request.query
    if chat_history.strip():
        search_query = await RAGEngine.condense_question(chat_history, request.query)

    # 4. Tracing Setup
    trace = None
    if is_langfuse_active and langfuse_client:
        trace = langfuse_client.trace(
            name="rag-query",
            input={"query": request.query, "search_query": search_query, "session_id": str(session_id)}
        )

    # 5. Retrieve chunks
    retrieval_span = None
    if trace:
        retrieval_span = trace.span(
            name="retrieval",
            input={"query": search_query, "department": request.department, "top_k": request.similarity_top_k}
        )

    try:
        retrieved_chunks = await RAGEngine.retrieve_similar_chunks(
            db=db,
            query=search_query,
            department=request.department,
            top_k=request.similarity_top_k,
            role=request.role,
            filename=request.filename,
            days_ago=request.days_ago
        )
    except ValueError as e:
        if retrieval_span:
            retrieval_span.end(output={"error": str(e)})
        if trace:
            trace.end(output={"error": str(e)})
        raise HTTPException(status_code=403, detail=str(e))

    if retrieval_span:
        retrieval_span.end(
            output={"chunks_retrieved": [
                {"filename": c["filename"], "page": c["page"], "score": c["score"]} 
                for c in retrieved_chunks
            ]}
        )

    # 6. Generate answer
    generation_span = None
    if trace:
        generation_span = trace.span(
            name="generation",
            input={"query": search_query, "context_chunks": [c["content"] for c in retrieved_chunks]}
        )

    answer = await RAGEngine.generate_grounded_answer(search_query, retrieved_chunks)

    if generation_span:
        generation_span.end(
            output={"answer": answer}
        )

    # 7. Format citations
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

    # 8. Record Chat Messages in Session
    user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=request.query
    )
    assistant_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=answer
    )
    db.add(user_msg)
    db.add(assistant_msg)
    await db.commit()

    return QueryResponse(answer=answer, sources=citations, session_id=session_id)
