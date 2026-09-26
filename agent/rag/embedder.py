"""Multilingual embeddings (EN/AR in one vector space). The team's version used bge-small-en
(English-only) with mean pooling; BGE models are trained for CLS pooling. sentence-transformers
applies each model's correct pooling and normalisation."""
from functools import lru_cache

import numpy as np

from config import settings as S


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer  # lazy: heavy import

    return SentenceTransformer(S.EMBEDDING_MODEL, device=S.EMBEDDING_DEVICE)


def embed(texts: list[str]) -> np.ndarray:
    """(n, dim) float32, L2-normalised, so a dot product is cosine similarity."""
    if not texts:
        return np.zeros((0, S.EMBEDDING_DIM), dtype=np.float32)
    return _model().encode(texts, normalize_embeddings=True, batch_size=16, show_progress_bar=False).astype(np.float32)
