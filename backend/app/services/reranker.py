from sentence_transformers import CrossEncoder

_reranker = None


def get_reranker():
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _reranker


def rerank(query: str, candidates: list[dict], top_k: int = 5):
    """candidates: list of chunk metadata dicts (must include 'content'). Returns re-scored, re-sorted top_k."""
    if not candidates:
        return []

    model = get_reranker()
    pairs = [[query, c["content"]] for c in candidates]
    scores = model.predict(pairs)

    scored = list(zip(candidates, scores))
    scored.sort(key=lambda x: x[1], reverse=True)

    return [(metadata, float(score)) for metadata, score in scored[:top_k]]