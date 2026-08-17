import torch
from sentence_transformers import CrossEncoder
from app.config import settings
from typing import List, Dict, Any

class RerankerService:
    def __init__(self):
        self.enabled = settings.ENABLE_RERANKER
        if self.enabled:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"Initializing Cross-Encoder model '{settings.CROSS_ENCODER_MODEL_NAME}' on {device}...")
            try:
                self.model = CrossEncoder(settings.CROSS_ENCODER_MODEL_NAME, device=device)
                print("Cross-Encoder initialization complete.")
            except Exception as e:
                print(f"Error loading Cross-Encoder model: {e}. Disabling re-ranking.")
                self.model = None
                self.enabled = False
        else:
            self.model = None

    def rerank(self, query: str, candidates: List[Dict[str, Any]], top_n: int) -> List[Dict[str, Any]]:
        if not self.enabled or not self.model or not candidates:
            return candidates[:top_n]

        # Form pairs of (query, context) for relevance assessment
        pairs = [[query, c["content"]] for c in candidates]
        
        try:
            # Predict relevance scores.
            scores = self.model.predict(pairs)
            
            # Associate scores with candidates
            for candidate, score in zip(candidates, scores):
                candidate["rerank_score"] = float(score)
                # Overwrite score displayed in client with rerank score for validation
                candidate["score"] = float(score)

            # Sort by rerank score descending
            candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
            
            print(f"Reranked {len(candidates)} candidates. Top score: {candidates[0]['rerank_score']:.4f}")
        except Exception as e:
            print(f"Failed to execute cross-encoder reranking: {e}. Falling back to default RRF ranking.")
            for c in candidates:
                c["rerank_score"] = None

        return candidates[:top_n]

reranker_service = RerankerService()
