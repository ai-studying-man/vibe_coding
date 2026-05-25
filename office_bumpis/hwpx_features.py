from __future__ import annotations

import copy
import json
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET

from .hwpx import verify_hwpx
from .standard_features import normalize_whitespace
from .template_engine import HH_NS, HP_NS


HC_NS = "http://www.hancom.co.kr/hwpml/2011/core"
LANG_ATTRS = ("hangul", "latin", "hanja", "japanese", "other", "symbol", "user")

ET.register_namespace("hp", HP_NS)
ET.register_namespace("hh", HH_NS)
ET.register_namespace("hc", HC_NS)


@dataclass
class FeatureOperation:
    key: str
    params: dict[str, object] = field(default_factory=dict)


def apply_standard_features(
    input_path: str | Path,
    output_path: str | Path,
    operations: list[FeatureOperation | dict[str, object] | str],
) -> Path:
    source = Path(input_path)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    normalized_ops = [_normalize_operation(item) for item in operations]

    with zipfile.ZipFile(source, "r") as src:
        entries = [(info, src.read(info.filename)) for info in src.infolist()]

    header_root: ET.Element | None = None
    section_roots: dict[str, ET.Element] = {}
    for info, data in entries:
        if info.filename == "Contents/header.xml":
            header_root = ET.fromstring(data)
        elif info.filename.startswith("Contents/section") and info.filename.endswith(".xml"):
            section_roots[info.filename] = ET.fromstring(data)

    for operation in normalized_ops:
        _apply_operation(operation, header_root, section_roots)

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as dst:
        for info, data in entries:
            if info.filename == "Contents/header.xml" and header_root is not None:
                data = ET.tostring(header_root, encoding="utf-8", xml_declaration=True)
            elif info.filename in section_roots:
                data = ET.tostring(section_roots[info.filename], encoding="utf-8", xml_declaration=True)
            dst.writestr(info, data)

    verify_hwpx(output)
    return output


def _normalize_operation(item: FeatureOperation | dict[str, object] | str) -> FeatureOperation:
    if isinstance(item, FeatureOperation):
        return item
    if isinstance(item, str):
        return FeatureOperation(item, {})
    params = dict(item.get("params", {})) if isinstance(item.get("params", {}), dict) else {}
    for key, value in item.items():
        if key not in {"key", "params"}:
            params[key] = value
    return FeatureOperation(str(item["key"]), params)


def _apply_operation(operation: FeatureOperation, header_root: ET.Element | None, section_roots: dict[str, ET.Element]) -> None:
    key = operation.key
    params = operation.params
    if key == "cleanup_whitespace":
        _apply_text_cleanup(section_roots, remove_empty_lines=False)
    elif key == "remove_empty_lines":
        _apply_text_cleanup(section_roots, remove_empty_lines=True)
    elif key == "font_color":
        _require_header(header_root)
        char_id = _create_char_style(header_root, textColor=_normalize_color(params.get("color", "#000000")))
        _apply_char_style(section_roots, char_id)
    elif key == "font_size":
        _require_header(header_root)
        height = str(int(float(params.get("points", 12)) * 100))
        char_id = _create_char_style(header_root, height=height)
        _apply_char_style(section_roots, char_id)
    elif key == "font_family":
        _require_header(header_root)
        font_refs = _font_refs_for_family(header_root, params)
        char_id = _create_char_style(header_root, fontRefs=font_refs)
        _apply_char_style(section_roots, char_id)
    elif key == "strike_or_underline":
        _require_header(header_root)
        char_id = _create_char_style(
            header_root,
            underline=bool(params.get("underline", True)),
            strike=bool(params.get("strike", False)),
        )
        _apply_char_style(section_roots, char_id)
    elif key == "text_background":
        _require_header(header_root)
        char_id = _create_char_style(header_root, shadeColor=_normalize_color(params.get("color", "#FFF2CC")))
        _apply_char_style(section_roots, char_id)
    elif key == "character_emphasis":
        _require_header(header_root)
        char_id = _create_char_style(
            header_root,
            bold=None if "bold" not in params else bool(params.get("bold")),
            italic=None if "italic" not in params else bool(params.get("italic")),
            normal=bool(params.get("normal", False)),
        )
        _apply_char_style(section_roots, char_id)
    elif key == "superscript_subscript":
        _require_header(header_root)
        char_id = _create_char_style(header_root, supscript=_normalize_script_type(params.get("type", params.get("script", "SUPERSCRIPT"))))
        _apply_char_style(section_roots, char_id)
    elif key == "character_spacing":
        _require_header(header_root)
        char_id = _create_char_style(header_root, spacing=str(params.get("spacing", params.get("value", "5"))))
        _apply_char_style(section_roots, char_id)
    elif key == "character_width":
        _require_header(header_root)
        char_id = _create_char_style(header_root, ratio=str(params.get("ratio", params.get("value", "100"))))
        _apply_char_style(section_roots, char_id)
    elif key == "character_shadow":
        _require_header(header_root)
        char_id = _create_char_style(header_root, shadow=params)
        _apply_char_style(section_roots, char_id)
    elif key == "table_background":
        _require_header(header_root)
        border_id = _create_border_fill(
            header_root,
            fill_color=_normalize_color(params.get("color", "#F2F2F2")),
            remove_fill=bool(params.get("remove", False)),
        )
        _apply_cell_border_fill(section_roots, border_id)
    elif key == "transparent_table":
        _require_header(header_root)
        border_id = _create_border_fill(header_root, border_type="NONE", fill_color="none", remove_fill=True)
        _apply_cell_border_fill(section_roots, border_id)
    elif key == "table_border":
        _require_header(header_root)
        border_id = _create_border_fill(
            header_root,
            border_type=str(params.get("type", "SOLID")),
            border_width=str(params.get("width", "0.1 mm")),
            border_color=_normalize_color(params.get("color", "#000000")),
        )
        _apply_cell_border_fill(section_roots, border_id)
    elif key == "paragraph_alignment":
        _require_header(header_root)
        para_id = _create_para_style(header_root, horizontal=str(params.get("horizontal", "CENTER")))
        _apply_para_style(section_roots, para_id)
    elif key == "paragraph_spacing":
        _require_header(header_root)
        para_id = _create_para_style(
            header_root,
            line_spacing_type=str(params.get("line_spacing_type", "PERCENT")),
            line_spacing_value=str(params.get("line_spacing_value", params.get("lineSpacing", "160"))),
            margin_left=str(params.get("left", params.get("margin_left", "0"))),
            margin_right=str(params.get("right", params.get("margin_right", "0"))),
        )
        _apply_para_style(section_roots, para_id)
    elif key == "page_layout":
        _apply_page_layout(section_roots, params)
    elif key == "page_border":
        _require_header(header_root)
        _apply_page_border(header_root, section_roots, params)
    elif key == "table_dimensions":
        _apply_table_dimensions(section_roots, params)
    elif key == "table_sort":
        _apply_table_sort(
            section_roots,
            numeric=bool(params.get("numeric", False)),
            descending=bool(params.get("descending", False)),
            header_rows=int(params.get("header_rows", 1)),
        )
    elif key == "table_merge_split":
        _apply_table_merge_split(
            section_roots,
            mode=str(params.get("mode", "merge")),
            rows=int(params.get("rows", 1)),
            cols=int(params.get("cols", 2)),
        )
    elif key == "table_rows":
        _apply_table_rows(section_roots, params)
    elif key == "table_columns":
        _apply_table_columns(section_roots, params)
    elif key == "numeric_calculation":
        _apply_numeric_calculation(section_roots)
    elif key == "document_blocks":
        _apply_document_blocks(section_roots, params)
    elif key == "control_characters":
        _apply_control_characters(section_roots, params)
    elif key == "page_break":
        _apply_page_break(section_roots, params)
    elif key == "page_number":
        _apply_page_number(section_roots, params)
    else:
        raise ValueError(f"Unsupported standard feature: {key}")


