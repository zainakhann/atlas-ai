from groq import Groq
from app.core.config import settings

MODEL_NAME = "llama-3.3-70b-versatile"

client = Groq(api_key=settings.groq_api_key)

MAP_PROMPT = """Summarize the following text passage in 2-3 sentences, capturing the key points only.

Passage:
{chunk}

Summary:"""

REDUCE_PROMPT = """The following are summaries of different sections of the same document, in order. Combine them into one coherent summary of the entire document, 4-6 sentences long. Do not just list the sections — synthesize them into a flowing summary.

Return ONLY the summary text, with no preamble, headers, or meta-commentary like "Here is a summary."

Section summaries:
{summaries}

Full document summary:"""

COMPARE_PROMPT = """You are comparing two documents based on their summaries below.

Document A ({name_a}):
{summary_a}

Document B ({name_b}):
{summary_b}

Write a structured comparison covering: (1) what each document is primarily about, (2) key similarities, (3) key differences. Keep it to 5-7 sentences total. Return ONLY the comparison text, no headers or preamble."""


def _summarize_chunk(chunk_content: str) -> str:
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": MAP_PROMPT.format(chunk=chunk_content)}],
    )
    return response.choices[0].message.content.strip()


def map_reduce_summarize(chunk_contents: list[str]) -> str:
    """chunk_contents: list of chunk text, in document order (by chunk_index)."""
    if not chunk_contents:
        return "No content available to summarize."

    # Map step: summarize each chunk individually
    chunk_summaries = [_summarize_chunk(c) for c in chunk_contents]

    # Reduce step: combine chunk summaries into one coherent summary
    combined = "\n\n".join(f"- {s}" for s in chunk_summaries)
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": REDUCE_PROMPT.format(summaries=combined)}],
    )
    return response.choices[0].message.content.strip()


ANALYZE_PROMPTS = {
    "key_points": """The following is the full text of a document. List its key points as a concise bulleted list (5-8 bullets max).

Document:
{document_text}

Return ONLY the bulleted list, no preamble or headers.""",

    "questions": """The following is the full text of a document. List the main questions this document answers or addresses, as a short bulleted list (4-6 bullets max).

Document:
{document_text}

Return ONLY the bulleted list, no preamble or headers.""",

    "simplify": """The following is the full text of a document. Explain it in simple, plain-language terms, as if to someone with no background in the topic. Keep it to 4-6 sentences.

Document:
{document_text}

Return ONLY the explanation, no preamble or headers.""",
}


def analyze_document(mode: str, chunk_contents: list[str]) -> str:
    if mode not in ANALYZE_PROMPTS:
        raise ValueError(f"Unknown analyze mode: {mode}")
    if not chunk_contents:
        return "No content available to analyze."

    document_text = "\n\n".join(chunk_contents)
    prompt = ANALYZE_PROMPTS[mode].format(document_text=document_text)
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()


def compare_documents(name_a: str, summary_a: str, name_b: str, summary_b: str) -> str:
    prompt = COMPARE_PROMPT.format(name_a=name_a, summary_a=summary_a, name_b=name_b, summary_b=summary_b)
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()