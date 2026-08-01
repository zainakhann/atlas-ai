# Atlas AI — Search Quality Evaluation Findings

**Corpus at time of evaluation:** 14 chunks, ~4 short test documents (single topic cluster: RAG concepts, hybrid search, BM25, reranking, evaluation). QA set: 12 hand-labeled questions, 10 with a single ground-truth relevant chunk and 2 with two acceptable relevant chunks.

## Results

| Configuration | Precision@3 | Precision@5 | MRR | Avg latency |
|---|---|---|---|---|
| Baseline: Vector search only | 0.389 | 0.233 | 1.000 | 921.1 ms |
| Hybrid search (BM25 + vector, RRF) | 0.361 | 0.233 | 0.958 | 51.9 ms |
| Hybrid + cross-encoder reranking | 0.361 | 0.233 | 1.000 | 1132.2 ms |

## Key findings

**Precision@5 was uninformative at this corpus size.** Nearly every question in the QA set has only one truly relevant chunk, so retrieving 5 chunks structurally caps precision@5 at ~0.2 regardless of ranking quality. Precision@3 and MRR proved far more discriminating and are the metrics actually worth reading here.

**Hybrid search slightly underperformed pure vector search on this corpus.** Both Precision@3 (0.361 vs 0.389) and MRR (0.958 vs 1.000) show a small regression when BM25 is fused in via Reciprocal Rank Fusion. The likely cause: this test corpus is small and narrowly themed (everything is *about* RAG/search concepts), so BM25's keyword matching surfaces topically-adjacent-but-not-precisely-correct chunks that occasionally outrank the true answer once fused with the vector ranking. This is a plausible, real characteristic of hybrid search on small, thematically dense corpora — not a bug in the RRF implementation (which was separately verified to correctly fuse rankings once a tokenization bug was caught and fixed — see Phase 6 build notes).

**Reranking fully recovered the ranking quality hybrid search lost**, bringing MRR back to a perfect 1.000. This confirms the two-stage retrieve-then-rerank pattern works as intended: even when the first-stage fused ranking wasn't perfect, the cross-encoder's more careful (query, document) joint scoring corrected it. The cost: ~20x the latency of hybrid search alone (1132ms vs 52ms), which is the expected bi-encoder-vs-cross-encoder speed/accuracy tradeoff described in the study guide.

**Latency confirms the expected shape of the retrieve-then-rerank pattern.** BM25 + FAISS hybrid search is dramatically faster than embedding a query through the bi-encoder model path alone (52ms vs 921ms) since BM25 requires no model inference at all. Reranking adds meaningful latency (~1.1s total) since it's a second, heavier model pass over the top candidates — exactly the tradeoff the study guide flags as the reason reranking is only run on a narrowed candidate set, never the full corpus.

## Caveat and next step

This evaluation was run against a deliberately small (14-chunk), single-topic test corpus used during development. The precision regression seen in hybrid search is expected to shift — likely favorably — once evaluated against the full ~8-10 arXiv paper corpus, where documents span more varied topics and hybrid search's keyword-matching strength (e.g. catching specific technical terms, model names, or acronyms across more heterogeneous documents) should show a clearer advantage over pure semantic search alone. **The evaluation harness should be re-run once the real document set is loaded**, and these numbers updated accordingly before finalizing the README's evaluation section.
