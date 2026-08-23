# Multilingual Enterprise RAG Assistant

**DocuTrace AI** is a decoupled, production-optimized Retrieval-Augmented Generation (RAG) assistant designed for enterprise documents across multiple languages (e.g., English, Sinhala, Tamil). 

Developed and branded as a product of **[SS Labz](https://ss-labz.pages.dev/)**, the system integrates FastAPI, PostgreSQL (with the `pgvector` extension), GIN lexical search indexing, Reciprocal Rank Fusion (RRF), Cross-Encoder Re-ranking, and Langfuse tracing to achieve state-of-the-art retrieval accuracy and observability.

---

### Enhanced Architecture & Pipeline

The retrieval and document processing pipeline consists of 15 key phases to optimize relevance, speed, compliance, and user accessibility:

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
                             │  - Persisted Chat Sessions    │
                             └───────────────┬───────────────┘
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       ▼                                           ▼
           ┌───────────────────────┐                   ┌───────────────────────┐
           │ PostgreSQL + pgvector │                   │   LLM & Embeddings    │
           │  - Port 5433          │                   │  - multilingual-e5    │
           │  - HNSW Dense Index   │                   │  - MiniLM-L-6-v2      │
           │  - FTS Simple Index   │                   │    Cross-Encoder      │
           │  - Chat History DB    │                   │  - OpenAI GPT-4o-mini │
           └───────────────────────┘                   └───────────────────────┘
```

1. **Smart Ingestion De-duplication**: Computes SHA-256 hashes of PDF files. If the hash matches an existing document, it re-uses the metadata and skips indexing, saving compute. If the content changes but the filename matches, it cascades delete old chunks and re-indexes.
2. **Multi-Modal Layout Ingestion**: Extracts text using `PyMuPDF` and executes page-level table grid detection (`page.find_tables()`). Discovered tables are formatted into structured GFM Markdown and appended to the text context.
3. **Hierarchical (Parent-Child) Chunking**: Page contents are saved as `DocumentParentChunk` nodes. Then, pages are split into smaller overlapping child chunks (150 words, 30 words overlap) which are embedded using the `intfloat/multilingual-e5-base` model.
4. **Query Pre-processing (HyDE & Translation)**:
   - Identifies query script language using `langdetect`.
   - Translates non-English queries (Sinhala/Tamil) to English using OpenAI.
   - Generates a hypothetical paragraph answer (HyDE) using the LLM for optimized passage alignment.
5. **Hybrid Retrieval**: Queries the database using the hypothetical answer embedding for pgvector cosine similarity, while concurrently executing full-text lexical matches (GIN indexing) on the combined string of the original + translated query.
6. **Reciprocal Rank Fusion (RRF)**: Merges dense and sparse candidates to rank them based on combined rank values.
7. **Cross-Encoder Re-ranking**: Scores the top 12 RRF candidates using a lightweight Cross-Encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`) on CPU/CUDA, selecting only the top 3-4 highly relevant chunks.
8. **Visual RAG (Vision-Language Processing)**: If a page has drawings, diagrams, or charts, it renders the page to 150 DPI PNG bytes, base64 encodes it, and queries GPT-4o-mini Vision to get detailed text descriptions, appending it to context chunks.
9. **Role-Based Access Control (RBAC)**: Checks simulated user roles (`admin`, `hr_staff`, `finance_staff`, `regular_user`) against allowed department scopes. Returns `403 Forbidden` on access violations and implicitly filters multi-department query results.
10. **Metadata Filtering**: Constraints retrieval SQL queries to filter by unique `filename` strings or upload dates (`days_ago` cutoff date comparing).
11. **Conversational Memory**: Stores message histories in database logs. Condenses multi-turn questions containing reference pronouns ("it", "they") into standalone questions.
12. **Markdown Report Export**: Compiles dialogue histories and cited document sources into downloadable Markdown report assets on-the-fly.
13. **RAG Observability & Evaluation**: Integrates Langfuse tracing spans (retrieval and generation metrics) and runs automated score runs evaluating precision, recall, and answer faithfulness.

---

## File Structure

```text
rag-assistant/
├── app/
├── app/templates/
│   └── index.html             # Premium User interface HTML dashboard
├── USER_MANUAL.md             # End-user guide for dashboard features
├── PRODUCT_HANDOVER.md        # Technical specs, maintenance, and backup guides
├── docker-compose.yml         # PostgreSQL + pgvector (Port 5433)
├── requirements.txt           # Python application dependencies
├── .env                       # Environment configuration details
├── main.py                    # Gateway application entrypoint (Port 8008)
└── scratch/                   # Verification test scripts
    ├── test_hybrid.py         # Lexical sparse vs vector dense RRF verification
    ├── test_parent_child.py   # Hierarchical parent chunk retrieval verification
    ├── test_query_expansion.py # Script detection and query translation verification
    ├── test_table_parsing.py  # Markdown table extraction verification
    ├── test_observability.py  # Langfuse tracing verification
    ├── test_de_duplication.py # Byte-hash de-duplication and overwrite verification
    ├── test_memory.py         # Thread history memory re-contextualization verification
    ├── test_rbac.py           # Role permission and implicit tenant filtering verification
    ├── test_visual_rag.py     # Vision-Language page graphic captioning verification
    ├── test_filters.py        # Filename metadata scope filtering verification
    ├── test_export.py         # Markdown report download verification
    └── test_evaluation.py     # Automated Context precision & faithfulness evaluation
```

---

## Documentation Links

For more details on deploying and operating this product:
- **[User Manual](file:///d:/xampp/htdocs/DocuTrace%20AI/USER_MANUAL.md)**: Steps to upload and query policies, view citations, and troubleshoot issues.
- **[Product Handover Plan](file:///d:/xampp/htdocs/DocuTrace%20AI/PRODUCT_HANDOVER.md)**: Server setup commands, database backups, logs monitoring, and environment keys setup.

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
   You can start both the database container and the FastAPI app server in one click by running:
   ```cmd
   run.bat
   ```
   Or launch the server manually:
   ```bash
   .venv\Scripts\python main.py
   ```
   *Note: The FastAPI application listens on port `8008`.*

---

## Verification Test Scripts

Run verification test scripts via PowerShell inside the root folder:
```powershell
# Set UTF-8 encoding environment variable
$env:PYTHONIOENCODING="utf-8"

# Example: Run the RAG evaluation suite
.venv\Scripts\python "C:/Users/Sadeep/.gemini/antigravity-ide/brain/56b49822-3989-45f7-b663-c4e87459f622/scratch/test_evaluation.py"
```

---

## About SS Labz

**DocuTrace AI** is proudly developed by **[SS Labz](https://ss-labz.pages.dev/)**, dedicated to creating intelligent, localized enterprise solutions. Visit our website at [https://ss-labz.pages.dev/](https://ss-labz.pages.dev/) to discover more systems and products.
