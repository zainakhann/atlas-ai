from groq import Groq
from app.core.config import settings

MODEL_NAME = "llama-3.3-70b-versatile"

client = Groq(api_key=settings.groq_api_key)

RELEVANCE_THRESHOLD = 0.1  # set from real Cohere rerank scores (0-1 scale, not the old cross-encoder's
                             # raw logit scale): greetings scored 0.02-0.06 max, genuine document matches
                             # scored 0.25-0.63 — 0.1 sits cleanly between the two with real margin

SYSTEM_PROMPT = """You are Atlas, a helpful assistant for answering questions about the user's uploaded documents.

For greetings, small talk, or general conversation not related to the documents, respond naturally and briefly — you don't need to reference the documents for these.

For questions about the documents' content, answer using ONLY the provided context below. If the answer isn't in the context, say "I don't have enough information in the provided documents to answer that." Do not use outside knowledge for document questions.

Match your response length and depth to what the user asks for: if they ask for something short or a quick answer, be concise; if they ask for detail, depth, or a full explanation, be thorough and comprehensive. Otherwise, use your judgment for a natural, appropriately-sized response."""


def _filter_relevant(context_chunks: list[dict]) -> list[dict]:
    """Drops chunks below the relevance threshold. If chunks have no 'score' key,
    this is a no-op — check that your retriever/reranker attaches one."""
    if not context_chunks:
        return []
    if "score" not in context_chunks[0]:
        print(f"[DEBUG] _filter_relevant: no 'score' key found, skipping filter entirely. Sample chunk keys: {list(context_chunks[0].keys())}")
        return context_chunks
    before = len(context_chunks)
    result = [c for c in context_chunks if c["score"] >= RELEVANCE_THRESHOLD]
    print(f"[DEBUG] _filter_relevant: threshold={RELEVANCE_THRESHOLD}, before={before}, after={len(result)}, scores={[round(c['score'], 4) for c in context_chunks]}")
    return result


CLASSIFY_PROMPT = """Classify the message below as exactly one word: GREETING or QUESTION.

GREETING = casual small talk, a greeting, or a social remark (e.g. "hi", "how are you", "good", "thanks", "nothing much").
QUESTION = any request for information, explanation, or facts — even if brief or vague (e.g. "what is a hybrid car?", "tell me about X").

Message: {question}

Respond with exactly one word: GREETING or QUESTION. Nothing else."""


def _classify_intent(question: str) -> str:
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": CLASSIFY_PROMPT.format(question=question)}],
        temperature=0.0,
    )
    result = response.choices[0].message.content.strip().upper()
    return "GREETING" if "GREETING" in result else "QUESTION"


NO_INFO_RESPONSE = "I don't have enough information in the provided documents to answer that."

import re

def _strip_reference_list(text: str) -> str:
    """Removes a trailing References/Sources block the model may add despite prompt instructions.
    Only strips from a References/Sources heading to the end of the text."""
    text = re.sub(r"\n+(References|Sources):?\s*\n.*$", "", text, flags=re.IGNORECASE | re.DOTALL).rstrip()
    return _strip_invalid_citations(text)


def _strip_invalid_citations(text: str) -> str:
    """Removes any inline [...] citation that isn't a valid [Source N] reference —
    catches cases where the model cites a document/section title directly instead."""
    def replace_invalid(match):
        inner = match.group(1)
        return match.group(0) if re.fullmatch(r"Source\s+\d+", inner.strip()) else ""
    text = re.sub(r"\[([^\[\]]+)\]", replace_invalid, text)
    return re.sub(r"[ \t]{2,}", " ", text)  # clean up any double-spacing left behind


def _dedupe_chunks(context_chunks: list[dict]) -> list[dict]:
    """Collapses multiple chunks from the same document+page into a single source,
    keeping the first (highest-ranked) occurrence and merging content for context."""
    seen = {}
    ordered_keys = []
    for chunk in context_chunks:
        key = (chunk["document_id"], chunk.get("page_number"))
        if key not in seen:
            seen[key] = dict(chunk)
            ordered_keys.append(key)
        else:
            seen[key]["content"] += "\n\n" + chunk["content"]
    return [seen[key] for key in ordered_keys]


def build_prompt(question: str, context_chunks: list[dict]) -> str:
    """context_chunks: list of dicts with 'content', 'document_id', 'chunk_id' etc from FAISS search results."""
    if not context_chunks:
        return f"""No relevant document context was found for this message.

User message: {question}

- If this message is a greeting or casual social remark (e.g. "hi", "how are you", "good"), respond naturally and briefly. Do not reference sources or documents.
- If this message is any kind of question or request for information — whether or not it relates to the uploaded documents — respond with exactly: "I don't have enough information in the provided documents to answer that." Do not use your own general knowledge, and do not ask an unrelated clarifying question instead."""

    context_text = "\n\n".join(
        f"[Source {i+1}]: {chunk['content']}"
        for i, chunk in enumerate(context_chunks)
    )
    return f"""Context from the user's documents:
{context_text}

User message: {question}

If this is a document-related question, answer using the context above and reference sources inline using [Source N] notation, where N is a number from 1 to {len(context_chunks)}. Use ONLY this exact format for citations — never invent a different citation style, never add a "References," "Sources," or similar list at the end of your answer, and never cite a source name or section title directly. If this is a greeting or casual message, just respond naturally without needing to use the context."""


