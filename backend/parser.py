import os
from fastapi import UploadFile
from typing import Optional
import io

# pdf parsing
from pdfminer.high_level import extract_text as pdf_extract_text
# docx parsing
import docx

def save_upload_file(upload: UploadFile, dest_path: str) -> None:
    """Save a FastAPI UploadFile to disk (binary)"""
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    with open(dest_path, "wb") as fw:
        for chunk in iter(lambda: upload.file.read(1024 * 1024), b""):
            fw.write(chunk)
    try:
        upload.file.close()
    except Exception:
        pass

def parse_pdf(path: str) -> str:
    try:
        return pdf_extract_text(path) or ""
    except Exception:
        # fallback: read bytes and decode
        try:
            with open(path, "rb") as fr:
                return fr.read().decode(errors="ignore")
        except Exception:
            return ""

def parse_docx(path: str) -> str:
    try:
        doc = docx.Document(path)
        parts = [p.text for p in doc.paragraphs]
        return "\n".join(parts)
    except Exception:
        try:
            with open(path, "rb") as fr:
                return fr.read().decode(errors="ignore")
        except Exception:
            return ""

def parse_resume(path: str, filename: Optional[str] = None) -> str:
    """Detect file type and extract text."""
    if not filename:
        filename = os.path.basename(path)
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf":
        return parse_pdf(path)
    if ext in [".doc", ".docx"]:
        return parse_docx(path)
    # fallback: try to read as text
    try:
        with open(path, "rb") as fr:
            return fr.read().decode(errors="ignore")
    except Exception:
        return ""
