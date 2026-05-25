from __future__ import annotations

import json
import re
import zipfile
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET

from .template_engine import HH_NS, HP_NS, StyleSummary, _extract_style_summary


@dataclass
class BlockPrototype:
    block_id: str
    section: str
    index: int
    kind: str
    role: str
    text: str
    char_pr_ids: list[str]
    para_pr_ids: list[str]
    table_attrs: dict[str, str]
    cell_count: int = 0


@dataclass
class SlotCandidate:
    name: str
    role: str
    section: str
    block_id: str
    text: str
    char_pr_id: str
    para_pr_id: str
    score: float
    style: dict = field(default_factory=dict)


@dataclass
class TablePrototype:
    block_id: str
    section: str
    row_count: int
    column_count: int
    header_rows: int
    data_row_index: int
    cell_texts: list[list[str]]
    row_attrs: list[dict[str, str]] = field(default_factory=list)
    cell_attrs: list[list[dict]] = field(default_factory=list)


@dataclass
class LearnedTemplateProfile:
    template_id: str
    filename: str
    section_files: list[str]
    blocks: list[BlockPrototype]
    slots: list[SlotCandidate]
    tables: list[TablePrototype]
    style_summary: StyleSummary

    def to_dict(self) -> dict:
        return asdict(self)


def learn_template_profile(path: str | Path, *, template_id: str | None = None) -> LearnedTemplateProfile:
    source = Path(path)
    with zipfile.ZipFile(source) as zf:
        section_files = sorted(name for name in zf.namelist() if name.startswith("Contents/section") and name.endswith(".xml"))
        if not section_files:
            raise ValueError("HWPX section XML was not found.")
        style_summary = _extract_style_summary(zf, section_files)
        blocks: list[BlockPrototype] = []
        tables: list[TablePrototype] = []
        for section in section_files:
            root = ET.fromstring(zf.read(section))
            section_blocks = _extract_blocks(root, section, start_index=len(blocks))
            blocks.extend(section_blocks)
            tables.extend(_extract_table_prototypes(root, section, section_blocks))

    slots = _detect_slots(blocks, style_summary)
    return LearnedTemplateProfile(
        template_id=template_id or source.stem,
        filename=source.name,
        section_files=section_files,
        blocks=blocks,
        slots=slots,
        tables=tables,
        style_summary=style_summary,
    )