def _apply_text_cleanup(section_roots: dict[str, ET.Element], *, remove_empty_lines: bool) -> None:
    for root in section_roots.values():
        for elem in root.iter(f"{{{HP_NS}}}t"):
            if elem.text:
                elem.text = normalize_whitespace(elem.text, remove_empty_lines=remove_empty_lines)


def _create_char_style(header_root: ET.Element, **updates: object) -> str:
    collection = _find_required(header_root, f"{{{HH_NS}}}charProperties", "charProperties")
    source = next(header_root.iter(f"{{{HH_NS}}}charPr"), None)
    if source is None:
        source = _default_char_pr()
    clone = copy.deepcopy(source)
    new_id = str(_next_numeric_id(collection, f"{{{HH_NS}}}charPr"))
    clone.attrib["id"] = new_id
    for key, value in updates.items():
        if key == "underline":
            _set_underline(clone, enabled=bool(value))
        elif key == "strike":
            _set_strikeout(clone, enabled=bool(value))
        elif key == "bold":
            if value is not None:
                _set_empty_style_child(clone, "bold", enabled=bool(value))
        elif key == "italic":
            if value is not None:
                _set_empty_style_child(clone, "italic", enabled=bool(value))
        elif key == "normal":
            if value:
                _set_normal_char_style(clone)
        elif key == "supscript":
            _set_supscript(clone, str(value))
        elif key == "spacing":
            _set_language_attrs(_ensure_child(clone, f"{{{HH_NS}}}spacing"), str(value))
        elif key == "ratio":
            _set_language_attrs(_ensure_child(clone, f"{{{HH_NS}}}ratio"), str(value))
        elif key == "shadow":
            _set_shadow(clone, value if isinstance(value, dict) else {})
        elif key == "fontRefs":
            _set_font_refs(clone, value if isinstance(value, dict) else {})
        elif value is not None:
            clone.attrib[key] = str(value)
    collection.append(clone)
    collection.attrib["itemCnt"] = str(len(list(collection.iter(f"{{{HH_NS}}}charPr"))))
    return new_id


def _create_border_fill(
    header_root: ET.Element,
    *,
    border_type: str | None = None,
    border_width: str | None = None,
    border_color: str | None = None,
    fill_color: str | None = None,
    remove_fill: bool = False,
) -> str:
    collection = _find_required(header_root, f"{{{HH_NS}}}borderFills", "borderFills")
    source = next(header_root.iter(f"{{{HH_NS}}}borderFill"), None)
    clone = copy.deepcopy(source) if source is not None else _default_border_fill()
    new_id = str(_next_numeric_id(collection, f"{{{HH_NS}}}borderFill"))
    clone.attrib["id"] = new_id

    for name in ["leftBorder", "rightBorder", "topBorder", "bottomBorder", "diagonal"]:
        border = _ensure_child(clone, f"{{{HH_NS}}}{name}")
        if border_type:
            border.attrib["type"] = border_type
        if border_width:
            border.attrib["width"] = border_width
        if border_color:
            border.attrib["color"] = border_color

    if remove_fill:
        _remove_fill(clone)
    elif fill_color:
        _set_fill(clone, fill_color)

    collection.append(clone)
    collection.attrib["itemCnt"] = str(len(list(collection.iter(f"{{{HH_NS}}}borderFill"))))
    return new_id


