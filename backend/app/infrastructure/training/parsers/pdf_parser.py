"""Local PDF Parser (pure Python zlib stream & BT/ET text extractor + optional pypdf)."""

from __future__ import annotations

import io
import re
import zlib

from app.application.training.ports import RawExtractedDocument


def _unescape_pdf_literal(raw_bytes: bytes) -> str:
    out = bytearray()
    i = 0
    n = len(raw_bytes)
    while i < n:
        ch = raw_bytes[i]
        if ch == 92 and i + 1 < n:  # backslash
            nxt = raw_bytes[i + 1]
            escapes = {
                ord("n"): 10,
                ord("r"): 13,
                ord("t"): 9,
                ord("b"): 8,
                ord("f"): 12,
                ord("("): 40,
                ord(")"): 41,
                ord("\\"): 92,
            }
            if nxt in escapes:
                out.append(escapes[nxt])
                i += 2
                continue
            if 48 <= nxt <= 55:  # octal \ddd
                oct_digits = bytes([nxt])
                j = i + 2
                while j < min(n, i + 4) and 48 <= raw_bytes[j] <= 55:
                    oct_digits += bytes([raw_bytes[j]])
                    j += 1
                out.append(int(oct_digits, 8) & 0xFF)
                i = j
                continue
            out.append(nxt)
            i += 2
        else:
            out.append(ch)
            i += 1
    if out.startswith(b"\xfe\xff"):
        return out[2:].decode("utf-16-be", errors="ignore")
    return out.decode("latin-1", errors="ignore")


def _extract_text_from_pdf_stream(stream_bytes: bytes) -> list[str]:
    text_str = stream_bytes.decode("latin-1", errors="ignore")
    if "BT" not in text_str and "Tj" not in text_str and "TJ" not in text_str:
        return []

    lines: list[str] = []
    for bt_block in re.findall(r"BT\b(.*?)\bET", text_str, flags=re.S):
        current_line_parts: list[str] = []
        # Match literals (...) followed by Tj/', or arrays [...] followed by TJ
        token_re = re.compile(r"(\((?:\\.|[^\\()])*\)|<([0-9A-Fa-f\s]+)>)\s*(Tj|'|\"|)|\[(.*?)\]\s*TJ|(\bT\*|\bTd\b|\bTD\b)", re.S)
        for m in token_re.finditer(bt_block):
            if m.group(1) and m.group(3):
                tok = m.group(1)
                if tok.startswith("("):
                    decoded = _unescape_pdf_literal(tok[1:-1].encode("latin-1", errors="ignore"))
                else:
                    hex_clean = re.sub(r"\s+", "", m.group(2) or "")
                    try:
                        decoded = bytes.fromhex(hex_clean).decode("utf-16-be" if hex_clean.startswith("feff") else "latin-1", errors="ignore")
                    except ValueError:
                        decoded = ""
                current_line_parts.append(decoded)
                if m.group(3) in {"'", '"'}:
                    line = "".join(current_line_parts).strip()
                    if line:
                        lines.append(line)
                    current_line_parts = []
            elif m.group(4) is not None:
                arr_body = m.group(4)
                for lit in re.findall(r"\((?:\\.|[^\\()])*\)", arr_body):
                    current_line_parts.append(
                        _unescape_pdf_literal(lit[1:-1].encode("latin-1", errors="ignore"))
                    )
            elif m.group(5):
                line = "".join(current_line_parts).strip()
                if line:
                    lines.append(line)
                current_line_parts = []
        tail = "".join(current_line_parts).strip()
        if tail:
            lines.append(tail)
    return lines


def parse_pdf_bytes(filename: str, content: bytes) -> RawExtractedDocument:
    try:
        import pypdf  # type: ignore

        reader = pypdf.PdfReader(io.BytesIO(content))
        pages = [page.extract_text() or "" for page in reader.pages]
        blocks = [p.strip() for p in pages if p.strip()]
        return RawExtractedDocument(filename=filename, file_format="pdf", text_blocks=blocks)
    except ImportError:
        pass

    if not content.lstrip().startswith(b"%PDF"):
        raise ValueError(f"Invalid PDF signature in '{filename}'.")

    extracted_lines: list[str] = []
    for match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", content, flags=re.S):
        raw_stream = match.group(1)
        candidate_streams = [raw_stream]
        try:
            candidate_streams.insert(0, zlib.decompress(raw_stream))
        except zlib.error:
            pass

        for st in candidate_streams:
            lines = _extract_text_from_pdf_stream(st)
            if lines:
                extracted_lines.extend(lines)
                break

    blocks = ["\n".join(extracted_lines)] if extracted_lines else []
    return RawExtractedDocument(
        filename=filename,
        file_format="pdf",
        text_blocks=blocks,
    )

