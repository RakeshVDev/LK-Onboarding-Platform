"""Local Excel (.xlsx / .xls) Parser (pure Python stdlib + optional openpyxl/xlrd)."""

from __future__ import annotations

import html
import io
import re
import struct
import xml.etree.ElementTree as ET
import zipfile

from app.application.training.ports import RawExtractedDocument
from app.infrastructure.training.parsers.csv_parser import decode_bytes_safely


def _col_ref_to_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha()).upper()
    idx = 0
    for ch in letters:
        idx = idx * 26 + (ord(ch) - ord("A") + 1)
    return max(0, idx - 1)


def _rows_to_dicts(grid: list[list[str]]) -> tuple[list[dict[str, str]], list[str]]:
    non_empty = [[c.strip() for c in row] for row in grid if any(c.strip() for c in row)]
    if not non_empty:
        return [], []
    header = non_empty[0]
    header_joined = " ".join(header).lower()
    if any(tok in header_joined for tok in ("question", "prompt", "option", "answer", "category", "topic")):
        dicts: list[dict[str, str]] = []
        for row in non_empty[1:]:
            row_dict: dict[str, str] = {}
            for col_i, h_val in enumerate(header):
                if h_val:
                    row_dict[h_val] = row[col_i] if col_i < len(row) else ""
            if any(row_dict.values()):
                dicts.append(row_dict)
        return dicts, []

    blocks = [" | ".join(c for c in row if c) for row in non_empty]
    return [], blocks


def _parse_xlsx_ooxml(content: bytes) -> list[list[str]]:
    grid: list[list[str]] = []
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            sst_root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in sst_root.iter():
                if si.tag.endswith("}si") or si.tag == "si":
                    texts = [el.text or "" for el in si.iter() if el.tag.endswith("}t") or el.tag == "t"]
                    shared_strings.append("".join(texts))

        sheet_names = sorted(
            name for name in zf.namelist()
            if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")
        )
        for sheet in sheet_names:
            root = ET.fromstring(zf.read(sheet))
            for row_el in root.iter():
                if not (row_el.tag.endswith("}row") or row_el.tag == "row"):
                    continue
                row_map: dict[int, str] = {}
                max_col = -1
                for cell_el in row_el:
                    if not (cell_el.tag.endswith("}c") or cell_el.tag == "c"):
                        continue
                    ref = cell_el.attrib.get("r", "")
                    col_idx = _col_ref_to_index(ref) if ref else (max_col + 1)
                    max_col = max(max_col, col_idx)
                    c_type = cell_el.attrib.get("t", "")
                    val = ""
                    if c_type == "inlineStr":
                        val = "".join(
                            t_el.text or ""
                            for t_el in cell_el.iter()
                            if t_el.tag.endswith("}t") or t_el.tag == "t"
                        )
                    else:
                        v_el = next(
                            (ch for ch in cell_el if ch.tag.endswith("}v") or ch.tag == "v"),
                            None,
                        )
                        if v_el is not None and v_el.text is not None:
                            raw_v = v_el.text
                            if c_type == "s":
                                try:
                                    s_idx = int(raw_v)
                                    val = shared_strings[s_idx] if 0 <= s_idx < len(shared_strings) else ""
                                except ValueError:
                                    val = raw_v
                            else:
                                val = raw_v
                    row_map[col_idx] = val
                if row_map:
                    grid.append([row_map.get(c, "") for c in range(max_col + 1)])
    return grid


def _parse_html_or_xml_xls(text: str) -> list[list[str]]:
    grid: list[list[str]] = []
    if "<Row" in text or "<ss:Row" in text:
        try:
            root = ET.fromstring(text)
            for row_el in root.iter():
                if row_el.tag.endswith("}Row") or row_el.tag == "Row":
                    cells = []
                    for cell_el in row_el:
                        if cell_el.tag.endswith("}Cell") or cell_el.tag == "Cell":
                            data_texts = [
                                ch.text or ""
                                for ch in cell_el.iter()
                                if ch.tag.endswith("}Data") or ch.tag == "Data"
                            ]
                            cells.append("".join(data_texts).strip())
                    if cells:
                        grid.append(cells)
            return grid
        except ET.ParseError:
            pass

    if "<tr" in text.lower() and "<td" in text.lower():
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", text, flags=re.I | re.S):
            cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, flags=re.I | re.S)
            cleaned = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in cells]
            if any(cleaned):
                grid.append(cleaned)
    return grid


def _read_ole2_stream(content: bytes, target_names: tuple[str, ...]) -> bytes | None:
    """Minimal pure-Python OLE2 Compound Binary File stream reader for .xls Workbook streams."""
    if len(content) < 512 or content[:8] != b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1":
        return None
    sector_shift = struct.unpack_from("<H", content, 30)[0]
    sector_size = 1 << sector_shift
    dir_start_sector = struct.unpack_from("<I", content, 48)[0]
    difat = [struct.unpack_from("<I", content, 76 + i * 4)[0] for i in range(109)]
    fat: list[int] = []
    for fat_sec in difat:
        if fat_sec in (0xFFFFFFFF, 0xFFFFFFFE):
            continue
        offset = (fat_sec + 1) * sector_size
        if offset + sector_size <= len(content):
            fat.extend(struct.unpack_from(f"<{sector_size // 4}I", content, offset))

    def read_chain(start_sec: int, max_len: int | None = None) -> bytes:
        chunks = bytearray()
        sec = start_sec
        seen: set[int] = set()
        while sec not in (0xFFFFFFFE, 0xFFFFFFFF) and sec not in seen and sec < len(fat):
            seen.add(sec)
            off = (sec + 1) * sector_size
            if off >= len(content):
                break
            chunks.extend(content[off : off + sector_size])
            sec = fat[sec]
            if max_len is not None and len(chunks) >= max_len:
                break
        return bytes(chunks[:max_len]) if max_len is not None else bytes(chunks)

    dir_bytes = read_chain(dir_start_sector)
    for pos in range(0, len(dir_bytes), 128):
        entry = dir_bytes[pos : pos + 128]
        if len(entry) < 128:
            break
        name_len = struct.unpack_from("<H", entry, 64)[0]
        raw_name = entry[: max(0, min(name_len - 2, 64))].decode("utf-16-le", errors="ignore")
        if raw_name in target_names:
            start_sec = struct.unpack_from("<I", entry, 116)[0]
            size = struct.unpack_from("<I", entry, 120)[0]
            return read_chain(start_sec, size)
    return None


