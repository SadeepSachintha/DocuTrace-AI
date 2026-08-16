from sentence_transformers import SentenceTransformer
from app.config import settings
from typing import List

class EmbeddingService:
    def __init__(self):
        # Multilingual-e5 expects queries prefixed with "query: " and passages with "passage: "
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)

    def generate_passage_embeddings(self, texts: List[str]) -> List[List[float]]:
        prefixed_texts = [f"passage: {t}" for t in texts]
        embeddings = self.model.encode(prefixed_texts, normalize_embeddings=True)
        return embeddings.tolist()

    def generate_query_embedding(self, query: str) -> List[float]:
        prefixed_query = f"query: {query}"
        embedding = self.model.encode(prefixed_query, normalize_embeddings=True)
        return embedding.tolist()

embedding_service = EmbeddingService()
