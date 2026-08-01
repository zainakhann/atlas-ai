import sys
import os
import json
import time

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import SessionLocal
from app.models.document import Chunk
from app.services.embeddings import embed_texts
from app.services.vector_store import search as vector_search
from app.services.bm25_search import build_bm25_index
from app.services.hybrid_search import hybrid_search
from app.services.reranker import rerank

TOP_K = 5
TOP_K_SMALL = 3


def load_qa_set():
    path = os.path.join(os.path.dirname(__file__), "qa_set.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def precision_at_k(retrieved_ids: list[str], relevant_ids: set[str]) -> float:
    if not retrieved_ids:
        return 0.0
    hits = sum(1 for rid in retrieved_ids if rid in relevant_ids)
    return hits / len(retrieved_ids)


def reciprocal_rank(retrieved_ids: list[str], relevant_ids: set[str]) -> float:
    for rank, rid in enumerate(retrieved_ids, start=1):
        if rid in relevant_ids:
            return 1 / rank
    return 0.0


def run_config(name: str, qa_set: list[dict], retrieve_fn):
    precisions_at_5 = []
    precisions_at_3 = []
    reciprocal_ranks = []
    start = time.time()

    for item in qa_set:
        question = item["question"]
        relevant_ids = set(item["relevant_chunk_ids"])

        retrieved = retrieve_fn(question)
        retrieved_ids = [r["chunk_id"] for r in retrieved]

        precisions_at_5.append(precision_at_k(retrieved_ids, relevant_ids))
        precisions_at_3.append(precision_at_k(retrieved_ids[:TOP_K_SMALL], relevant_ids))
        reciprocal_ranks.append(reciprocal_rank(retrieved_ids, relevant_ids))

    elapsed = time.time() - start
    avg_precision_5 = sum(precisions_at_5) / len(precisions_at_5)
    avg_precision_3 = sum(precisions_at_3) / len(precisions_at_3)
    mrr = sum(reciprocal_ranks) / len(reciprocal_ranks)
    avg_latency_ms = (elapsed / len(qa_set)) * 1000

    print(f"\n=== {name} ===")
    print(f"Precision@{TOP_K_SMALL}: {avg_precision_3:.3f}")
    print(f"Precision@{TOP_K}: {avg_precision_5:.3f}")
    print(f"MRR: {mrr:.3f}")
    print(f"Avg latency: {avg_latency_ms:.1f} ms/query")


def main():
    db = SessionLocal()
    chunks = db.query(Chunk).all()
    chunk_dicts = [
        {
            "chunk_id": str(c.id),
            "document_id": str(c.document_id),
            "page_number": c.page_number,
            "content": c.content,
        }
        for c in chunks
    ]
    build_bm25_index(chunk_dicts)
    qa_set = load_qa_set()
    print(f"Loaded {len(qa_set)} QA pairs, evaluating against {len(chunks)} chunks\n")

    def baseline_vector(question: str):
        query_vec = embed_texts([question])[0]
        results = vector_search(query_vec, top_k=TOP_K)
        return [metadata for metadata, score in results]

    def hybrid(question: str):
        query_vec = embed_texts([question])[0]
        results = hybrid_search(question, query_vec, top_k=TOP_K, candidate_k=20)
        return [metadata for metadata, score in results]

    def hybrid_reranked(question: str):
        query_vec = embed_texts([question])[0]
        candidates = hybrid_search(question, query_vec, top_k=20, candidate_k=20)
        candidate_chunks = [metadata for metadata, score in candidates]
        reranked = rerank(question, candidate_chunks, top_k=TOP_K)
        return [metadata for metadata, score in reranked]

    run_config("Baseline: Vector Search Only", qa_set, baseline_vector)
    run_config("Hybrid Search (BM25 + Vector, RRF)", qa_set, hybrid)
    run_config("Hybrid + Reranked", qa_set, hybrid_reranked)


if __name__ == "__main__":
    main()