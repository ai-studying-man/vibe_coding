from __future__ import annotations

import copy
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

from .hwpx import verify_hwpx
from .template_engine import DraftContent, HP_NS
from .template_profile import LearnedTemplateProfile, SlotCandidate, TablePrototype


@dataclass
class FillReport:
    title_slot: str
    body_slots: list[str]
    attachment_slots: list[str]
    table_slots: list[str]
    appended_blocks: int


def fill_hwpx_with_profile(
    template_path: str | Path,
    output_path: str | Path,
    draft: DraftContent,
    profile: LearnedTemplateProfile,
) -> FillReport:
    source = Path(template_path)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    report = FillReport(title_slot="", body_slots=[], attachment_slots=[], table_slots=[], appended_blocks=0)
    with zipfile.ZipFile(source, "r") as src, zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            data = src.read(info.filename)
            if info.filename in profile.section_files:
                root = ET.fromstring(data)
                _fill_section(root, info.filename, draft, profile, report)
                data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
            elif info.filename == "Preview/PrvText.txt":
                data = _preview_text(draft).encode("utf-16le")
            dst.writestr(info, data)

    verify_hwpx(output)
    return report


def _fill_section(
    root: ET.Element,
    section: str,
    draft: DraftContent,
    profile: LearnedTemplateProfile,
    report: FillReport,
) -> None:
    element_by_block = _map_block_elements(root, section, profile)
    slots = [slot for slot in profile.slots if slot.section == section]

    title_slot = next((slot for slot in slots if slot.role == "title"), None)
    if title_slot and title_slot.block_id in element_by_block:
        _replace_block_text(element_by_block[title_slot.block_id], draft.title)
        report.title_slot = title_slot.block_id

    body_slots = [slot for slot in slots if slot.role == "body" and slot.block_id in element_by_block]
    for slot, paragraph in zip(body_slots, draft.paragraphs):
        _replace_block_text(element_by_block[slot.block_id], paragraph)
        report.body_slots.append(slot.block_id)

    remaining = draft.paragraphs[len(body_slots) :]
    if remaining and body_slots:
        anchor = element_by_block[body_slots[-1].block_id]
        report.appended_blocks += _append_after(root, anchor, remaining)

    attachment_slots = [slot for slot in slots if slot.role == "attachment" and slot.block_id in element_by_block]
    attachment_text = _attachment_text(draft)
    if attachment_text and attachment_slots:
        _replace_block_text(element_by_block[attachment_slots[0].block_id], attachment_text)
        report.attachment_slots.append(attachment_slots[0].block_id)

    _fill_tables(element_by_block, slots, draft, profile, report)


def _map_block_elements(
    root: ET.Element,
    section: str,
    profile: LearnedTemplateProfile | None = None,
) -> dict[str, ET.Element]:
    parent_map = {child: parent for parent in root.iter() for child in parent}
    known_block_ids = [block.block_id for block in profile.blocks if block.section == section] if profile else []
    blocks: dict[str, ET.Element] = {}
    index = 0
    for elem in root.iter():
        if elem.tag == f"{{{HP_NS}}}tbl":
            block_id = known_block_ids[index] if index < len(known_block_ids) else f"b{index:04d}"
            blocks[block_id] = elem
            index += 1
        elif elem.tag == f"{{{HP_NS}}}p" and _nearest(elem, parent_map, f"{{{HP_NS}}}tbl") is None:
            if _block_text(elem):
                block_id = known_block_ids[index] if index < len(known_block_ids) else f"b{index:04d}"
                blocks[block_id] = elem
                index += 1
    return blocks


def _fill_tables(
    element_by_block: dict[str, ET.Element],
    slots: list[SlotCandidate],
    draft: DraftContent,
    profile: LearnedTemplateProfile,
    report: FillReport,
) -> None:
    table_slots = [slot for slot in slots if slot.role == "table" and slot.block_id in element_by_block]
    available = table_slots[:]
    for rows in draft.tables:
        if not rows or not available:
            continue
        slot = _best_table_slot(rows, available, profile)
        available.remove(slot)
        prototype = _table_prototype(profile, slot.block_id)
        normalized_rows = _strip_input_header(rows, prototype)
        if not normalized_rows:
            continue
        _fill_table(element_by_block[slot.block_id], normalized_rows, profile, slot.block_id)
        report.table_slots.append(slot.block_id)


def _best_table_slot(
    rows: list[list[str]],
    slots: list[SlotCandidate],
    profile: LearnedTemplateProfile,
) -> SlotCandidate:
    return max(slots, key=lambda slot: _table_match_score(rows, _table_prototype(profile, slot.block_id)))


def _table_match_score(rows: list[list[str]], prototype: TablePrototype | None) -> float:
    if prototype is None:
        return 0.0
    input_columns = _max_column_count(rows)
    score = 0.0
    if input_columns and prototype.column_count:
        score += max(0.0, 4.0 - abs(input_columns - prototype.column_count))
        if input_columns == prototype.column_count:
            score += 2.0
    score += _header_similarity(rows[0] if rows else [], prototype) * 3.0
    if len(rows) >= max(1, prototype.row_count - prototype.header_rows):
        score += 0.5
    return score