def _create_para_style(header_root: ET.Element, **updates: object) -> str:
    collection = _find_required(header_root, f"{{{HH_NS}}}paraProperties", "paraProperties")
    source = next(header_root.iter(f"{{{HH_NS}}}paraPr"), None)
    if source is None:
        source = _default_para_pr()
    clone = copy.deepcopy(source)
    new_id = str(_next_numeric_id(collection, f"{{{HH_NS}}}paraPr"))
    clone.attrib["id"] = new_id

    horizontal = updates.get("horizontal")
    if horizontal:
        align = _ensure_child(clone, f"{{{HH_NS}}}align")
        align.attrib["horizontal"] = str(horizontal).upper()
        align.attrib.setdefault("vertical", "BASELINE")

    line_spacing_value = updates.get("line_spacing_value")
    if line_spacing_value is not None:
        line_spacing = _ensure_child(clone, f"{{{HH_NS}}}lineSpacing")
        line_spacing.attrib["type"] = str(updates.get("line_spacing_type") or "PERCENT")
        line_spacing.attrib["value"] = str(line_spacing_value)

    if updates.get("margin_left") is not None or updates.get("margin_right") is not None:
        margin = _ensure_child(clone, f"{{{HH_NS}}}margin")
        margin.attrib["left"] = str(updates.get("margin_left") or "0")
        margin.attrib["right"] = str(updates.get("margin_right") or "0")
        margin.attrib.setdefault("indent", "0")
        margin.attrib.setdefault("prev", "0")
        margin.attrib.setdefault("next", "0")

    collection.append(clone)
    collection.attrib["itemCnt"] = str(len(list(collection.iter(f"{{{HH_NS}}}paraPr"))))
    return new_id


def _apply_char_style(section_roots: dict[str, ET.Element], char_id: str) -> None:
    for root in section_roots.values():
        parent_map = {child: parent for parent in root.iter() for child in parent}
        target_runs = []
        for text in root.iter(f"{{{HP_NS}}}t"):
            if text.text and text.text.strip():
                run = _nearest(text, parent_map, f"{{{HP_NS}}}run")
                if run is not None:
                    target_runs.append(run)
        for run in target_runs:
            run.attrib["charPrIDRef"] = char_id


def _apply_para_style(section_roots: dict[str, ET.Element], para_id: str) -> None:
    for root in section_roots.values():
        for paragraph in root.iter(f"{{{HP_NS}}}p"):
            if any(text.text and text.text.strip() for text in paragraph.iter(f"{{{HP_NS}}}t")):
                paragraph.attrib["paraPrIDRef"] = para_id


def _apply_cell_border_fill(section_roots: dict[str, ET.Element], border_id: str) -> None:
    for root in section_roots.values():
        for cell in root.iter(f"{{{HP_NS}}}tc"):
            cell.attrib["borderFillIDRef"] = border_id


def _apply_page_layout(section_roots: dict[str, ET.Element], params: dict[str, object]) -> None:
    for root in section_roots.values():
        for page_pr in root.iter(f"{{{HP_NS}}}pagePr"):
            orientation = params.get("orientation", params.get("landscape"))
            if orientation is not None:
                page_pr.attrib["landscape"] = _normalize_orientation(orientation)
            if params.get("width") is not None:
                page_pr.attrib["width"] = _layout_value(params["width"], params)
            if params.get("height") is not None:
                page_pr.attrib["height"] = _layout_value(params["height"], params)

            margin = _ensure_child(page_pr, f"{{{HP_NS}}}margin")
            margin_defaults = params.get("margin")
            margin_attrs = {
                "left": params.get("left", params.get("margin_left", margin_defaults)),
                "right": params.get("right", params.get("margin_right", margin_defaults)),
                "top": params.get("top", params.get("margin_top", margin_defaults)),
                "bottom": params.get("bottom", params.get("margin_bottom", margin_defaults)),
                "header": params.get("header", params.get("header_len")),
                "footer": params.get("footer", params.get("footer_len")),
                "gutter": params.get("gutter"),
            }
            for key, value in margin_attrs.items():
                if value is not None:
                    margin.attrib[key] = _layout_value(value, params)


def _apply_page_border(header_root: ET.Element, section_roots: dict[str, ET.Element], params: dict[str, object]) -> None:
    remove = bool(params.get("remove", False))
    border_id = _create_border_fill(
        header_root,
        border_type="NONE" if remove else str(params.get("type", params.get("border_type", "SOLID"))),
        border_width=str(params.get("width", params.get("border_width", "0.1 mm"))),
        border_color=_normalize_color(params.get("color", params.get("border_color", "#000000"))),
        remove_fill=True,
    )
    for root in section_roots.values():
        for page_border in root.iter(f"{{{HP_NS}}}pageBorderFill"):
            page_border.attrib["borderFillIDRef"] = border_id
            if params.get("text_border") is not None:
                page_border.attrib["textBorder"] = str(params["text_border"])
            if params.get("fill_area") is not None:
                page_border.attrib["fillArea"] = str(params["fill_area"])
            for key, param_key in [("headerInside", "header_inside"), ("footerInside", "footer_inside")]:
                if params.get(param_key) is not None:
                    page_border.attrib[key] = "1" if _truthy(params[param_key]) else "0"
            offset = _ensure_child(page_border, f"{{{HP_NS}}}offset")
            default_offset = params.get("offset")
            for key in ["left", "right", "top", "bottom"]:
                value = params.get(key, params.get(f"offset_{key}", default_offset))
                if value is not None:
                    offset.attrib[key] = _layout_value(value, params)


def _apply_table_dimensions(section_roots: dict[str, ET.Element], params: dict[str, object]) -> None:
    width = params.get("cell_width")
    height = params.get("cell_height")
    margin = params.get("margin")
    margin_attrs = {
        "left": params.get("margin_left", margin),
        "right": params.get("margin_right", margin),
        "top": params.get("margin_top", margin),
        "bottom": params.get("margin_bottom", margin),
    }
    for root in section_roots.values():
        for table in root.iter(f"{{{HP_NS}}}tbl"):
            if params.get("cell_spacing") is not None:
                table.attrib["cellSpacing"] = str(params["cell_spacing"])
            if params.get("no_adjust") is not None:
                table.attrib["noAdjust"] = "1" if bool(params["no_adjust"]) else "0"
            for cell in table.iter(f"{{{HP_NS}}}tc"):
                if width is not None or height is not None:
                    size = _ensure_child(cell, f"{{{HP_NS}}}cellSz")
                    if width is not None:
                        size.attrib["width"] = str(width)
                    if height is not None:
                        size.attrib["height"] = str(height)
                if any(value is not None for value in margin_attrs.values()):
                    cell.attrib["hasMargin"] = "1"
                    cell_margin = _ensure_child(cell, f"{{{HP_NS}}}cellMargin")
                    for key, value in margin_attrs.items():
                        if value is not None:
                            cell_margin.attrib[key] = str(value)


