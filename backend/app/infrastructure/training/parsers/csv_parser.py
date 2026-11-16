"""Local CSV / TSV Question Bank Parser (pure Python stdlib)."""

from __future__ import annotations

import csv
import io

from app.application.training.ports import RawExtractedDocument


def decode_bytes_safely(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def parse_csv_bytes(filename: str, content: bytes) -> RawExtractedDocument:
    text = decode_bytes_safely(content).strip()
    if not text:
        return RawExtractedDocument(filename=filename, file_format="csv")

    sample = "\n".join(text.splitlines()[:5])
    delimiter = ","
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        delimiter = dialect.delimiter
    except csv.Error:
        if "\t" in sample and "," not in sample:
            delimiter = "\t"
        elif ";" in sample and sample.count(";") >= sample.count(","):
            delimiter = ";"

    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    rows: list[dict[str, str]] = []
    for row in reader:
        cleaned = {
            str(k).strip(): ("" if v is None else str(v).strip())
            for k, v in row.items()
            if k is not None
        }
        if any(cleaned.values()):
            rows.append(cleaned)

    return RawExtractedDocument(
        filename=filename,
        file_format="csv",
        table_rows=rows,
    )

