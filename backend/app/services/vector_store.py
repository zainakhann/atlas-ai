import os
import pickle
import numpy as np
import faiss

INDEX_DIR = "data/faiss_index"
INDEX_PATH = os.path.join(INDEX_DIR, "index.faiss")
METADATA_PATH = os.path.join(INDEX_DIR, "metadata.pkl")

EMBEDDING_DIM = 768  # bge-base-en-v1.5 output size

_index = None
_metadata = []  # parallel list: metadata[i] corresponds to vector i in the index


def _ensure_dir():
    os.makedirs(INDEX_DIR, exist_ok=True)


def get_index():
    global _index, _metadata
    if _index is None:
        if os.path.exists(INDEX_PATH):
            _index = faiss.read_index(INDEX_PATH)
            with open(METADATA_PATH, "rb") as f:
                _metadata = pickle.load(f)
        else:
            _index = faiss.IndexFlatIP(EMBEDDING_DIM)  # inner product = cosine similarity on normalized vectors
            _metadata = []
    return _index


def reset_index():
    """Clears the in-memory index so it can be rebuilt from scratch (used at app startup)."""
    global _index, _metadata
    _index = faiss.IndexFlatIP(EMBEDDING_DIM)
    _metadata = []


def add_vectors(vectors: np.ndarray, metadatas: list[dict]):
    """vectors: shape (n, 768), metadatas: list of n dicts (e.g. chunk_id, document_id, content)"""
    global _metadata
    index = get_index()
    index.add(vectors)
    _metadata.extend(metadatas)
    _save()


def search(query_vector: np.ndarray, top_k: int = 5):
    """query_vector: shape (768,) or (1, 768). Returns list of (metadata, score) tuples."""
    index = get_index()
    if index.ntotal == 0:
        return []
    if query_vector.ndim == 1:
        query_vector = query_vector.reshape(1, -1)
    scores, indices = index.search(query_vector, top_k)
    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue
        results.append((_metadata[idx], float(score)))
    return results


def _save():
    _ensure_dir()
    faiss.write_index(_index, INDEX_PATH)
    with open(METADATA_PATH, "wb") as f:
        pickle.dump(_metadata, f)