def _apply_table_sort(section_roots: dict[str, ET.Element], *, numeric: bool, descending: bool, header_rows: int) -> None:
    for root in section_roots.values():
        for table in root.iter(f"{{{HP_NS}}}tbl"):
            rows = list(table.findall(f"{{{HP_NS}}}tr"))
            if len(rows) < 2:
                continue
            header_part, sortable_rows = _split_header_rows(rows, header_rows=header_rows)
            sortable_rows.sort(key=lambda row: _row_sort_key(row, numeric=numeric), reverse=descending)
            _replace_rows(table, header_part + sortable_rows)


def _apply_table_merge_split(section_roots: dict[str, ET.Element], *, mode: str, rows: int, cols: int) -> None:
    for root in section_roots.values():
        table = next(root.iter(f"{{{HP_NS}}}tbl"), None)
        if table is None:
            continue
        if mode == "split":
            for span in table.iter(f"{{{HP_NS}}}cellSpan"):
                span.attrib["colSpan"] = "1"
                span.attrib["rowSpan"] = "1"
            return
        _merge_from_top_left(table, max(1, rows), max(1, cols))
        return


def _apply_table_rows(section_roots: dict[str, ET.Element], params: dict[str, object]) -> None:
    tables = [table for root in section_roots.values() for table in root.iter(f"{{{HP_NS}}}tbl")]
    if not tables:
        return
    if not _truthy(params.get("all_tables", False)):
        tables = tables[:1]

    mode = str(params.get("mode", "append")).strip().lower()
    count = max(1, int(params.get("count", 1)))
    header_rows = max(0, int(params.get("header_rows", 1)))
    values = _normalize_table_row_values(params.get("values", params.get("row_values")))

    for table in tables:
        if mode in {"delete", "remove", "drop"}:
            _delete_table_rows(table, count=count, header_rows=header_rows)
        else:
            _append_table_rows(table, count=count, values=values)
        _renumber_table_rows(table)


def _apply_table_columns(section_roots: dict[str, ET.Element], params: dict[str, object]) -> None:
    tables = [table for root in section_roots.values() for table in root.iter(f"{{{HP_NS}}}tbl")]
    if not tables:
        return
    if not _truthy(params.get("all_tables", False)):
        tables = tables[:1]

    mode = str(params.get("mode", "append")).strip().lower()
    position = str(params.get("position", params.get("side", "right"))).strip().lower()
    count = max(1, int(params.get("count", 1)))
    values = _normalize_table_column_values(params.get("values", params.get("column_values")))

    for table in tables:
        if mode in {"delete", "remove", "drop"}:
            _delete_table_columns(table, count=count, position=position)
        else:
            _append_table_columns(table, count=count, values=values, position=position)
        _renumber_table_rows(table)


def _merge_from_top_left(table: ET.Element, rows: int, cols: int) -> None:
    table_rows = table.findall(f"{{{HP_NS}}}tr")
    if not table_rows:
        return
    first_row_cells = table_rows[0].findall(f"{{{HP_NS}}}tc")
    if not first_row_cells:
        return
    anchor = first_row_cells[0]
    span = _ensure_child(anchor, f"{{{HP_NS}}}cellSpan")
    span.attrib["rowSpan"] = str(rows)
    span.attrib["colSpan"] = str(cols)

    for row_index, row in enumerate(table_rows[:rows]):
        cells = row.findall(f"{{{HP_NS}}}tc")
        start = 1 if row_index == 0 else 0
        for cell in cells[start:cols]:
            row.remove(cell)


def _append_table_rows(table: ET.Element, *, count: int, values: list[list[str]]) -> None:
    rows = table.findall(f"{{{HP_NS}}}tr")
    if not rows:
        return
    template_row = rows[-1]
    total = max(count, len(values)) if values else count
    new_rows = list(rows)
    for index in range(total):
        clone = copy.deepcopy(template_row)
        _clear_row_text(clone)
        if index < len(values):
            _fill_row_values(clone, values[index])
        new_rows.append(clone)
    _replace_rows(table, new_rows)


def _delete_table_rows(table: ET.Element, *, count: int, header_rows: int) -> None:
    rows = table.findall(f"{{{HP_NS}}}tr")
    if not rows:
        return
    minimum_rows = min(header_rows, len(rows))
    keep_count = max(minimum_rows, len(rows) - count)
    if keep_count == len(rows):
        return
    _replace_rows(table, rows[:keep_count])


def _append_table_columns(table: ET.Element, *, count: int, values: list[list[str]], position: str) -> None:
    rows = table.findall(f"{{{HP_NS}}}tr")
    if not rows:
        return
    total = max(count, len(values)) if values else count
    for row_index, row in enumerate(rows):
        cells = row.findall(f"{{{HP_NS}}}tc")
        if not cells:
            continue
        insert_left = position in {"left", "before", "start"}
        source = cells[0] if insert_left else cells[-1]
        insert_at = list(row).index(cells[0]) if insert_left else list(row).index(cells[-1]) + 1
        for column_index in range(total):
            clone = copy.deepcopy(source)
            _clear_row_text(clone)
            if column_index < len(values) and row_index < len(values[column_index]):
                _fill_cell_value(clone, values[column_index][row_index])
            row.insert(insert_at + column_index, clone)
    table.attrib["colCnt"] = str(_table_col_count(table) + total)


def _delete_table_columns(table: ET.Element, *, count: int, position: str) -> None:
    rows = table.findall(f"{{{HP_NS}}}tr")
    if not rows:
        return
    delete_left = position in {"left", "before", "start"}
    for row in rows:
        for _ in range(count):
            cells = row.findall(f"{{{HP_NS}}}tc")
            if len(cells) <= 1:
                break
            row.remove(cells[0] if delete_left else cells[-1])
    table.attrib["colCnt"] = str(max(1, _table_col_count(table) - count))