def _strip_input_header(rows: list[list[str]], prototype: TablePrototype | None) -> list[list[str]]:
    if len(rows) <= 1 or prototype is None or prototype.header_rows <= 0:
        return rows
    first_row = rows[0]
    if _header_similarity(first_row, prototype) >= 0.35 or _looks_like_input_header(first_row):
        return rows[1:]
    return rows


def _table_prototype(profile: LearnedTemplateProfile, block_id: str) -> TablePrototype | None:
    return next((item for item in profile.tables if item.block_id == block_id), None)


def _header_similarity(row: list[str], prototype: TablePrototype) -> float:
    header_rows = prototype.cell_texts[: prototype.header_rows]
    prototype_tokens = {_normalize_label(cell) for header in header_rows for cell in header}
    input_tokens = {_normalize_label(cell) for cell in row}
    prototype_tokens.discard("")
    input_tokens.discard("")
    if not prototype_tokens or not input_tokens:
        return 0.0
    exact = len(prototype_tokens & input_tokens) / max(len(prototype_tokens), len(input_tokens))
    partial = 0
    for input_token in input_tokens:
        if any(input_token in token or token in input_token for token in prototype_tokens):
            partial += 1
    return max(exact, partial / max(len(input_tokens), len(prototype_tokens)))


def _looks_like_input_header(row: list[str]) -> bool:
    labels = {
        "task",
        "content",
        "date",
        "item",
        "name",
        "amount",
        "category",
        "division",
        "owner",
        "department",
        "note",
        "remark",
        "status",
    }
    tokens = [_normalize_label(cell) for cell in row if _normalize_label(cell)]
    if not tokens:
        return False
    matched = sum(1 for token in tokens if token in labels)
    return matched >= max(1, len(tokens) // 2)


def _normalize_label(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣]+", "", str(value)).lower()


def _max_column_count(rows: list[list[str]]) -> int:
    return max((len(row) for row in rows), default=0)


def _fill_table(table: ET.Element, rows: list[list[str]], profile: LearnedTemplateProfile, block_id: str) -> None:
    if not rows:
        return
    prototype = next((item for item in profile.tables if item.block_id == block_id), None)
    table_rows = table.findall(f"{{{HP_NS}}}tr")
    if not table_rows:
        return
    header_rows = prototype.header_rows if prototype else 1
    data_row_index = prototype.data_row_index if prototype else min(header_rows, len(table_rows) - 1)
    data_row_index = min(max(0, data_row_index), len(table_rows) - 1)
    template_row = table_rows[data_row_index]

    for row in table_rows[header_rows:]:
        table.remove(row)

    insert_at = _first_row_index(table) + header_rows
    for row_values in rows:
        clone = copy.deepcopy(template_row)
        _fill_row(clone, row_values)
        table.insert(insert_at, clone)
        insert_at += 1
    table.attrib["rowCnt"] = str(header_rows + len(rows))


def _fill_row(row: ET.Element, values: list[str]) -> None:
    cells = row.findall(f"{{{HP_NS}}}tc")
    for cell, value in zip(cells, values):
        _replace_block_text(cell, str(value))
    for cell in cells[len(values) :]:
        _replace_block_text(cell, "")


def _first_row_index(table: ET.Element) -> int:
    for index, child in enumerate(list(table)):
        if child.tag == f"{{{HP_NS}}}tr":
            return index
    return len(list(table))


def _replace_block_text(block: ET.Element, value: str) -> None:
    first = True
    for elem in block.iter(f"{{{HP_NS}}}t"):
        elem.text = value if first else ""
        first = False


def _append_after(root: ET.Element, anchor: ET.Element, values: list[str]) -> int:
    root_children = list(root)
    if anchor not in root_children:
        return 0
    insert_at = root_children.index(anchor) + 1
    count = 0
    for value in values:
        clone = copy.deepcopy(anchor)
        _replace_block_text(clone, value)
        root.insert(insert_at, clone)
        insert_at += 1
        count += 1
    return count


def _attachment_text(draft: DraftContent) -> str:
    if not draft.attachments:
        return ""
    return "붙임  " + ", ".join(draft.attachments)


def _preview_text(draft: DraftContent) -> str:
    lines = [draft.title, *draft.paragraphs]
    attachment = _attachment_text(draft)
    if attachment:
        lines.append(attachment)
    return "\n".join(line for line in lines if line)


def _block_text(elem: ET.Element) -> str:
    return " ".join((item.text or "").strip() for item in elem.iter(f"{{{HP_NS}}}t") if (item.text or "").strip()).strip()


def _nearest(elem: ET.Element, parent_map: dict[ET.Element, ET.Element], tag: str) -> ET.Element | None:
    current = elem
    while current in parent_map:
        current = parent_map[current]
        if current.tag == tag:
            return current
    return None
