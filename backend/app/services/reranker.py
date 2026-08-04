import cohere
from app.core.config import settings

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = cohere.ClientV2(api_key=settings.cohere_api_key)
    return _client


def rerank(query: str, candidates: list[dict], top_k: int = 5):
    """candidates: list of chunk metadata dicts (must include 'content'). Returns re-scored, re-sorted top_k."""
    if not candidates:
        return []

    client = _get_client()
    documents = [c["content"] for c in candidates]

    response = client.rerank(
        model="rerank-v3.5",
        query=query,
        documents=documents,
        top_n=top_k,
    )

    results = []
    for result in response.results:
        metadata = candidates[result.index]
        results.append((metadata, float(result.relevance_score)))
    return results