def _parse_biff8_workbook(stream: bytes) -> list[list[str]]:
    """Extracts SST strings and LABELSST/LABEL/NUMBER cell values from a BIFF8 Workbook stream."""
    pos = 0
    sst: list[str] = []
    cells: dict[tuple[int, int], str] = {}
    in_sheet = False

    def parse_xl_unicode(buf: bytes, offset: int) -> tuple[str, int]:
        if offset + 3 > len(buf):
            return "", offset
        cch = struct.unpack_from("<H", buf, offset)[0]
        flags = buf[offset + 2]
        idx = offset + 3
        is_16 = bool(flags & 0x01)
        has_ext = bool(flags & 0x04)
        has_rich = bool(flags & 0x08)
        rt_runs = struct.unpack_from("<H", buf, idx)[0] if has_rich else 0
        if has_rich:
            idx += 2
        ext_sz = struct.unpack_from("<I", buf, idx)[0] if has_ext else 0
        if has_ext:
            idx += 4
        byte_len = cch * (2 if is_16 else 1)
        raw = buf[idx : idx + byte_len]
        text = raw.decode("utf-16-le" if is_16 else "latin-1", errors="ignore")
        idx += byte_len + rt_runs * 4 + ext_sz
        return text, idx

    while pos + 4 <= len(stream):
        rec_id, rec_len = struct.unpack_from("<HH", stream, pos)
        data = stream[pos + 4 : pos + 4 + rec_len]
        pos += 4 + rec_len
        if rec_id == 0x0809 and len(data) >= 6:  # BOF
            bof_type = struct.unpack_from("<H", data, 2)[0]
            in_sheet = bof_type == 0x0010
        elif rec_id == 0x000A:  # EOF
            if in_sheet:
                break
        elif rec_id == 0x00FC and len(data) >= 8:  # SST
            cst_unique = struct.unpack_from("<I", data, 4)[0]
            off = 8
            for _ in range(cst_unique):
                s_val, off = parse_xl_unicode(data, off)
                sst.append(s_val)
        elif in_sheet and rec_id == 0x00FD and len(data) >= 10:  # LABELSST
            r, c, _xf, sst_idx = struct.unpack_from("<HHHI", data, 0)
            if sst_idx < len(sst):
                cells[(r, c)] = sst[sst_idx]
        elif in_sheet and rec_id == 0x0204 and len(data) >= 8:  # LABEL
            r, c, _xf = struct.unpack_from("<HHH", data, 0)
            s_val, _ = parse_xl_unicode(data, 6)
            cells[(r, c)] = s_val
        elif in_sheet and rec_id == 0x0203 and len(data) >= 14:  # NUMBER
            r, c, _xf, num = struct.unpack_from("<HHHd", data, 0)
            cells[(r, c)] = str(int(num) if num.is_integer() else num)

    if not cells:
        return []
    max_r = max(r for r, _ in cells)
    max_c = max(c for _, c in cells)
    return [[cells.get((r, c), "") for c in range(max_c + 1)] for r in range(max_r + 1)]


def parse_excel_bytes(filename: str, content: bytes) -> RawExtractedDocument:
    ext = "xlsx" if filename.lower().endswith(".xlsx") else "xls"
    grid: list[list[str]] = []

    if ext == "xlsx":
        try:
            grid = _parse_xlsx_ooxml(content)
        except Exception as exc:
            raise ValueError(f"Unable to read .xlsx workbook '{filename}': {exc}") from exc
    else:
        # Try xlrd if installed, else OLE2 BIFF8, else HTML/XML .xls export, else delimiter text
        try:
            import xlrd  # type: ignore

            wb = xlrd.open_workbook(file_contents=content)
            for sheet in wb.sheets():
                for r in range(sheet.nrows):
                    grid.append([str(sheet.cell_value(r, c)) for c in range(sheet.ncols)])
        except ImportError:
            ole_stream = _read_ole2_stream(content, ("Workbook", "Book"))
            if ole_stream:
                grid = _parse_biff8_workbook(ole_stream)
            else:
                decoded = decode_bytes_safely(content)
                grid = _parse_html_or_xml_xls(decoded)
                if not grid and ("\t" in decoded or "," in decoded):
                    sep = "\t" if "\t" in decoded else ","
                    grid = [line.split(sep) for line in decoded.splitlines() if line.strip()]

    table_rows, text_blocks = _rows_to_dicts(grid)
    return RawExtractedDocument(
        filename=filename,
        file_format=ext,
        table_rows=table_rows,
        text_blocks=text_blocks,
    )

