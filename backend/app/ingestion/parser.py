"""Document parser supporting PDF, DOCX, and Markdown formats."""

from pathlib import Path
from dataclasses import dataclass


@dataclass
class ParsedDocument:
    """Result of parsing a document file."""
    text: str
    page_count: int = 1
    title: str | None = None


def parse_pdf(file_path: str) -> ParsedDocument:
    """Extract text from a PDF file using pypdf."""
    from pypdf import PdfReader

    reader = PdfReader(file_path)
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)

    title = None
    if reader.metadata and reader.metadata.title:
        title = reader.metadata.title

    return ParsedDocument(
        text="\n\n".join(pages),
        page_count=len(reader.pages),
        title=title,
    )


def parse_docx(file_path: str) -> ParsedDocument:
    """Extract text from a DOCX file using python-docx."""
    from docx import Document

    doc = Document(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]

    # Try to use first heading as title
    title = None
    if doc.paragraphs and doc.paragraphs[0].style.name.startswith("Heading"):
        title = doc.paragraphs[0].text

    return ParsedDocument(
        text="\n\n".join(paragraphs),
        page_count=1,  # DOCX doesn't have fixed pages
        title=title,
    )


def parse_markdown(file_path: str) -> ParsedDocument:
    """Read a Markdown file and return raw text."""
    path = Path(file_path)
    text = path.read_text(encoding="utf-8")

    # Try to use first # heading as title
    title = None
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("# "):
            title = stripped.lstrip("# ").strip()
            break

    return ParsedDocument(
        text=text,
        page_count=1,
        title=title,
    )


PARSER_MAP = {
    "pdf": parse_pdf,
    "docx": parse_docx,
    "markdown": parse_markdown,
}


def parse_document(file_path: str, doc_type: str) -> ParsedDocument:
    """Parse a document file and return extracted text.

    Args:
        file_path: Path to the document file.
        doc_type: One of 'pdf', 'docx', 'markdown'.

    Returns:
        ParsedDocument with extracted text and metadata.

    Raises:
        ValueError: If doc_type is not supported.
    """
    parser = PARSER_MAP.get(doc_type)
    if parser is None:
        raise ValueError(f"Unsupported document type: {doc_type}. Supported: {list(PARSER_MAP.keys())}")
    return parser(file_path)
