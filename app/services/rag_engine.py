import asyncio
from datetime import datetime, timedelta
from langdetect import detect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, text, func
from openai import AsyncOpenAI
from app.models import DocumentChunk, Document, DocumentParentChunk
from app.services.embedding_service import embedding_service
from app.config import settings
from typing import List, Dict, Any

# Initialize OpenAI client. We can handle invalid keys gracefully during query execution.
openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

ROLE_PERMISSIONS = {
    "admin": ["HR", "Finance", "Operations", "Security"],
    "hr_staff": ["HR", "Operations"],
    "finance_staff": ["Finance", "Operations"],
    "regular_user": ["Operations"]
}

class RAGEngine:
    @staticmethod
    async def retrieve_similar_chunks(
        db: AsyncSession, 
        query: str, 
        department: str | None = None, 
        top_k: int = 4,
        role: str = "regular_user",
        filename: str | None = None,
        days_ago: int | None = None
    ) -> List[Dict[str, Any]]:
        # Detect query language
        try:
            detected_lang = detect(query)
        except Exception:
            detected_lang = "en"

        # Translate query if non-English
        translated_query = query
        is_mock_key = not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY.startswith("mock")
        
        if settings.ENABLE_TRANSLATION and detected_lang != "en" and not is_mock_key:
            try:
                sys_prompt = "You are a professional translator. Translate the following user query to English. Do not add any explanation or greeting, just provide the exact translation."
                response = await openai_client.chat.completions.create(
                    model=settings.LLM_MODEL,
                    messages=[
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": query}
                    ],
                    temperature=0.0
                )
                translated_query = response.choices[0].message.content.strip()
                print(f"Translated query '{query}' ({detected_lang}) -> '{translated_query}' (en)")
            except Exception as e:
                print(f"Query translation failed: {e}")

        # Hypothetical Document Embeddings (HyDE) expansion
        search_text = translated_query
        if settings.ENABLE_HYDE and not is_mock_key:
            try:
                sys_prompt = "You are a corporate search helper. Write a brief, direct 1-2 sentence hypothetical answer to the user query that might appear in a company policy document. Do not add any greeting, preamble, or formatting."
                response = await openai_client.chat.completions.create(
                    model=settings.LLM_MODEL,
                    messages=[
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": translated_query}
                    ],
                    temperature=0.0
                )
                hyde_answer = response.choices[0].message.content.strip()
                search_text = hyde_answer
                print(f"HyDE expansion for query '{translated_query}' -> '{hyde_answer}'")
            except Exception as e:
                print(f"HyDE generation failed: {e}")

        # Generate query embedding on the expanded/translated text
        query_vector = embedding_service.generate_query_embedding(search_text)
        
        # Determine query candidate limits based on whether reranking is active
        search_limit = top_k * 4 if settings.ENABLE_RERANKER else top_k * 2
        
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
            .limit(search_limit)
        )
        # Resolve allowed departments for Role
        allowed_depts = ROLE_PERMISSIONS.get(role, ["Operations"])
        if department:
            if department not in allowed_depts:
                raise ValueError(f"Role '{role}' is not authorized to access department '{department}'.")
            depts_to_search = [department]
        else:
            depts_to_search = allowed_depts

        dense_stmt = dense_stmt.where(Document.department.in_(depts_to_search))
        if filename:
            dense_stmt = dense_stmt.where(Document.filename == filename)
        if days_ago:
            cutoff_date = datetime.utcnow() - timedelta(days=days_ago)
            dense_stmt = dense_stmt.where(Document.created_at >= cutoff_date)

        # Lexical search combines original + translated keywords
        lexical_query = query
        if translated_query != query:
            lexical_query = f"{query} {translated_query}"

        # Sparse Query definition: Lexical FTS match joining parent context
        tsvector_col = func.to_tsvector('simple', DocumentChunk.content)
        tsquery_col = func.plainto_tsquery('simple', lexical_query)
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
            .limit(search_limit)
        )
        sparse_stmt = sparse_stmt.where(Document.department.in_(depts_to_search))
        if filename:
            sparse_stmt = sparse_stmt.where(Document.filename == filename)
        if days_ago:
            cutoff_date = datetime.utcnow() - timedelta(days=days_ago)
            sparse_stmt = sparse_stmt.where(Document.created_at >= cutoff_date)

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

        # Retrieve a wider pool if re-ranking, else retrieve top_k directly
        rrf_pool_limit = top_k * 3 if settings.ENABLE_RERANKER else top_k

        retrieved = []
        for key in sorted_keys[:rrf_pool_limit]:
            data = candidate_data[key]
            retrieved.append({
                "filename": data["filename"],
                "page": data["page"],
                "content": data["content"],
                "child_content": data["child_content"],
                # We return the RRF score rounded for verification
                "score": round(rrf_scores[key], 4)
            })

        # Apply Cross-Encoder re-ranking if active
        if settings.ENABLE_RERANKER:
            from app.services.reranker_service import reranker_service
            retrieved = reranker_service.rerank(query, retrieved, top_n=top_k)

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

    @staticmethod
    async def condense_question(chat_history: str, query: str) -> str:
        is_mock_key = not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY.startswith("mock")
        if is_mock_key:
            return query
            
        sys_prompt = (
            "Given the following chat history and a follow-up question, rephrase the follow-up question "
            "to be a standalone question, in its original language, that contains all necessary context from the chat history. "
            "Do not answer the question, just return the standalone, rephrased question."
        )
        user_content = f"Chat History:\n{chat_history}\n\nFollow-up Question: {query}\nStandalone Question:"
        
        try:
            response = await openai_client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.0
            )
            condensed = response.choices[0].message.content.strip()
            print(f"Condensed query '{query}' -> '{condensed}'")
            return condensed
        except Exception as e:
            print(f"Failed to condense question: {e}")
            return query