def _renumber_table_rows(table: ET.Element) -> None:
    rows = table.findall(f"{{{HP_NS}}}tr")
    table.attrib["rowCnt"] = str(len(rows))
    for row_index, row in enumerate(rows):
        for cell_index, cell in enumerate(row.findall(f"{{{HP_NS}}}tc")):
            addr = cell.find(f"{{{HP_NS}}}cellAddr")
            if addr is not None:
                addr.attrib["rowAddr"] = str(row_index)
                if "colAddr" in addr.attrib:
                    addr.attrib["colAddr"] = str(cell_index)


def _clear_row_text(row: ET.Element) -> None:
    for text in row.iter(f"{{{HP_NS}}}t"):
        text.text = ""


def _fill_row_values(row: ET.Element, values: list[str]) -> None:
    for cell, value in zip(row.findall(f"{{{HP_NS}}}tc"), values):
        _fill_cell_value(cell, value)


def _fill_cell_value(cell: ET.Element, value: object) -> None:
    text_nodes = _ensure_cell_text_nodes(cell)
    if not text_nodes:
        return
    text_nodes[0].text = str(value)
    for extra in text_nodes[1:]:
        extra.text = ""


def _ensure_cell_text_nodes(cell: ET.Element) -> list[ET.Element]:
    text_nodes = list(cell.iter(f"{{{HP_NS}}}t"))
    if text_nodes:
        return text_nodes
    run = next(cell.iter(f"{{{HP_NS}}}run"), None)
    if run is None:
        paragraph = next(cell.iter(f"{{{HP_NS}}}p"), None)
        if paragraph is None:
            return []
        run = ET.SubElement(paragraph, f"{{{HP_NS}}}run")
    return [ET.SubElement(run, f"{{{HP_NS}}}t")]


def _normalize_table_row_values(value: object) -> list[list[str]]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return [[cell.strip() for cell in value.split("|")]]
    if isinstance(value, (tuple, list)):
        if all(not isinstance(item, (tuple, list)) for item in value):
            return [[str(item) for item in value]]
        return [[str(cell) for cell in row] for row in value if isinstance(row, (tuple, list))]
    return []


def _normalize_table_column_values(value: object) -> list[list[str]]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return [[cell.strip() for cell in value.split("|")]]
    if isinstance(value, (tuple, list)):
        if all(not isinstance(item, (tuple, list)) for item in value):
            return [[str(item) for item in value]]
        return [[str(cell) for cell in column] for column in value if isinstance(column, (tuple, list))]
    return []


def _table_col_count(table: ET.Element) -> int:
    value = table.attrib.get("colCnt", "")
    if value.isdigit():
        return int(value)
    counts = []
    for row in table.findall(f"{{{HP_NS}}}tr"):
        count = 0
        for cell in row.findall(f"{{{HP_NS}}}tc"):
            span = cell.find(f"{{{HP_NS}}}cellSpan")
            count += int(span.attrib.get("colSpan", "1")) if span is not None and span.attrib.get("colSpan", "1").isdigit() else 1
        counts.append(count)
    return max(counts) if counts else 0


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _apply_numeric_calculation(section_roots: dict[str, ET.Element]) -> None:
    for root in section_roots.values():
        for text in root.iter(f"{{{HP_NS}}}t"):
            if text.text:
                text.text = _replace_numeric_expressions(text.text)


def _apply_document_blocks(section_roots: dict[str, ET.Element], params: dict[str, object]) -> None:
    paragraphs = params.get("paragraphs", [])
    if isinstance(paragraphs, str):
        paragraphs = [line for line in paragraphs.splitlines() if line.strip()]
    if not isinstance(paragraphs, list) or not paragraphs:
        return
    for root in section_roots.values():
        anchor = _last_top_level_paragraph(root)
        if anchor is None:
            continue
        root_children = list(root)
        insert_at = root_children.index(anchor) + 1
        for value in paragraphs:
            clone = copy.deepcopy(anchor)
            first = True
            for text in clone.iter(f"{{{HP_NS}}}t"):
                text.text = str(value) if first else ""
                first = False
            root.insert(insert_at, clone)
            insert_at += 1
        break


def _apply_control_characters(section_roots: dict[str, ET.Element], params: dict[str, object]) -> None:
    for root in section_roots.values():
        for run in root.iter(f"{{{HP_NS}}}run"):
            children = list(run)
            changed = False
            replacement: list[ET.Element] = []
            for child in children:
                if child.tag == f"{{{HP_NS}}}t" and child.text:
                    nodes = _control_nodes_from_text(child.text, params)
                    if nodes is not None:
                        replacement.extend(nodes)
                        changed = True
                    else:
                        replacement.append(child)
                else:
                    replacement.append(child)
            if changed:
                run[:] = replacement


def _control_nodes_from_text(value: str, params: dict[str, object]) -> list[ET.Element] | None:
    fixed_space_token = str(params.get("fixed_space_token", "{{fixedspace}}"))
    fixed_space_changed = fixed_space_token in value
    value = value.replace(fixed_space_token, "\u2007")
    token_map = {
        str(params.get("tab_token", "{{tab}}")): f"{{{HP_NS}}}tab",
        str(params.get("line_break_token", "{{linebreak}}")): f"{{{HP_NS}}}lineBreak",
        str(params.get("br_token", "{{br}}")): f"{{{HP_NS}}}lineBreak",
    }
    pattern = re.compile("|".join(re.escape(token) for token in token_map if token))
    if not pattern.search(value):
        if not fixed_space_changed:
            return None
        text_node = ET.Element(f"{{{HP_NS}}}t")
        text_node.text = value
        return [text_node]

    nodes: list[ET.Element] = []
    offset = 0
    for match in pattern.finditer(value):
        if match.start() > offset:
            text_node = ET.Element(f"{{{HP_NS}}}t")
            text_node.text = value[offset : match.start()]
            nodes.append(text_node)
        nodes.append(ET.Element(token_map[match.group(0)]))
        offset = match.end()
    if offset < len(value):
        text_node = ET.Element(f"{{{HP_NS}}}t")
        text_node.text = value[offset:]
        nodes.append(text_node)
    return nodes or [ET.Element(f"{{{HP_NS}}}t")]


