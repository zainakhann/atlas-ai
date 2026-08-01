from app.services.hybrid_search import is_multi_document_query


def test_comparison_keywords_detected():
    assert is_multi_document_query("Compare document A and document B") is True
    assert is_multi_document_query("What is the difference between X and Y?") is True


def test_normal_question_not_flagged():
    assert is_multi_document_query("What is hybrid search?") is False
    assert is_multi_document_query("Summarize the chunking strategy") is False


def test_multiple_filenames_triggers_multi_doc():
    filenames = ["report_a.pdf", "report_b.pdf"]
    question = "What does report_a.pdf say compared to report_b.pdf?"
    assert is_multi_document_query(question, filenames) is True