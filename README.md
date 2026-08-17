# Multilingual Enterprise RAG Assistant

A decoupled, production-optimized Retrieval-Augmented Generation (RAG) assistant designed for enterprise documents across multiple languages (e.g., English, Sinhala, Tamil). The system integrates FastAPI, PostgreSQL (with the `pgvector` extension), GIN lexical search indexing, Reciprocal Rank Fusion (RRF), Cross-Encoder Re-ranking, and Langfuse tracing to achieve state-of-the-art retrieval accuracy and observability.

---

## Enhanced Architecture & Pipeline

The retrieval pipeline consists of 6 key phases to optimize relevance and cross-lingual compliance:

```text
                                  [ Client UI / Mobile ]
                                             │
                                     (HTTP REST / SSE)
                                             ▼
                             ┌───────────────────────────────┐
                             │     FastAPI Gateway (App)     │  (Port 8008)
                             │  - Auth & Metadata Filters    │
                             │  - Lang Detection & Chunker   │
                             │  - Vector Retrieval Engine    │
                             └───────────────┬───────────────┘
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       ▼                                           ▼
           ┌───────────────────────┐                   ┌───────────────────────┐
           │ PostgreSQL + pgvector │                   │   LLM & Embeddings    │
           │  - Port 5433          │                   │  - multilingual-e5    │
           │  - HNSW Dense Index   │                   │  - MiniLM-L-6-v2      │
           │  - FTS Simple Index   │                   │    Cross-Encoder      │
           │  - RRF Fusion Stage   │                   │  - OpenAI GPT-4o-mini │
           └───────────────────────┘                   └───────────────────────┘
```

1. **Multi-Modal Layout Ingestion**: Extracts text using `PyMuPDF` and executes page-level table grid detection (`page.find_tables()`). Discovered tables are formatted into structured GFM Markdown and appended to the text context. Empty or scanned visual pages are tagged with placeholders (e.g. `[Scanned Visual Page...]`) rather than skipped.
2. **Hierarchical (Parent-Child) Chunking**: Page contents are saved as `DocumentParentChunk` nodes. Then, pages are split into smaller overlapping child chunks (150 words, 30 words overlap) which are embedded using the `intfloat/multilingual-e5-base` model.
3. **Query Pre-processing (HyDE & Translation)**:
   - Identifies query script language using `langdetect`.
   - Translates non-English queries (Sinhala/Tamil) to English using OpenAI.
   - Generates a hypothetical paragraph answer (HyDE) using the LLM for optimized passage alignment.
4. **Hybrid Retrieval**: Queries the database using the hypothetical answer embedding for pgvector cosine similarity, while concurrently executing full-text lexical matches (GIN indexing) on the combined string of the original + translated query.
5. **Reciprocal Rank Fusion (RRF)**: Merges dense and sparse candidates to rank them based on combined rank values.
6. **Cross-Encoder Re-ranking**: Scores the top 12 RRF candidates using a lightweight Cross-Encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`) on CPU/CUDA, selecting only the top 3-4 highly relevant chunks.
7. **Context Synthesis & Tracing**: Synthesizes the final response using parent page context blocks and logs tracing events asynchronously to Langfuse.

---

## File Structure

```text
rag-assistant/
├── app/
│   ├── __init__.py
│   ├── config.py              # Configuration settings (HyDE, Reranker, Langfuse)
│   ├── database.py            # Async engine, session, table and index creation
│   ├── models.py              # SQLAlchemy tables (Parent & Child Chunks)
│   ├── schemas.py             # Pydantic schemas (Query & Ingestion payloads)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── document_parser.py # PDF layout table parser and child splitter
│   │   ├── embedding_service.py # Vector embedding generator (multilingual-e5)
│   │   ├── reranker_service.py # BGE/MiniLM Cross-Encoder re-ranker
│   │   ├── observability.py   # Langfuse Tracing initialization client
│   │   └── rag_engine.py      # Pre-processing, hybrid RRF, and synthesis
│   └── routes/
│       ├── __init__.py
│       ├── documents.py       # PDF document upload (Page parent & child link)
│       └── chat.py            # RAG query routes with Langfuse span tracing
├── docker-compose.yml         # PostgreSQL + pgvector (Port 5433)
├── requirements.txt           # Python application dependencies
├── .env                       # Environment configuration details
└── main.py                    # Gateway application entrypoint (Port 8008)
```

---

## Getting Started

### Prerequisites

- **Python**: Version `3.10` or higher.
- **Docker**: Docker Desktop running.
- **OpenAI API Key** (Optional: Fallbacks to mock responses if key is mock).

### Setup Instructions

1. **Clone & Navigate**:
   ```bash
   cd "d:/xampp/htdocs/DocuTrace AI"
   ```

2. **Start the Vector Database**:
   ```bash
   docker compose up -d
   ```
   *Note: PostgreSQL maps to host port `5433` to prevent conflicts with local SQL databases.*

3. **Install Dependencies**:
   ```bash
   # Create environment
   python -m venv .venv

   # Activate and install dependencies (Windows PowerShell)
   .venv\Scripts\pip install -r requirements.txt
   ```

4. **Configure Credentials (`.env`)**:
   ```ini
   DATABASE_URL=postgresql+asyncpg://rag_user:rag_password@localhost:5433/rag_documents
   EMBEDDING_MODEL_NAME=intfloat/multilingual-e5-base
   OPENAI_API_KEY=your-openai-key
   LLM_MODEL=gpt-4o-mini
   EMBEDDING_DIMENSION=768
   ENABLE_HYDE=True
   ENABLE_TRANSLATION=True
   ENABLE_RERANKER=True
   CROSS_ENCODER_MODEL_NAME=cross-encoder/ms-marco-MiniLM-L-6-v2
   # Optional Langfuse tracing keys
   LANGFUSE_PUBLIC_KEY=
   LANGFUSE_SECRET_KEY=
   LANGFUSE_HOST=https://cloud.langfuse.com
   ```

5. **Start the API Server**:
   ```bash
   .venv\Scripts\python main.py
   ```
   *Note: The FastAPI application listens on port `8008`.*

---

## Verification Test Scripts

Five scratch verification scripts are provided under the `scratch/` directory to validate the RAG components:

1. **`test_hybrid.py`**: Ingests a policy containing a unique serial ID `"B-77-Z"`. Queries for `"B-77-Z"` and verifies RRF retrieves the exact match lexical chunk despite low semantic vector scores.
2. **`test_parent_child.py`**: Ingests a multiline document and queries for details. Verifies child chunks retrieve page-level parent chunks for synthesis while retaining the exact child snippet for source citations.
3. **`test_query_expansion.py`**: Queries in Sinhala (`"ඩ්‍රෝන යානයේ..."`) against English document text. Verifies cross-lingual script detection and retrieval success.
4. **`test_table_parsing.py`**: Ingests drawn table grids, converts them to Markdown tables, and verifies that the assistant answers query details (e.g. Leave policy figures) correctly.
5. **`test_observability.py`**: Verifies RAG queries execute smoothly when Langfuse is disabled or empty.

Run test scripts via PowerShell:
```powershell
$env:PYTHONIOENCODING="utf-8"; .venv\Scripts\python "C:/Users/Sadeep/.gemini/antigravity-ide/brain/56b49822-3989-45f7-b663-c4e87459f622/scratch/test_table_parsing.py"
```

---

## API Documentation

Once the server is running, the interactive documentation is available at `http://localhost:8008/docs`.
- **Upload Endpoint**: `POST /documents/upload`
- **RAG Chat Endpoint**: `POST /rag/query`