def _apply_page_break(section_roots: dict[str, ET.Element], params: dict[str, object]) -> None:
    if params.get("enabled") is False:
        return
    contains = str(params.get("contains", "")).strip()
    insert_blank = bool(params.get("insert_blank", False))
    for root in section_roots.values():
        paragraphs = [paragraph for paragraph in root.iter(f"{{{HP_NS}}}p") if any(text.text and text.text.strip() for text in paragraph.iter(f"{{{HP_NS}}}t"))]
        if contains:
            paragraphs = [paragraph for paragraph in paragraphs if contains in _paragraph_text(paragraph)]
        if not paragraphs:
            continue
        target = paragraphs[min(int(params.get("index", len(paragraphs) - 1)), len(paragraphs) - 1)] if str(params.get("index", "")).isdigit() else paragraphs[-1]
        if insert_blank and target in list(root):
            clone = copy.deepcopy(target)
            clone.attrib["pageBreak"] = "1"
            for text in clone.iter(f"{{{HP_NS}}}t"):
                text.text = ""
            root.insert(list(root).index(target) + 1, clone)
        else:
            target.attrib["pageBreak"] = "1"
        return


def _apply_page_number(section_roots: dict[str, ET.Element], params: dict[str, object]) -> None:
    mode = str(params.get("mode", "show")).strip().lower()
    for root in section_roots.values():
        for start_num in root.iter(f"{{{HP_NS}}}startNum"):
            if params.get("start") is not None:
                start_num.attrib["page"] = str(int(params["start"]))
            if params.get("pic") is not None:
                start_num.attrib["pic"] = str(int(params["pic"]))
            if params.get("tbl") is not None:
                start_num.attrib["tbl"] = str(int(params["tbl"]))
            if params.get("equation") is not None:
                start_num.attrib["equation"] = str(int(params["equation"]))
        for visibility in root.iter(f"{{{HP_NS}}}visibility"):
            if mode in {"hide", "hidden", "off"}:
                visibility.attrib["hideFirstPageNum"] = "1"
            elif mode in {"show", "visible", "on"}:
                visibility.attrib["hideFirstPageNum"] = "0"
            elif mode in {"reset", "restart"}:
                visibility.attrib["hideFirstPageNum"] = "0"
        if mode in {"reset", "restart"}:
            for start_num in root.iter(f"{{{HP_NS}}}startNum"):
                start_num.attrib["page"] = str(int(params.get("start", 1)))


def _paragraph_text(paragraph: ET.Element) -> str:
    return "".join(text.text or "" for text in paragraph.iter(f"{{{HP_NS}}}t"))


def _last_top_level_paragraph(root: ET.Element) -> ET.Element | None:
    for child in reversed(list(root)):
        if child.tag == f"{{{HP_NS}}}p" and any(text.text and text.text.strip() for text in child.iter(f"{{{HP_NS}}}t")):
            return child
    for paragraph in reversed(list(root.iter(f"{{{HP_NS}}}p"))):
        if any(text.text and text.text.strip() for text in paragraph.iter(f"{{{HP_NS}}}t")):
            return paragraph
    return None


def _split_header_rows(rows: list[ET.Element], *, header_rows: int) -> tuple[list[ET.Element], list[ET.Element]]:
    count = max(0, min(header_rows, len(rows) - 1))
    return rows[:count], rows[count:]


def _row_sort_key(row: ET.Element, *, numeric: bool) -> tuple[int, float | str]:
    text = " ".join((elem.text or "").strip() for elem in row.iter(f"{{{HP_NS}}}t") if (elem.text or "").strip())
    if not numeric:
        return (0, text)
    match = re.search(r"-?\d[\d,]*(?:\.\d+)?", text)
    if not match:
        return (1, text)
    return (0, float(match.group(0).replace(",", "")))


def _replace_rows(table: ET.Element, rows: list[ET.Element]) -> None:
    children = list(table)
    row_indices = [index for index, child in enumerate(children) if child.tag == f"{{{HP_NS}}}tr"]
    if not row_indices:
        return
    first_index = row_indices[0]
    for child in list(table):
        if child.tag == f"{{{HP_NS}}}tr":
            table.remove(child)
    for offset, row in enumerate(rows):
        table.insert(first_index + offset, row)


def _replace_numeric_expressions(value: str) -> str:
    value = re.sub(r"\{\{sum:([^}]+)\}\}", lambda match: _format_number(sum(_numbers(match.group(1)))), value)
    value = re.sub(r"\{\{diff:([^,}]+),([^}]+)\}\}", lambda match: _format_number(_number(match.group(2)) - _number(match.group(1))), value)
    value = re.sub(r"\{\{rate:([^,}]+),([^}]+)\}\}", lambda match: _format_percent(_rate(_number(match.group(1)), _number(match.group(2)))), value)
    value = re.sub(r"\{\{pct:([^,}]+),([^}]+)\}\}", lambda match: _format_percent(_pct(_number(match.group(1)), _number(match.group(2)))), value)
    return re.sub(r"(-?\d[\d,]*(?:\.\d+)?)\s*(?:→|->)\s*(-?\d[\d,]*(?:\.\d+)?)", _arrow_change, value)


def _arrow_change(match: re.Match[str]) -> str:
    before = _number(match.group(1))
    after = _number(match.group(2))
    diff = after - before
    rate = _rate(before, after)
    sign = "+" if diff >= 0 else ""
    return f"{match.group(1)} -> {match.group(2)} ({sign}{_format_number(diff)}, {sign}{_format_percent(rate)})"


def _numbers(value: str) -> list[float]:
    return [_number(item) for item in re.findall(r"-?\d[\d,]*(?:\.\d+)?", value)]


def _number(value: str) -> float:
    return float(str(value).replace(",", "").strip())


def _rate(before: float, after: float) -> float:
    return 0.0 if before == 0 else ((after - before) / before) * 100


def _pct(part: float, total: float) -> float:
    return 0.0 if total == 0 else (part / total) * 100


