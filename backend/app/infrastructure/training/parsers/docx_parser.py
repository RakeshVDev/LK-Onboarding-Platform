"""Local Word (.docx) Parser (pure Python stdlib OOXML XML + optional python-docx)."""

from __future__ import annotations

import io
import xml.etree.ElementTree as ET
import zipfile

from app.application.training.ports import RawExtractedDocument
from app.infrastructure.training.parsers.excel_parser import _rows_to_dicts


def parse_docx_bytes(filename: str, content: bytes) -> RawExtractedDocument:
    paragraphs: list[str] = []
    table_rows: list[dict[str, str]] = []
    extra_blocks: list[str] = []

    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        if "word/document.xml" not in zf.namelist():
            raise ValueError(f"Invalid .docx package '{filename}': missing word/document.xml")
        root = ET.fromstring(zf.read("word/document.xml"))

    body = next((el for el in root.iter() if el.tag.endswith("}body") or el.tag == "body"), root)

    for child in list(body):
        tag_name = child.tag.split("}")[-1]
        if tag_name == "p":
            parts = [el.text or "" for el in child.iter() if el.tag.endswith("}t") or el.tag == "t"]
            line = "".join(parts).strip()
            if line:
                paragraphs.append(line)
        elif tag_name == "tbl":
            grid: list[list[str]] = []
            for tr in child.iter():
                if tr.tag.endswith("}tr") or tr.tag == "tr":
                    row_cells: list[str] = []
                    for tc in tr:
                        if tc.tag.endswith("}tc") or tc.tag == "tc":
                            cell_parts = [
                                t.text or ""
                                for t in tc.iter()
                                if t.tag.endswith("}t") or t.tag == "t"
                            ]
                            row_cells.append("".join(cell_parts).strip())
                    if any(row_cells):
                        grid.append(row_cells)
            rows, blocks = _rows_to_dicts(grid)
            table_rows.extend(rows)
            extra_blocks.extend(blocks)

    text_blocks = ["\n".join(paragraphs)] if paragraphs else []
    text_blocks.extend(extra_blocks)

    return RawExtractedDocument(
        filename=filename,
        file_format="docx",
        table_rows=table_rows,
        text_blocks=text_blocks,
    )