def _build_sources(context_chunks: list[dict]) -> list[dict]:
    return [
        {
            "source_number": i + 1,
            "document_id": chunk["document_id"],
            "chunk_id": chunk["chunk_id"],
            "page_number": chunk["page_number"],
            "filename": chunk.get("filename", "Unknown document"),
            "snippet": chunk["content"][:200],
        }
        for i, chunk in enumerate(context_chunks)
    ]


def generate_answer(question: str, context_chunks: list[dict], conversation_history: list[dict] | None = None) -> dict:
    """Non-streaming: waits for the full response, returns it all at once."""
    context_chunks = _filter_relevant(context_chunks)
    context_chunks = _dedupe_chunks(context_chunks)
    history = conversation_history or []

    if not context_chunks:
        if _classify_intent(question) == "QUESTION":
            return {"answer": NO_INFO_RESPONSE, "sources": []}
        # else GREETING — fall through to a normal casual LLM reply below

    prompt = build_prompt(question, context_chunks)
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            *history,
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )
    return {
        "answer": _strip_reference_list(response.choices[0].message.content),
        "sources": _build_sources(context_chunks),
    }


def generate_answer_stream(question: str, context_chunks: list[dict], conversation_history: list[dict] | None = None):
    """Yields answer tokens one at a time as they're generated, then yields the sources dict last.
    conversation_history: list of {"role": "user"|"assistant", "content": str}, oldest first, NOT including the current question."""
    context_chunks = _filter_relevant(context_chunks)
    context_chunks = _dedupe_chunks(context_chunks)
    history = conversation_history or []

    if not context_chunks:
        if _classify_intent(question) == "QUESTION":
            yield {"type": "token", "content": NO_INFO_RESPONSE}
            yield {"type": "sources", "sources": []}
            return
        # else GREETING — fall through to a normal casual LLM reply below

    prompt = build_prompt(question, context_chunks)

    stream = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            *history,
            {"role": "user", "content": prompt},
        ],
        stream=True,
        temperature=0.3,
    )

    for chunk in stream:
        token = chunk.choices[0].delta.content
        if token:
            yield {"type": "token", "content": token}

    yield {"type": "sources", "sources": _build_sources(context_chunks)}


CONTEXTUALIZE_PROMPT = """Given the conversation history and a follow-up message, rewrite the follow-up as a standalone question that makes sense without the history. If the follow-up is already standalone (doesn't depend on prior context), return it unchanged. If the follow-up is casual small talk with no informational intent, return it unchanged.

Conversation history:
{history}

Follow-up message: {question}

Return ONLY the rewritten standalone question (or the original message if no rewrite is needed), with no preamble or explanation."""


def contextualize_query(question: str, conversation_history: list[dict]) -> str:
    """Rewrites a short/ambiguous follow-up into a standalone query using recent conversation history.
    Used only for retrieval — the original question is still used for display and answer generation."""
    if not conversation_history:
        return question

    recent = conversation_history[-6:]  # last few turns is enough context
    history_text = "\n".join(f"{m['role']}: {m['content']}" for m in recent)
    prompt = CONTEXTUALIZE_PROMPT.format(history=history_text, question=question)

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
    )
    rewritten = response.choices[0].message.content.strip().strip('"')
    return rewritten if rewritten else question


QUERY_REWRITE_PROMPT = """Generate 3 alternate phrasings of the following question. The phrasings should preserve the original meaning but use different wording, synonyms, or sentence structure. This is for improving document search recall.

Question: {question}

Return ONLY the 3 phrasings, one per line, with no numbering, bullets, or extra commentary."""


def rewrite_query(question: str) -> list[str]:
    """Returns a list of alternate phrasings of the question (does not include the original)."""
    prompt = QUERY_REWRITE_PROMPT.format(question=question)
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
    )
    raw_text = response.choices[0].message.content
    lines = [line.strip() for line in raw_text.splitlines()]
    lines = [line for line in lines if line]
    return lines[:3]


FOLLOW_UP_PROMPT = """Based on the question and answer below, suggest 3 natural follow-up questions the user might want to ask next. Keep them short and directly related to the topic.

Question: {question}
Answer: {answer}

Return ONLY the 3 follow-up questions, one per line, with no numbering, bullets, or extra commentary."""


def generate_follow_ups(question: str, answer: str) -> list[str]:
    prompt = FOLLOW_UP_PROMPT.format(question=question, answer=answer)
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
    )
    raw_text = response.choices[0].message.content
    lines = [line.strip() for line in raw_text.splitlines()]
    lines = [line for line in lines if line]
    return lines[:3]