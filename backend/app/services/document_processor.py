import os
from pypdf import PdfReader
from docx import Document as DocxDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter


def extract_pages(file_path: str) -> list[tuple[int | None, str]]:
    """Returns a list of (page_number, raw_text) tuples. page_number is None for formats without pages."""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        reader = PdfReader(file_path)
        return [(i + 1, page.extract_text() or "") for i, page in enumerate(reader.pages)]

    elif ext == ".docx":
        doc = DocxDocument(file_path)
        text = "\n".join(p.text for p in doc.paragraphs)
        return [(None, text)]  # DOCX has no reliable page concept at the text level

    elif ext in (".txt", ".md"):
        with open(file_path, "rb") as f:
            raw_bytes = f.read()
        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = raw_bytes.decode("cp1252", errors="replace")
        return [(None, text)]

    else:
        raise ValueError(f"Unsupported file type: {ext}")


def clean_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def chunk_text(text: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=650,
        chunk_overlap=100,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_text(text)