def _format_number(value: float) -> str:
    if value.is_integer():
        return f"{int(value):,}"
    return f"{value:,.2f}".rstrip("0").rstrip(".")


def _format_percent(value: float) -> str:
    return f"{value:.1f}%"


def _set_underline(char_pr: ET.Element, *, enabled: bool) -> None:
    underline = _ensure_child(char_pr, f"{{{HH_NS}}}underline")
    underline.attrib.update({"type": "BOTTOM" if enabled else "NONE", "shape": "SOLID", "color": "#000000"})


def _set_strikeout(char_pr: ET.Element, *, enabled: bool) -> None:
    strikeout = _ensure_child(char_pr, f"{{{HH_NS}}}strikeout")
    strikeout.attrib.update({"shape": "SOLID" if enabled else "NONE", "color": "#000000"})


def _set_empty_style_child(char_pr: ET.Element, name: str, *, enabled: bool) -> None:
    tag = f"{{{HH_NS}}}{name}"
    child = char_pr.find(tag)
    if enabled and child is None:
        ET.SubElement(char_pr, tag)
    elif not enabled and child is not None:
        char_pr.remove(child)


def _set_normal_char_style(char_pr: ET.Element) -> None:
    for name in ["bold", "italic"]:
        _set_empty_style_child(char_pr, name, enabled=False)
    _set_underline(char_pr, enabled=False)
    _set_strikeout(char_pr, enabled=False)
    _set_supscript(char_pr, "NONE")


def _set_supscript(char_pr: ET.Element, script_type: str) -> None:
    supscript = _ensure_child(char_pr, f"{{{HH_NS}}}supscript")
    supscript.attrib["type"] = _normalize_script_type(script_type)


def _set_shadow(char_pr: ET.Element, params: dict[str, object]) -> None:
    shadow = _ensure_child(char_pr, f"{{{HH_NS}}}shadow")
    if bool(params.get("remove", False)):
        shadow.attrib.clear()
        shadow.attrib["type"] = "NONE"
        return

    shadow_type = str(params.get("type", "DROP")).strip().upper() or "DROP"
    if shadow_type in {"OFF", "FALSE", "0"}:
        shadow_type = "NONE"
    shadow.attrib["type"] = shadow_type
    if shadow_type == "NONE":
        return

    offset = params.get("offset", "10")
    shadow.attrib["color"] = _normalize_color(params.get("color", "#C0C0C0"))
    shadow.attrib["offsetX"] = str(params.get("offset_x", params.get("x", offset)))
    shadow.attrib["offsetY"] = str(params.get("offset_y", params.get("y", offset)))


def _set_language_attrs(elem: ET.Element, value: str) -> None:
    for attr in LANG_ATTRS:
        elem.attrib[attr] = value


def _font_refs_for_family(header_root: ET.Element, params: dict[str, object]) -> dict[str, str]:
    face = str(params.get("face", params.get("family", params.get("font", "함초롬바탕")))).strip()
    if not face:
        raise ValueError("font_family requires a non-empty face/family/font parameter")
    latin_face = str(params.get("latin_face", params.get("latin", face))).strip() or face
    languages = params.get("languages", params.get("langs"))
    if isinstance(languages, str) and languages.strip():
        targets = [item.strip().lower() for item in re.split(r"[, ]+", languages) if item.strip()]
    elif isinstance(languages, (list, tuple)):
        targets = [str(item).strip().lower() for item in languages if str(item).strip()]
    else:
        targets = ["hangul", "hanja", "japanese", "other", "user", "latin"]
    if _truthy(params.get("include_symbol", False)) and "symbol" not in targets:
        targets.append("symbol")

    refs: dict[str, str] = {}
    for lang in targets:
        if lang not in LANG_ATTRS:
            continue
        refs[lang] = _font_id_for_face(header_root, lang, latin_face if lang == "latin" else face)
    return refs


def _font_id_for_face(header_root: ET.Element, lang: str, face: str) -> str:
    fontface = _ensure_fontface(header_root, lang)
    for font in fontface.findall(f"{{{HH_NS}}}font"):
        if font.attrib.get("face") == face:
            return font.attrib.get("id", "0")
    new_id = str(_next_numeric_id(fontface, f"{{{HH_NS}}}font"))
    source = fontface.find(f"{{{HH_NS}}}font")
    attrs = dict(source.attrib) if source is not None else {"type": "TTF", "isEmbedded": "0"}
    attrs.update({"id": new_id, "face": face})
    fontface.append(ET.Element(f"{{{HH_NS}}}font", attrs))
    fontface.attrib["fontCnt"] = str(len(fontface.findall(f"{{{HH_NS}}}font")))
    return new_id


def _ensure_fontface(header_root: ET.Element, lang: str) -> ET.Element:
    target = lang.upper()
    for fontface in header_root.iter(f"{{{HH_NS}}}fontface"):
        if fontface.attrib.get("lang", "").upper() == target:
            return fontface
    collection = _find_required(header_root, f"{{{HH_NS}}}fontfaces", "fontfaces")
    fontface = ET.Element(f"{{{HH_NS}}}fontface", {"lang": target, "fontCnt": "0"})
    collection.append(fontface)
    collection.attrib["itemCnt"] = str(len(collection.findall(f"{{{HH_NS}}}fontface")))
    return fontface


def _set_font_refs(char_pr: ET.Element, refs: dict[str, str]) -> None:
    font_ref = _ensure_child(char_pr, f"{{{HH_NS}}}fontRef")
    for lang, font_id in refs.items():
        if lang in LANG_ATTRS:
            font_ref.attrib[lang] = str(font_id)


def _normalize_script_type(value: object) -> str:
    text = str(value or "SUPERSCRIPT").strip().upper()
    aliases = {
        "SUPER": "SUPERSCRIPT",
        "SUP": "SUPERSCRIPT",
        "위첨자": "SUPERSCRIPT",
        "SUB": "SUBSCRIPT",
        "아래첨자": "SUBSCRIPT",
        "NORMAL": "NONE",
        "OFF": "NONE",
        "FALSE": "NONE",
    }
    return aliases.get(text, text if text in {"SUPERSCRIPT", "SUBSCRIPT", "NONE"} else "SUPERSCRIPT")


