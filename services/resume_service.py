import os
import logging

logger = logging.getLogger(__name__)

UPLOADS_DIR = "uploads"


def extract_resume_text(filename: str) -> str:
    """
    Extracts plain text from a PDF or DOCX resume file.
    Returns the text, or an empty string if extraction fails.
    """
    if not filename:
        return ""

    file_path = os.path.join(UPLOADS_DIR, filename)

    if not os.path.exists(file_path):
        logger.warning("Resume file not found: %s", file_path)
        return ""

    ext = os.path.splitext(filename)[1].lower()

    try:
        if ext == ".pdf":
            return _extract_pdf(file_path)
        elif ext in (".doc", ".docx"):
            return _extract_docx(file_path)
        else:
            logger.warning("Unsupported resume format: %s", ext)
            return ""
    except Exception as exc:
        logger.error("Failed to extract resume text from %s: %s", filename, exc)
        return ""


def _extract_pdf(file_path: str) -> str:
    """Extract text from PDF using PyMuPDF (fitz)."""
    import fitz  # PyMuPDF
    text_parts = []
    with fitz.open(file_path) as doc:
        for page in doc:
            text_parts.append(page.get_text())
    return "\n".join(text_parts).strip()


def _extract_docx(file_path: str) -> str:
    """Extract text from DOCX using python-docx."""
    from docx import Document
    doc = Document(file_path)
    paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
    return "\n".join(paragraphs).strip()


def summarise_resume(text: str, max_chars: int = 3000) -> str:
    """
    Truncates resume text to avoid exceeding AI token limits.
    3000 chars ≈ ~750 tokens — well within Gemini's context window.
    """
    if not text:
        return "Not uploaded"
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... [truncated for brevity]"