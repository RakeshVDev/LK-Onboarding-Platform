"""Unified Multi-Format Document Parser (CSV, Excel .xlsx/.xls, PDF, PPTX, DOCX)."""

from __future__ import annotations

from pathlib import Path

from app.application.training.ports import RawExtractedDocument
from app.infrastructure.training.parsers.csv_parser import parse_csv_bytes
from app.infrastructure.training.parsers.docx_parser import parse_docx_bytes
from app.infrastructure.training.parsers.excel_parser import parse_excel_bytes
from app.infrastructure.training.parsers.pdf_parser import parse_pdf_bytes
from app.infrastructure.training.parsers.pptx_parser import parse_pptx_bytes

SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".pdf", ".pptx", ".docx"}
MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # 15 MB guard


class UnifiedDocumentParser:
    """Safely validates & dispatches uploaded files to offline local parsers."""

    def parse(self, filename: str, content: bytes) -> RawExtractedDocument:
        clean_name = Path(filename or "upload.csv").name
        ext = Path(clean_name).suffix.lower()

        if ext not in SUPPORTED_EXTENSIONS:
            allowed = ", ".join(sorted(SUPPORTED_EXTENSIONS))
            raise ValueError(f"Unsupported file type '{ext}'. Allowed formats: {allowed}")

        if not content:
            raise ValueError("Uploaded file is empty.")

        if len(content) > MAX_UPLOAD_BYTES:
            raise ValueError("Uploaded file exceeds 15 MB size limit.")

        if ext == ".csv":
            return parse_csv_bytes(clean_name, content)
        if ext in {".xlsx", ".xls"}:
            return parse_excel_bytes(clean_name, content)
        if ext == ".docx":
            return parse_docx_bytes(clean_name, content)
        if ext == ".pptx":
            return parse_pptx_bytes(clean_name, content)
        if ext == ".pdf":
            return parse_pdf_bytes(clean_name, content)

        raise ValueError(f"Unsupported file format '{ext}'.")

