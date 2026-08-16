from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, text
from openai import AsyncOpenAI
from app.models import DocumentChunk, Document
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
        query_vector = embedding_service.generate_query_embedding(query)
        
        # pgvector cosine similarity operator: <=> (Cosine distance)
        distance_col = DocumentChunk.embedding.cosine_distance(query_vector).label("distance")
        
        stmt = (
            select(
                DocumentChunk.content,
                DocumentChunk.page_number,
                Document.filename,
                distance_col
            )
            .join(Document, DocumentChunk.document_id == Document.id)
            .order_by(distance_col)
            .limit(top_k)
        )
        
        if department:
            stmt = stmt.where(Document.department == department)

        result = await db.execute(stmt)
        rows = result.all()
        
        retrieved = []
        for row in rows:
            content, page, filename, dist = row
            retrieved.append({
                "filename": filename,
                "page": page,
                "content": content,
                "score": float(1 - dist) # Convert distance to cosine similarity
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
