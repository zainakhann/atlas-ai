import re
from rank_bm25 import BM25Okapi

_bm25 = None
_corpus_metadata = []


def _tokenize(text: str) -> list[str]:
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)  # strip punctuation, keep word chars and whitespace
    return text.split()


def build_bm25_index(chunks: list[dict]):
    global _bm25, _corpus_metadata
    tokenized_corpus = [_tokenize(chunk["content"]) for chunk in chunks]
    if not tokenized_corpus:
        _bm25 = None
        _corpus_metadata = []
        return
    _bm25 = BM25Okapi(tokenized_corpus)
    _corpus_metadata = chunks


def bm25_search(query: str, top_k: int = 5):
    if _bm25 is None:
        return []
    tokenized_query = _tokenize(query)
    scores = _bm25.get_scores(tokenized_query)
    ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    return [(_corpus_metadata[i], float(scores[i])) for i in ranked_indices]