def _set_fill(border_fill: ET.Element, color: str) -> None:
    _remove_fill(border_fill)
    fill_brush = ET.SubElement(border_fill, f"{{{HC_NS}}}fillBrush")
    ET.SubElement(fill_brush, f"{{{HC_NS}}}winBrush", {"faceColor": color, "hatchColor": "#000000", "alpha": "0"})


def _remove_fill(border_fill: ET.Element) -> None:
    for child in list(border_fill):
        if child.tag in {f"{{{HH_NS}}}fillInfo", f"{{{HC_NS}}}fillBrush"}:
            border_fill.remove(child)


def _ensure_child(parent: ET.Element, tag: str) -> ET.Element:
    child = parent.find(tag)
    if child is None:
        child = ET.SubElement(parent, tag)
    return child


def _find_required(root: ET.Element, tag: str, label: str) -> ET.Element:
    elem = root.find(f".//{tag}")
    if elem is None:
        raise ValueError(f"HWPX header is missing {label}")
    return elem


def _next_numeric_id(collection: ET.Element, child_tag: str) -> int:
    ids = []
    for child in collection.findall(child_tag):
        value = child.attrib.get("id", "")
        if value.isdigit():
            ids.append(int(value))
    return (max(ids) + 1) if ids else 0


def _nearest(elem: ET.Element, parent_map: dict[ET.Element, ET.Element], tag: str) -> ET.Element | None:
    current = elem
    while current in parent_map:
        current = parent_map[current]
        if current.tag == tag:
            return current
    return None


def _require_header(header_root: ET.Element | None) -> None:
    if header_root is None:
        raise ValueError("HWPX header.xml is required for this feature")


def _normalize_color(value: object) -> str:
    text = str(value)
    if text == "none":
        return text
    if not text.startswith("#"):
        text = "#" + text
    if len(text) != 7:
        raise ValueError(f"Color must be #RRGGBB: {value}")
    return text.upper()


def _layout_value(value: object, params: dict[str, object]) -> str:
    if str(params.get("unit", "mm")).lower() in {"hwp", "hwpx", "hwpunit", "raw"}:
        return str(int(float(value)))
    return str(int(round(float(value) * 283.465)))


def _normalize_orientation(value: object) -> str:
    if isinstance(value, bool):
        return "WIDELY" if value else "NARROWLY"
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "landscape", "wide", "widely", "가로"}:
        return "WIDELY"
    if text in {"0", "false", "no", "portrait", "narrow", "narrowly", "세로"}:
        return "NARROWLY"
    return str(value)


def _default_char_pr() -> ET.Element:
    elem = ET.Element(
        f"{{{HH_NS}}}charPr",
        {
            "id": "0",
            "height": "1000",
            "textColor": "#000000",
            "shadeColor": "none",
            "useFontSpace": "0",
            "useKerning": "0",
            "symMark": "NONE",
            "borderFillIDRef": "0",
        },
    )
    ET.SubElement(elem, f"{{{HH_NS}}}fontRef", {"hangul": "0", "latin": "0", "hanja": "0", "japanese": "0", "other": "0", "symbol": "0", "user": "0"})
    for name in ["ratio", "spacing", "offset"]:
        ET.SubElement(elem, f"{{{HH_NS}}}{name}", {"hangul": "0", "latin": "0", "hanja": "0", "japanese": "0", "other": "0", "symbol": "0", "user": "0"})
    ET.SubElement(elem, f"{{{HH_NS}}}relSz", {"hangul": "100", "latin": "100", "hanja": "100", "japanese": "100", "other": "100", "symbol": "100", "user": "100"})
    return elem


def _default_border_fill() -> ET.Element:
    elem = ET.Element(f"{{{HH_NS}}}borderFill", {"id": "0", "threeD": "0", "shadow": "0", "centerLine": "0", "breakCellSeparateLine": "0"})
    ET.SubElement(elem, f"{{{HH_NS}}}slash", {"type": "NONE", "Crooked": "0", "isCounter": "0"})
    ET.SubElement(elem, f"{{{HH_NS}}}backSlash", {"type": "NONE", "Crooked": "0", "isCounter": "0"})
    for name in ["leftBorder", "rightBorder", "topBorder", "bottomBorder", "diagonal"]:
        ET.SubElement(elem, f"{{{HH_NS}}}{name}", {"type": "NONE", "width": "0.1 mm", "color": "#000000"})
    return elem


def _default_para_pr() -> ET.Element:
    elem = ET.Element(
        f"{{{HH_NS}}}paraPr",
        {
            "id": "0",
            "tabPrIDRef": "0",
            "condense": "0",
            "fontLineHeight": "0",
            "snapToGrid": "1",
            "suppressLineNumbers": "0",
            "checked": "0",
        },
    )
    ET.SubElement(elem, f"{{{HH_NS}}}align", {"horizontal": "JUSTIFY", "vertical": "BASELINE"})
    ET.SubElement(elem, f"{{{HH_NS}}}heading", {"type": "NONE", "idRef": "0", "level": "0"})
    ET.SubElement(
        elem,
        f"{{{HH_NS}}}breakSetting",
        {
            "breakLatinWord": "KEEP_WORD",
            "breakNonLatinWord": "BREAK_WORD",
            "widowOrphan": "0",
            "keepWithNext": "0",
            "keepLines": "0",
            "pageBreakBefore": "0",
            "lineWrap": "BREAK",
        },
    )
    ET.SubElement(elem, f"{{{HH_NS}}}lineSpacing", {"type": "PERCENT", "value": "160"})
    ET.SubElement(elem, f"{{{HH_NS}}}margin", {"left": "0", "right": "0", "indent": "0", "prev": "0", "next": "0"})
    return elem


def load_operations_json(value: str) -> list[FeatureOperation]:
    payload = json.loads(value)
    if not isinstance(payload, list):
        raise ValueError("feature operations JSON must be an array")
    return [_normalize_operation(item) for item in payload]
