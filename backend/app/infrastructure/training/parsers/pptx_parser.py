"""Local PowerPoint (.pptx) Parser (pure Python stdlib OOXML XML)."""

from __future__ import annotations

import io
import re
import xml.etree.ElementTree as ET
import zipfile

from app.application.training.ports import RawExtractedDocument
from app.infrastructure.training.parsers.excel_parser import _rows_to_dicts


def _slide_sort_key(path: str) -> int:
    m = re.search(r"slide(\d+)\.xml$", path)
    return int(m.group(1)) if m else 0


def parse_pptx_bytes(filename: str, content: bytes) -> RawExtractedDocument:
    slide_blocks: list[str] = []
    table_rows: list[dict[str, str]] = []

    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        slide_files = sorted(
            (name for name in zf.namelist() if re.match(r"^ppt/slides/slide\d+\.xml$", name)),
            key=_slide_sort_key,
        )
        if not slide_files:
            raise ValueError(f"Invalid .pptx archive '{filename}': no slides found")

        for s_path in slide_files:
            root = ET.fromstring(zf.read(s_path))
            slide_lines: list[str] = []

            for el in root.iter():
                if el.tag.endswith("}p") or el.tag == "p":
                    runs = [t.text or "" for t in el.iter() if t.tag.endswith("}t") or t.tag == "t"]
                    line = "".join(runs).strip()
                    if line:
                        slide_lines.append(line)
                elif el.tag.endswith("}tbl") or el.tag == "tbl":
                    grid: list[list[str]] = []
                    for tr in el:
                        if tr.tag.endswith("}tr") or tr.tag == "tr":
                            row_cells = []
                            for tc in tr:
                                if tc.tag.endswith("}tc") or tc.tag == "tc":
                                    cell_runs = [
                                        t.text or ""
                                        for t in tc.iter()
                                        if t.tag.endswith("}t") or t.tag == "t"
                                    ]
                                    row_cells.append("".join(cell_runs).strip())
                            if any(row_cells):
                                grid.append(row_cells)
                    rows, _ = _rows_to_dicts(grid)
                    table_rows.extend(rows)

            if slide_lines:
                slide_blocks.append("\n".join(slide_lines))

    return RawExtractedDocument(
        filename=filename,
        file_format="pptx",
        table_rows=table_rows,
        text_blocks=slide_blocks,
    )