def save_profile(path: str | Path, profile: LearnedTemplateProfile) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(profile.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


def load_profile(path: str | Path) -> LearnedTemplateProfile:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    style_data = data["style_summary"]
    return LearnedTemplateProfile(
        template_id=data["template_id"],
        filename=data["filename"],
        section_files=list(data["section_files"]),
        blocks=[BlockPrototype(**item) for item in data["blocks"]],
        slots=[SlotCandidate(**item) for item in data["slots"]],
        tables=[TablePrototype(**item) for item in data.get("tables", [])],
        style_summary=StyleSummary(**style_data),
    )


def render_profile_markdown(profile: LearnedTemplateProfile) -> str:
    lines = [
        f"# Learned HWPX Template Profile: {profile.filename}",
        "",
        "## Summary",
        "",
        f"- Sections: {', '.join(profile.section_files)}",
        f"- Blocks: {len(profile.blocks)}",
        f"- Slots: {len(profile.slots)}",
        f"- Data tables: {len(profile.tables)}",
        f"- Character styles: {profile.style_summary.char_pr_count}",
        f"- Paragraph styles: {profile.style_summary.para_pr_count}",
        f"- Font face groups: {len(profile.style_summary.font_faces)}",
        f"- Border fills: {profile.style_summary.border_fill_count}",
        f"- Tables: {profile.style_summary.table_count}",
        f"- Section styles: {len(profile.style_summary.section_styles)}",
        "",
        "## Style Profile",
        "",
        "| charPr | Size | Hangul Font | Latin Font | Text Color | Shade | BorderFill |",
        "| --- | ---: | --- | --- | --- | --- | --- |",
    ]
    for char_id, style in sorted(profile.style_summary.char_styles.items(), key=lambda item: _numeric_sort_key(item[0]))[:40]:
        lines.append(
            f"| {char_id} | {style.get('height', '')} | {style.get('fontFaceHangul', '')} | "
            f"{style.get('fontFaceLatin', '')} | {style.get('textColor', '')} | "
            f"{style.get('shadeColor', '')} | {style.get('borderFillIDRef', '')} |"
        )
    lines.extend(
        [
            "",
            "## Paragraph Styles",
            "",
            "| paraPr | Align | Left | Right | Indent | Prev | Next | Line | BorderFill |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for para_id, style in sorted(profile.style_summary.para_styles.items(), key=lambda item: _numeric_sort_key(item[0]))[:40]:
        line_spacing = f"{style.get('lineSpacingType', '')} {style.get('lineSpacingValue', '')}".strip()
        lines.append(
            f"| {para_id} | {style.get('horizontalAlign', '')} | {style.get('marginLeft', '')} | "
            f"{style.get('marginRight', '')} | {style.get('marginIndent', '')} | "
            f"{style.get('marginPrev', '')} | {style.get('marginNext', '')} | "
            f"{line_spacing} | {style.get('borderFillIDRef', '')} |"
        )
    lines.extend(
        [
            "",
            "## Section Styles",
            "",
            "| Section | Landscape | Width | Height | Left | Right | Top | Bottom | Header | Footer | Page Start | Visibility |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for section, style in sorted(profile.style_summary.section_styles.items()):
        page_pr = style.get("pagePr", {})
        margin = style.get("pageMargin", {})
        start_num = style.get("startNum", {})
        visibility = style.get("visibility", {})
        lines.append(
            f"| {section} | {page_pr.get('landscape', '')} | {page_pr.get('width', '')} | "
            f"{page_pr.get('height', '')} | {margin.get('left', '')} | {margin.get('right', '')} | "
            f"{margin.get('top', '')} | {margin.get('bottom', '')} | {margin.get('header', '')} | "
            f"{margin.get('footer', '')} | {start_num.get('page', '')} | {visibility.get('border', '')}/{visibility.get('fill', '')} |"
        )
    lines.extend(
        [
            "",
            "## Slots",
            "",
        "| Name | Role | Block | Score | Font | Size | Align | Text |",
        "| --- | --- | --- | ---: | --- | ---: | --- | --- |",
        ]
    )
    for slot in profile.slots:
        char_style = slot.style.get("char", {}) if isinstance(slot.style, dict) else {}
        para_style = slot.style.get("paragraph", {}) if isinstance(slot.style, dict) else {}
        lines.append(
            f"| {slot.name} | {slot.role} | {slot.block_id} | {slot.score:.2f} | "
            f"{char_style.get('fontFaceHangul', '')} | {char_style.get('height', '')} | "
            f"{para_style.get('horizontalAlign', '')} | {slot.text[:80]} |"
        )
    lines.extend(["", "## Tables", "", "| Block | Rows | Cols | Header Rows | Data Row | Sample |", "| --- | ---: | ---: | ---: | ---: | --- |"])
    for table in profile.tables:
        sample = " / ".join(" | ".join(row[:6]) for row in table.cell_texts[:3])
        lines.append(f"| {table.block_id} | {table.row_count} | {table.column_count} | {table.header_rows} | {table.data_row_index} | {sample[:120]} |")
    lines.extend(["", "## Blocks", "", "| Block | Kind | Role | paraPr | charPr | Text |", "| --- | --- | --- | --- | --- | --- |"])
    for block in profile.blocks[:80]:
        lines.append(
            f"| {block.block_id} | {block.kind} | {block.role} | "
            f"{','.join(block.para_pr_ids) or '-'} | {','.join(block.char_pr_ids) or '-'} | {block.text[:100]} |"
        )
    return "\n".join(lines) + "\n"


def _extract_blocks(root: ET.Element, section: str, *, start_index: int) -> list[BlockPrototype]:
    parent_map = {child: parent for parent in root.iter() for child in parent}
    blocks: list[BlockPrototype] = []
    for elem in root.iter():
        if elem.tag == f"{{{HP_NS}}}tbl":
            text = _node_text(elem)
            block = BlockPrototype(
                block_id=f"b{start_index + len(blocks):04d}",
                section=section,
                index=start_index + len(blocks),
                kind="table",
                role=_classify_block_text(text, is_table=True),
                text=text,
                char_pr_ids=sorted(_unique_run_attr(elem, "charPrIDRef")),
                para_pr_ids=sorted(_unique_para_attr(elem, "paraPrIDRef")),
                table_attrs={key: value for key, value in elem.attrib.items()},
                cell_count=sum(1 for _ in elem.iter(f"{{{HP_NS}}}tc")),
            )
            blocks.append(block)
        elif elem.tag == f"{{{HP_NS}}}p" and _nearest(elem, parent_map, f"{{{HP_NS}}}tbl") is None:
            text = _node_text(elem)
            if not text:
                continue
            block = BlockPrototype(
                block_id=f"b{start_index + len(blocks):04d}",
                section=section,
                index=start_index + len(blocks),
                kind="paragraph",
                role=_classify_block_text(text, is_table=False),
                text=text,
                char_pr_ids=sorted(_unique_run_attr(elem, "charPrIDRef")),
                para_pr_ids=sorted(_unique_para_attr(elem, "paraPrIDRef")),
                table_attrs={},
                cell_count=0,
            )
            blocks.append(block)
    return blocks


def _detect_slots(blocks: list[BlockPrototype], style_summary: StyleSummary) -> list[SlotCandidate]:
    slots: list[SlotCandidate] = []
    if not blocks:
        return slots

    char_usage = Counter(char_id for block in blocks for char_id in block.char_pr_ids)
    content_blocks = [block for block in blocks if block.role in {"title", "section_heading", "body", "attachment", "table"}]

    title = _best_title_block(content_blocks, style_summary, char_usage)
    if title:
        slots.append(_slot("title", "title", title, 0.95, style_summary))

    section_number = 1
    body_number = 1
    table_number = 1
    attachment_number = 1
    for block in content_blocks:
        if title and block.block_id == title.block_id:
            continue
        if block.role == "section_heading":
            slots.append(_slot(f"section_{section_number}", "section_heading", block, 0.85, style_summary))
            section_number += 1
        elif block.role == "attachment":
            slots.append(_slot(f"attachment_{attachment_number}", "attachment", block, 0.75, style_summary))
            attachment_number += 1
        elif block.kind == "table" or block.role == "table":
            slots.append(_slot(f"table_{table_number}", "table", block, 0.70, style_summary))
            table_number += 1
        elif block.role == "body" and body_number <= 20:
            slots.append(_slot(f"body_{body_number}", "body", block, 0.60, style_summary))
            body_number += 1
    return slots


def _best_title_block(blocks: list[BlockPrototype], style_summary: StyleSummary, char_usage: Counter[str]) -> BlockPrototype | None:
    candidates = [block for block in blocks if block.kind == "paragraph" and block.role in {"title", "body", "section_heading"}]
    if not candidates:
        return None
    first_section_index = min((block.index for block in blocks if block.role == "section_heading"), default=10**9)

    def score(block: BlockPrototype) -> tuple[float, int]:
        value = 0.0
        if block.role == "title":
            value += 4.0
        if block.text.startswith(("제목", "건명")):
            value += 5.0
        if block.index < first_section_index:
            value += 1.5
        if block.role == "section_heading" or _looks_like_known_section_heading(block.text):
            value -= 4.0
        if 4 <= len(block.text) <= 80:
            value += 1.0
        for char_id in block.char_pr_ids:
            height = style_summary.char_styles.get(char_id, {}).get("height", "")
            if height.isdigit():
                value += min(int(height) / 1000, 3)
            if char_usage[char_id] <= 2:
                value += 0.5
        return value, -block.index

    return max(candidates, key=score)


def _slot(name: str, role: str, block: BlockPrototype, score: float, style_summary: StyleSummary) -> SlotCandidate:
    char_pr_id = block.char_pr_ids[0] if block.char_pr_ids else ""
    para_pr_id = block.para_pr_ids[0] if block.para_pr_ids else ""
    return SlotCandidate(
        name=name,
        role=role,
        section=block.section,
        block_id=block.block_id,
        text=block.text,
        char_pr_id=char_pr_id,
        para_pr_id=para_pr_id,
        score=score,
        style=_slot_style(block, style_summary, char_pr_id, para_pr_id),
    )


def _slot_style(block: BlockPrototype, style_summary: StyleSummary, char_pr_id: str, para_pr_id: str) -> dict:
    return {
        "charPrIDRef": char_pr_id,
        "paraPrIDRef": para_pr_id,
        "char": dict(style_summary.char_styles.get(char_pr_id, {})),
        "paragraph": dict(style_summary.para_styles.get(para_pr_id, {})),
        "table": dict(block.table_attrs),
    }


def _classify_block_text(text: str, *, is_table: bool) -> str:
    if is_table:
        if _is_metadata_table(text):
            return "metadata_table"
        return "table"
    normalized = text.strip()
    if not normalized:
        return "empty"
    if re.fullmatch(r"(붙임|첨부)\s*.*", normalized):
        return "attachment"
    if re.fullmatch(r"([ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+|[0-9]+)[.．]?\s+.+", normalized) or _looks_like_known_section_heading(normalized):
        return "section_heading"
    if len(normalized) <= 80 and re.search(r"(계획|보고|요청|검토|결과|개선|추진|회의|간담회)", normalized):
        return "title"
    if _is_metadata(normalized):
        return "metadata"
    return "body"


def _extract_table_prototypes(root: ET.Element, section: str, blocks: list[BlockPrototype]) -> list[TablePrototype]:
    table_blocks = [block for block in blocks if block.kind == "table" and block.role == "table"]
    prototypes: list[TablePrototype] = []
    for block, table in zip(table_blocks, [elem for elem in root.iter(f"{{{HP_NS}}}tbl") if not _is_metadata_table(_node_text(elem))]):
        rows = table.findall(f"{{{HP_NS}}}tr")
        cell_texts = [[_node_text(cell) for cell in row.findall(f"{{{HP_NS}}}tc")] for row in rows]
        row_attrs = [dict(row.attrib) for row in rows]
        cell_attrs = [[_cell_style_attrs(cell) for cell in row.findall(f"{{{HP_NS}}}tc")] for row in rows]
        column_count = max((len(row) for row in cell_texts), default=0)
        header_rows = _guess_header_rows(cell_texts)
        prototypes.append(
            TablePrototype(
                block_id=block.block_id,
                section=section,
                row_count=len(rows),
                column_count=column_count,
                header_rows=header_rows,
                data_row_index=min(header_rows, max(0, len(rows) - 1)),
                cell_texts=cell_texts,
                row_attrs=row_attrs,
                cell_attrs=cell_attrs,
            )
        )
    return prototypes


def _guess_header_rows(rows: list[list[str]]) -> int:
    if len(rows) <= 1:
        return 0
    first = " ".join(rows[0])
    if re.search(r"(구분|내용|과제|일정|담당|비고|항목|분야)", first):
        return 1
    return 1


def _is_metadata_table(text: str) -> bool:
    return bool(re.search(r"(등록번호|생산등록번호|문서번호|결재|공개구분|시행일|담\s*당|과\s*장|국\s*장|수신|참조)", text))


def _looks_like_known_section_heading(text: str) -> bool:
    compact = re.sub(r"\s+", "", text)
    headings = {
        "개요",
        "추진배경",
        "추진방향",
        "추진계획",
        "주요내용",
        "향후계획",
        "향후일정",
        "행정사항",
        "목적및추진방향",
        "세부추진계획",
        "추진근거",
        "사업개요",
    }
    return compact in headings


def _is_metadata(text: str) -> bool:
    if len(text) <= 2:
        return True
    if re.search(r"(등록번호|문서번호|결재|공개구분|담당|과장|국장|수신|참조|협조|전화|팩스)", text):
        return True
    if re.fullmatch(r"[\d\s.\-:/()]+", text):
        return True
    return False


def _node_text(elem: ET.Element) -> str:
    return re.sub(r"\s+", " ", " ".join((item.text or "") for item in elem.iter(f"{{{HP_NS}}}t"))).strip()


def _cell_style_attrs(cell: ET.Element) -> dict:
    attrs: dict = dict(cell.attrib)
    for child_name in ("cellAddr", "cellSpan", "cellSz", "cellMargin"):
        child = cell.find(f"{{{HP_NS}}}{child_name}")
        if child is not None:
            attrs[child_name] = dict(child.attrib)
    return attrs


def _numeric_sort_key(value: str) -> tuple[int, str]:
    return (int(value), value) if value.isdigit() else (10**9, value)


def _unique_run_attr(elem: ET.Element, attr: str) -> set[str]:
    return {run.attrib[attr] for run in elem.iter(f"{{{HP_NS}}}run") if attr in run.attrib}


def _unique_para_attr(elem: ET.Element, attr: str) -> set[str]:
    return {para.attrib[attr] for para in elem.iter(f"{{{HP_NS}}}p") if attr in para.attrib}


def _nearest(elem: ET.Element, parent_map: dict[ET.Element, ET.Element], tag: str) -> ET.Element | None:
    current = elem
    while current in parent_map:
        current = parent_map[current]
        if current.tag == tag:
            return current
    return None
