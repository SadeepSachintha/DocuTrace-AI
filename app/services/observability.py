from langfuse import Langfuse
from app.config import settings

is_langfuse_active = bool(settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY)

if is_langfuse_active:
    print("Initializing Langfuse client for RAG Observability...")
    try:
        langfuse_client = Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST
        )
        print("Langfuse client initialization successful.")
    except Exception as e:
        print(f"Failed to initialize Langfuse client: {e}. Disabling RAG tracing.")
        langfuse_client = None
        is_langfuse_active = False
else:
    print("Langfuse environment keys not set. Running with RAG Observability disabled.")
    langfuse_client = None
