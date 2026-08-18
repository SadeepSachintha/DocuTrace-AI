# DocuTrace AI - Product Handover Plan

**DocuTrace AI** is an enterprise-grade multilingual RAG assistant, developed and branded as a product of **[SS Labz](https://ss-labz.pages.dev/)**. This document serves as the operational handover plan for deploying, maintaining, and managing the application in production.

---

## 1. Technical Architecture & Stack

| Component | Technology | Detail |
| :--- | :--- | :--- |
| **Gateway Application** | FastAPI (Python 3.10+) | Listens on port `8008`, serves API routes and HTML UI. |
| **Vector Database** | PostgreSQL 16 + `pgvector` | Runs as a Docker container mapped to host port `5433`. |
| **Dense Vector Model** | `intfloat/multilingual-e5-base` | 768-dimensional multilingual dense embeddings. |
| **Re-ranking Model** | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Lightweight passage ranking cross-encoder (~80MB). |
| **LLM Orchestrator** | OpenAI API (`gpt-4o-mini`) | Grounded synthesis, query translation, and history condensing. |
| **Observability Tracing**| Langfuse Python SDK | Conditionally logs query latency, tokens, and retrieval. |

---

## 2. Database Models & Schema Specifications

The database contains the following tables:

1. **`documents`**: Stores uploaded PDF filenames, tags, languages, and SHA-256 file hashes.
2. **`document_parent_chunks`**: Stores full page-level text segments.
3. **`document_chunks`**: Stores sub-page chunks, metadata tags, and dense vector embeddings.
4. **`chat_sessions`**: Manages conversational message logs grouped by thread IDs.
5. **`chat_messages`**: Stores multi-turn message history (`user` and `assistant` roles) referenced to `chat_sessions` with cascading deletes.

---

## 3. Environment Configurations (`.env`)

Deploying the system requires setting up the following values in the `.env` file:

```ini
# Database configuration
DATABASE_URL=postgresql+asyncpg://rag_user:rag_password@localhost:5433/rag_documents

# Embeddings Dimension
EMBEDDING_MODEL_NAME=intfloat/multilingual-e5-base
EMBEDDING_DIMENSION=768

# LLM Configs
OPENAI_API_KEY=your-api-key-here
LLM_MODEL=gpt-4o-mini

# Advanced Optimization Settings
ENABLE_HYDE=True
ENABLE_TRANSLATION=True
ENABLE_RERANKER=True
CROSS_ENCODER_MODEL_NAME=cross-encoder/ms-marco-MiniLM-L-6-v2

# Tracing configs (Optional: leave blank to disable)
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=https://cloud.langfuse.com
```

---

## 4. Maintenance & Operational Monitoring

### Startup & Orchestrator Operations
1. **Starting the database container**:
   Ensure Docker is active and run:
   ```bash
   docker compose up -d
   ```
2. **Launching the FastAPI Gateway**:
   Activate the virtual environment and execute the application:
   ```bash
   .venv\Scripts\python main.py
   ```

### Backup and Database Restores
To dump the database content from the PostgreSQL container:
```bash
# Dump DB data to local file
docker exec -t rag_pgvector pg_dump -U rag_password -d rag_documents > backup_rag.sql

# Restore DB data from local dump
cat backup_rag.sql | docker exec -i rag_pgvector psql -U rag_password -d rag_documents
```

---

## 5. Product Handoff Checklist

Before concluding the handover, verify that:
- [ ] Docker container is running and port `5433` is listening.
- [ ] FastAPI server is active on `http://localhost:8008` and the GUI loads.
- [ ] Documents can be successfully uploaded under different departments.
- [ ] English, Sinhala, and Tamil queries return source-attributed answers with precise page citations.
- [ ] Asking follow-up queries with pronouns correctly resolves preceding context in the conversation thread.
- [ ] Clicking "New Chat" resets the conversation log and initiates a new session ID.

---

## Technical Support

For further technical support, enhancements, or custom integration services, please contact the **SS Labz** team:
- **Website**: [https://ss-labz.pages.dev/](https://ss-labz.pages.dev/)
- **Product Branding**: Developed under SS Labz core systems.
