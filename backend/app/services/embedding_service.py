"""
Centralized embedding service using SentenceTransformer all-MiniLM-L6-v2 (384 dims).
Used for job embeddings (stored in DB) and user profile embedding (computed at request time).
"""
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

_embedding_model = None


def _get_model():
    """Lazy-load the SentenceTransformer model."""
    global _embedding_model
    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as e:
            logger.warning("Could not load embedding model: %s", e)
    return _embedding_model


def embed_text(text: str) -> Optional[List[float]]:
    """
    Encode text into a 384-dimensional embedding vector
    (all-MiniLM-L6-v2). Returns None if model is unavailable.
    """
    model = _get_model()
    if model is None:
        return None
    if not (text or "").strip():
        return None
    try:
        vec = model.encode([text.strip()], convert_to_numpy=True)
        return vec[0].tolist()
    except Exception as e:
        logger.warning("Embedding failed: %s", e)
        return None


def embed_texts(texts: List[str]) -> Optional[List[List[float]]]:
    """
    Encode multiple texts in one batch. Returns list of 384-dim vectors, or None on failure.
    """
    model = _get_model()
    if model is None:
        return None
    cleaned = [t.strip() if t else "" for t in texts]
    if not any(cleaned):
        return None
    try:
        vecs = model.encode(cleaned, convert_to_numpy=True)
        return [v.tolist() for v in vecs]
    except Exception as e:
        logger.warning("Batch embedding failed: %s", e)
        return None
