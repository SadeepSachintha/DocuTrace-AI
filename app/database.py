import asyncio
from sqlalchemy.exc import OperationalError, InterfaceError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    max_retries = 10
    retry_delay = 2
    for attempt in range(1, max_retries + 1):
        try:
            async with engine.begin() as conn:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                await conn.run_sync(Base.metadata.create_all)
                # Ensure parent_chunk_id column is added to document_chunks table if not present
                await conn.execute(text("""
                    ALTER TABLE document_chunks 
                    ADD COLUMN IF NOT EXISTS parent_chunk_id UUID REFERENCES document_parent_chunks(id) ON DELETE CASCADE;
                """))
                # Ensure file_hash column is added to documents table if not present
                await conn.execute(text("""
                    ALTER TABLE documents 
                    ADD COLUMN IF NOT EXISTS file_hash VARCHAR(64) UNIQUE;
                """))
                # Ensure sources column is added to chat_messages table if not present
                await conn.execute(text("""
                    ALTER TABLE chat_messages 
                    ADD COLUMN IF NOT EXISTS sources JSONB;
                """))
                # Create HNSW index for high performance vector retrieval
                await conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS chunk_embeddings_hnsw_idx 
                    ON document_chunks 
                    USING hnsw (embedding vector_cosine_ops);
                """))
                # Create GIN index for lexical search
                await conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS chunk_content_fts_idx 
                    ON document_chunks 
                    USING gin (to_tsvector('simple', content));
                """))
            print("Successfully initialized database extension, tables, and indices.")
            return
        except (OperationalError, InterfaceError) as e:
            if attempt == max_retries:
                print(f"Failed to connect to database after {max_retries} attempts.")
                raise e
            print(f"Database connection attempt {attempt}/{max_retries} failed. Retrying in {retry_delay} seconds...")
            await asyncio.sleep(retry_delay)
