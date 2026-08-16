from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://rag_user:rag_password@localhost:5433/rag_documents"
    EMBEDDING_MODEL_NAME: str = "intfloat/multilingual-e5-base"
    OPENAI_API_KEY: str = "mock-or-actual-key"
    LLM_MODEL: str = "gpt-4o-mini"
    EMBEDDING_DIMENSION: int = 768

    class Config:
        env_file = ".env"

settings = Settings()
