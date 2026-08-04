import numpy as np
from google import genai
from app.core.config import settings

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def embed_texts(texts: list[str]):
    """Returns a numpy array of shape (len(texts), 768), matching the existing FAISS index dimension."""
    client = _get_client()
    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents=texts,
        config={"output_dimensionality": 768},
    )
    vectors = np.array([e.values for e in result.embeddings], dtype=np.float32)

    # Gemini embeddings need L2 normalization for cosine similarity via inner product (same as before)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    vectors = vectors / norms
    return vectors