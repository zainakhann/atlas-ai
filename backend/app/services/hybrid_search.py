from app.services.vector_store import search as vector_search
from app.services.bm25_search import bm25_search
from app.services.llm import rewrite_query
from app.services.embeddings import embed_texts

RRF_K = 60


def hybrid_search(query: str, query_vector, top_k: int = 5, candidate_k: int = 20, allowed_document_ids: list[str] | None = None):
    """Combines vector search and BM25 search using Reciprocal Rank Fusion.
    If allowed_document_ids is given, filters BEFORE ranking (not after), and over-fetches
    from each underlying store so filtering doesn't starve real matches when the global
    index contains other users' documents."""
    fetch_k = candidate_k * 5 if allowed_document_ids else candidate_k

    vector_results = vector_search(query_vector, top_k=fetch_k)
    keyword_results = bm25_search(query, top_k=fetch_k)

    if allowed_document_ids is not None:
        allowed = set(allowed_document_ids)
        vector_results = [(m, s) for m, s in vector_results if m["document_id"] in allowed][:candidate_k]
        keyword_results = [(m, s) for m, s in keyword_results if m["document_id"] in allowed][:candidate_k]

    rrf_scores = {}
    chunk_lookup = {}

    for rank, (metadata, _score) in enumerate(vector_results, start=1):
        chunk_id = metadata["chunk_id"]
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + 1 / (RRF_K + rank)
        chunk_lookup[chunk_id] = metadata

    for rank, (metadata, _score) in enumerate(keyword_results, start=1):
        chunk_id = metadata["chunk_id"]
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + 1 / (RRF_K + rank)
        chunk_lookup[chunk_id] = metadata

    ranked_chunk_ids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)
    top_chunk_ids = ranked_chunk_ids[:top_k]

    return [(chunk_lookup[cid], rrf_scores[cid]) for cid in top_chunk_ids]


def hybrid_search_with_rewriting(question: str, top_k: int = 5, candidate_k: int = 20):
    """Runs hybrid search for the original question plus LLM-generated rephrasings, then fuses all result sets."""
    queries = [question] + rewrite_query(question)

    rrf_scores = {}
    chunk_lookup = {}

    for query_text in queries:
        query_vector = embed_texts([query_text])[0]
        results = hybrid_search(query_text, query_vector, top_k=candidate_k, candidate_k=candidate_k)
        for rank, (metadata, _score) in enumerate(results, start=1):
            chunk_id = metadata["chunk_id"]
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + 1 / (RRF_K + rank)
            chunk_lookup[chunk_id] = metadata

    ranked_chunk_ids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)
    top_chunk_ids = ranked_chunk_ids[:top_k]

    return [(chunk_lookup[cid], rrf_scores[cid]) for cid in top_chunk_ids]


COMPARISON_KEYWORDS = [
    "compare", "comparison", "difference", "differences", "versus", " vs ",
    "across documents", "across all documents", "each document", "every document",
    "all documents", "both documents", "between documents",
]


def is_multi_document_query(question: str, document_filenames: list[str] | None = None) -> bool:
    """Heuristic: flags a query as needing per-document retrieval based on comparison language
    or explicit mention of multiple document names."""
    lowered = question.lower()

    if any(kw in lowered for kw in COMPARISON_KEYWORDS):
        return True

    if document_filenames:
        mentioned = [fn for fn in document_filenames if fn.lower() in lowered]
        if len(mentioned) >= 2:
            return True

    return False


def per_document_hybrid_search(question: str, query_vector, document_ids: list[str], top_k_per_doc: int = 3):
    """Runs hybrid search scoped to each document individually, then combines results.
    Prevents one dominant document from crowding out others in multi-document questions."""
    all_results = []

    for doc_id in document_ids:
        vector_candidates = vector_search(query_vector, top_k=50)
        vector_candidates = [
            (m, s) for m, s in vector_candidates if m["document_id"] == doc_id
        ][:top_k_per_doc]

        keyword_candidates = bm25_search(question, top_k=50)
        keyword_candidates = [
            (m, s) for m, s in keyword_candidates if m["document_id"] == doc_id
        ][:top_k_per_doc]

        rrf_scores = {}
        chunk_lookup = {}
        for rank, (metadata, _s) in enumerate(vector_candidates, start=1):
            cid = metadata["chunk_id"]
            rrf_scores[cid] = rrf_scores.get(cid, 0) + 1 / (RRF_K + rank)
            chunk_lookup[cid] = metadata
        for rank, (metadata, _s) in enumerate(keyword_candidates, start=1):
            cid = metadata["chunk_id"]
            rrf_scores[cid] = rrf_scores.get(cid, 0) + 1 / (RRF_K + rank)
            chunk_lookup[cid] = metadata

        top_ids = sorted(rrf_scores.keys(), key=lambda c: rrf_scores[c], reverse=True)[:top_k_per_doc]
        all_results.extend([(chunk_lookup[cid], rrf_scores[cid]) for cid in top_ids])

    return all_results