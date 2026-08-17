import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, text, func
from openai import AsyncOpenAI
from app.models import DocumentChunk, Document, DocumentParentChunk
from app.services.embedding_service import embedding_service
from app.config import settings
from typing import List, Dict, Any

# Initialize OpenAI client. We can handle invalid keys gracefully during query execution.
openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

class RAGEngine:
    @staticmethod
    async def retrieve_similar_chunks(
        db: AsyncSession, 
        query: str, 
        department: str | None = None, 
        top_k: int = 4
    ) -> List[Dict[str, Any]]:
        # 1. Generate query embedding for dense search
        query_vector = embedding_service.generate_query_embedding(query)
        
        # Dense Query definition: Cosine similarity search joining parent context
        distance_col = DocumentChunk.embedding.cosine_distance(query_vector).label("distance")
        dense_stmt = (
            select(
                DocumentChunk.content.label("child_content"),
                DocumentParentChunk.content.label("parent_content"),
                DocumentChunk.page_number,
                Document.filename,
                distance_col
            )
            .join(Document, DocumentChunk.document_id == Document.id)
            .outerjoin(DocumentParentChunk, DocumentChunk.parent_chunk_id == DocumentParentChunk.id)
            .order_by(distance_col)
            .limit(top_k * 2) # Fetch extra candidates for fusion
        )
        if department:
            dense_stmt = dense_stmt.where(Document.department == department)

        # Sparse Query definition: Lexical FTS match joining parent context
        tsvector_col = func.to_tsvector('simple', DocumentChunk.content)
        tsquery_col = func.plainto_tsquery('simple', query)
        lexical_score = func.ts_rank(tsvector_col, tsquery_col).label("score")
        
        sparse_stmt = (
            select(
                DocumentChunk.content.label("child_content"),
                DocumentParentChunk.content.label("parent_content"),
                DocumentChunk.page_number,
                Document.filename,
                lexical_score
            )
            .join(Document, DocumentChunk.document_id == Document.id)
            .outerjoin(DocumentParentChunk, DocumentChunk.parent_chunk_id == DocumentParentChunk.id)
            .where(tsvector_col.op('@@')(tsquery_col))
            .order_by(lexical_score.desc())
            .limit(top_k * 2) # Fetch extra candidates for fusion
        )
        if department:
            sparse_stmt = sparse_stmt.where(Document.department == department)

        # Execute both searches concurrently
        dense_task = db.execute(dense_stmt)
        sparse_task = db.execute(sparse_stmt)
        
        try:
            dense_res, sparse_res = await asyncio.gather(dense_task, sparse_task)
            dense_rows = dense_res.all()
            sparse_rows = sparse_res.all()
        except Exception as e:
            # Safe fallback if full-text index query fails or is not supported
            print(f"Sparse search lookup failed: {e}. Falling back to dense-only retrieval.")
            fallback_res = await db.execute(dense_stmt.limit(top_k))
            dense_rows = fallback_res.all()
            sparse_rows = []

        # Reciprocal Rank Fusion (RRF) implementation
        rrf_scores = {}
        candidate_data = {}
        k = 60 # RRF fusion constant

        # Parse dense results and assign RRF ranks
        for rank, row in enumerate(dense_rows):
            child_content, parent_content, page, filename, dist = row
            key = (filename, page, child_content)
            
            if key not in rrf_scores:
                rrf_scores[key] = 0.0
                candidate_data[key] = {
                    "filename": filename,
                    "page": page,
                    "content": parent_content or child_content, # Pass parent context to LLM
                    "child_content": child_content,
                    "base_score": float(1 - dist)
                }
            rrf_scores[key] += 1.0 / (k + (rank + 1))

        # Parse sparse results and accumulate RRF ranks
        for rank, row in enumerate(sparse_rows):
            child_content, parent_content, page, filename, lex_score = row
            key = (filename, page, child_content)
            
            if key not in rrf_scores:
                rrf_scores[key] = 0.0
                candidate_data[key] = {
                    "filename": filename,
                    "page": page,
                    "content": parent_content or child_content, # Pass parent context to LLM
                    "child_content": child_content,
                    "base_score": 0.5
                }
            rrf_scores[key] += 1.0 / (k + (rank + 1))

        # Sort all unique candidates based on their combined RRF score descending
        sorted_keys = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

        retrieved = []
        for key in sorted_keys[:top_k]:
            data = candidate_data[key]
            retrieved.append({
                "filename": data["filename"],
                "page": data["page"],
                "content": data["content"],
                "child_content": data["child_content"],
                # We return the RRF score rounded for verification
                "score": round(rrf_scores[key], 4)
            })

        return retrieved

    @staticmethod
    async def generate_grounded_answer(query: str, context_chunks: List[Dict[str, Any]]) -> str:
        if not context_chunks:
            return "No verified documentation was found matching your query within the selected scope."

        # Graceful fallback if no OpenAI API Key or a mock key is configured
        if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY.startswith("mock"):
            citation_refs = ", ".join([f"({c['filename']}, p. {c['page']})" for c in context_chunks])
            summary_points = "\n".join([f"- {c['content'][:150]}..." for c in context_chunks])
            return (
                f"[MOCK Grounded Response - OpenAI API Key is Mock]\n\n"
                f"You asked: \"{query}\"\n\n"
                f"Retrieved Context Summary:\n{summary_points}\n\n"
                f"Sources: {citation_refs}"
            )

        context_blocks = "\n\n".join([
            f"--- SOURCE: {c['filename']} (Page {c['page']}) ---\n{c['content']}"
            for c in context_chunks
        ])

        system_prompt = (
            "You are a factual corporate document assistant. Answer the user prompt strictly using "
            "the provided source context below. Follow these rules:\n"
            "1. Answer concisely and cite the source filename and page inline [e.g., (HR_Policy.pdf, p. 4)].\n"
            "2. If the context does not contain the answer, state clearly: 'The provided documents do not contain this information.' Do not fabricate facts.\n"
            "3. If the user asks in Sinhala or Tamil, formulate the answer in the same language while preserving technical context."
        )

        user_content = f"Context:\n{context_blocks}\n\nUser Question: {query}"

        try:
            response = await openai_client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.0
            )
            return response.choices[0].message.content
        except Exception as e:
            # If OpenAI throws auth error or other exceptions, return a fallback message with retrieved details
            citation_refs = ", ".join([f"({c['filename']}, p. {c['page']})" for c in context_chunks])
            return (
                f"[Error during OpenAI LLM execution: {str(e)}]\n\n"
                f"Answer fallback (based on retrieved chunks):\n"
                + "\n".join([f"- {c['content'][:150]}..." for c in context_chunks])
                + f"\n\nSources: {citation_refs}"
            )
