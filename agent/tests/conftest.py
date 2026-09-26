import re
import numpy as np
import pytest

from config import settings as S
from utils.text import normalize_text

DIM = S.EMBEDDING_DIM


def fake_embed(texts):
    """Deterministic char-trigram hashing embedder: similar strings -> similar vectors. No model download."""
    out = np.zeros((len(texts), DIM), dtype=np.float32)
    for i, t in enumerate(texts):
        s = f"  {normalize_text(t)}  "
        for j in range(len(s) - 2):
            out[i, hash(s[j:j + 3]) % DIM] += 1.0
        n = np.linalg.norm(out[i])
        if n:
            out[i] /= n
    return out


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    import rag.store as store
    monkeypatch.setattr(S, "QDRANT_PATH", tmp_path / "qdrant")
    monkeypatch.setattr(S, "TMP_DIR", tmp_path / "tmp")
    monkeypatch.setattr(S, "RESULT_DIR", tmp_path / "result")
    monkeypatch.setattr(S, "LOG_DIR", tmp_path / "logs")
    monkeypatch.setattr(S, "TAVILY_API_KEY", "")
    for mod in ("rag.store", "analysis.skills", "agent.nodes.gap_agent"):
        monkeypatch.setattr(f"{mod}.embed", fake_embed)
    store.reset_client()
    yield
    store.reset_client()
