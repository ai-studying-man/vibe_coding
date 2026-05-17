from __future__ import annotations

import copy
import json
import re
import urllib.error
import urllib.request
import uuid
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET

from .llm_adapter import DEFAULT_LOCAL_MODEL

from .hwpx import verify_hwpx


HP_NS = "http://www.hancom.co.kr/hwpml/2011/paragraph"
HS_NS = "http://www.hancom.co.kr/hwpml/2011/section"
HH_NS = "http://www.hancom.co.kr/hwpml/2011/head"

ET.register_namespace("hp", HP_NS)
ET.register_namespace("hs", HS_NS)
ET.register_namespace("hh", HH_NS)


@dataclass
class TextNodeInfo:
    index: int
    section: str
    text: str
    role: str
    char_pr_id: str = ""
    para_pr_id: str = ""
    in_table: bool = False


@dataclass
class StyleSummary:
    char_pr_count: int
    para_pr_count: int
    border_fill_count: int
    table_count: int
    cell_count: int
    char_styles: dict[str, dict[str, str]]
    para_styles: dict[str, dict[str, str]]
    table_samples: list[dict[str, str]]
    font_faces: dict[str, dict[str, dict[str, str]]] = field(default_factory=dict)
    border_fills: dict[str, dict] = field(default_factory=dict)


@dataclass
class TemplateAnalysis:
    template_id: str
    filename: str
    section_files: list[str]
    text_nodes: list[TextNodeInfo]
    title_candidates: list[str]
    content_candidates: list[str]
    preview_text: str
    style_summary: StyleSummary | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["text_nodes"] = [asdict(item) for item in self.text_nodes]
        if self.style_summary:
            data["style_summary"] = asdict(self.style_summary)
        return data


@dataclass
class DraftContent:
    title: str
    paragraphs: list[str]
    attachments: list[str]
    tables: list[list[list[str]]] = field(default_factory=list)
    llm_used: bool = False


def analyze_hwpx_template(path: str | Path, *, template_id: str | None = None) -> TemplateAnalysis:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(source)

    text_nodes: list[TextNodeInfo] = []
    section_files: list[str] = []
    running_index = 0
    with zipfile.ZipFile(source) as zf:
        section_files = sorted(name for name in zf.namelist() if name.startswith("Contents/section") and name.endswith(".xml"))
        if not section_files:
            raise ValueError("HWPX section XML was not found.")
        style_summary = _extract_style_summary(zf, section_files)
        for section in section_files:
            root = ET.fromstring(zf.read(section))
            parent_map = {child: parent for parent in root.iter() for child in parent}
            for elem in root.iter(f"{{{HP_NS}}}t"):
                value = _clean_text(elem.text or "")
                if not value:
                    continue
                role = _classify_text(value)
                run = _nearest_ancestor(elem, parent_map, f"{{{HP_NS}}}run")
                para = _nearest_ancestor(elem, parent_map, f"{{{HP_NS}}}p")
                table = _nearest_ancestor(elem, parent_map, f"{{{HP_NS}}}tbl")
                text_nodes.append(
                    TextNodeInfo(
                        running_index,
                        section,
                        value,
                        role,
                        char_pr_id=(run.attrib.get("charPrIDRef", "") if run is not None else ""),
                        para_pr_id=(para.attrib.get("paraPrIDRef", "") if para is not None else ""),
                        in_table=table is not None,
                    )
                )
                running_index += 1

    content = [node.text for node in text_nodes if node.role == "content"]
    titles = _select_title_candidates(text_nodes)
    preview_text = "\n".join(node.text for node in text_nodes[:60])
    return TemplateAnalysis(
        template_id=template_id or uuid.uuid4().hex,
        filename=source.name,
        section_files=section_files,
        text_nodes=text_nodes,
        title_candidates=titles[:5],
        content_candidates=content[:20],
        preview_text=preview_text[:3000],
        style_summary=style_summary,
    )


def draft_from_text(
    raw_text: str,
    analysis: TemplateAnalysis,
    *,
    model: str | None = None,
    base_url: str | None = None,
    use_llm: bool = True,
    profile: object | None = None,
) -> DraftContent:
    text = raw_text.strip()
    if not text:
        raise ValueError("텍스트 입력이 비어 있습니다.")

    if use_llm:
        try:
            return _draft_with_ollama(text, analysis, model=model, base_url=base_url, profile=profile)
        except Exception:
            pass
    return _draft_deterministic(text, profile=profile)


def fill_hwpx_template(
    template_path: str | Path,
    output_path: str | Path,
    draft: DraftContent,
    *,
    analysis: TemplateAnalysis | None = None,
) -> Path:
    source = Path(template_path)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if analysis is None:
        analysis = analyze_hwpx_template(source)

    replacements = _build_replacement_queue(draft)
    with zipfile.ZipFile(source, "r") as src, zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            data = src.read(info.filename)
            if info.filename in analysis.section_files:
                data = _rewrite_section_xml(data, replacements)
            elif info.filename == "Preview/PrvText.txt":
                data = _preview_text(draft).encode("utf-16le")
            elif info.filename == "DocInfo/DocumentProperties.xml":
                data = _rewrite_properties(data, draft.title)
            dst.writestr(info, data)

    verify_hwpx(output)
    return output


def save_analysis(path: str | Path, analysis: TemplateAnalysis) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(analysis.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


def load_analysis(path: str | Path) -> TemplateAnalysis:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return TemplateAnalysis(
        template_id=data["template_id"],
        filename=data["filename"],
        section_files=list(data["section_files"]),
        text_nodes=[TextNodeInfo(**item) for item in data["text_nodes"]],
        title_candidates=list(data.get("title_candidates", [])),
        content_candidates=list(data.get("content_candidates", [])),
        preview_text=data.get("preview_text", ""),
        style_summary=StyleSummary(**data["style_summary"]) if data.get("style_summary") else None,
    )


def _extract_style_summary(zf: zipfile.ZipFile, section_files: list[str]) -> StyleSummary:
    char_styles: dict[str, dict[str, str]] = {}
    para_styles: dict[str, dict[str, str]] = {}
    font_faces: dict[str, dict[str, dict[str, str]]] = {}
    border_fills: dict[str, dict] = {}
    border_fill_count = 0
    if "Contents/header.xml" in zf.namelist():
        header = ET.fromstring(zf.read("Contents/header.xml"))
        font_faces = _extract_font_faces(header)
        for char_pr in header.iter(f"{{{HH_NS}}}charPr"):
            style_id = char_pr.attrib.get("id", "")
            font_ref = char_pr.find(f"{{{HH_NS}}}fontRef")
            font_ref_ids = dict(font_ref.attrib) if font_ref is not None else {}
            font_ref_faces = _font_ref_faces(font_ref_ids, font_faces)
            char_styles[style_id] = {
                "height": char_pr.attrib.get("height", ""),
                "textColor": char_pr.attrib.get("textColor", ""),
                "shadeColor": char_pr.attrib.get("shadeColor", ""),
                "borderFillIDRef": char_pr.attrib.get("borderFillIDRef", ""),
                "fontRefHangul": font_ref_ids.get("hangul", ""),
                "fontRefLatin": font_ref_ids.get("latin", ""),
                "fontFaceHangul": font_ref_faces.get("hangul", ""),
                "fontFaceLatin": font_ref_faces.get("latin", ""),
            }
        for para_pr in header.iter(f"{{{HH_NS}}}paraPr"):
            style_id = para_pr.attrib.get("id", "")
            align = para_pr.find(f"{{{HH_NS}}}align")
            margin = para_pr.find(f"{{{HH_NS}}}margin")
            line_spacing = para_pr.find(f"{{{HH_NS}}}lineSpacing")
            para_styles[style_id] = {
                "horizontalAlign": align.attrib.get("horizontal", "") if align is not None else "",
                "verticalAlign": align.attrib.get("vertical", "") if align is not None else "",
                "marginLeft": margin.attrib.get("left", "") if margin is not None else "",
                "marginRight": margin.attrib.get("right", "") if margin is not None else "",
                "lineSpacingType": line_spacing.attrib.get("type", "") if line_spacing is not None else "",
                "lineSpacingValue": line_spacing.attrib.get("value", "") if line_spacing is not None else "",
            }
        border_fills = _extract_border_fills(header)
        border_fill_count = len(border_fills)

    table_count = 0
    cell_count = 0
    table_samples: list[dict[str, str]] = []
    for section in section_files:
        root = ET.fromstring(zf.read(section))
        for table in root.iter(f"{{{HP_NS}}}tbl"):
            table_count += 1
            if len(table_samples) < 10:
                table_samples.append({key: value for key, value in table.attrib.items() if key in {"rowCnt", "colCnt", "repeatHeader", "noAdjust", "zOrder"}})
        cell_count += sum(1 for _ in root.iter(f"{{{HP_NS}}}tc"))

    return StyleSummary(
        char_pr_count=len(char_styles),
        para_pr_count=len(para_styles),
        border_fill_count=border_fill_count,
        table_count=table_count,
        cell_count=cell_count,
        char_styles=char_styles,
        para_styles=para_styles,
        table_samples=table_samples,
        font_faces=font_faces,
        border_fills=border_fills,
    )


def _extract_font_faces(header: ET.Element) -> dict[str, dict[str, dict[str, str]]]:
    faces: dict[str, dict[str, dict[str, str]]] = {}
    for fontface in header.iter(f"{{{HH_NS}}}fontface"):
        lang = fontface.attrib.get("lang", "").lower()
        if not lang:
            continue
        faces[lang] = {}
        for font in fontface.findall(f"{{{HH_NS}}}font"):
            font_id = font.attrib.get("id", "")
            if font_id:
                faces[lang][font_id] = dict(font.attrib)
    return faces


def _font_ref_faces(
    font_ref_ids: dict[str, str],
    font_faces: dict[str, dict[str, dict[str, str]]],
) -> dict[str, str]:
    result: dict[str, str] = {}
    for lang, font_id in font_ref_ids.items():
        result[lang] = font_faces.get(lang, {}).get(font_id, {}).get("face", "")
    return result


def _extract_border_fills(header: ET.Element) -> dict[str, dict]:
    fills: dict[str, dict] = {}
    for border_fill in header.iter(f"{{{HH_NS}}}borderFill"):
        fill_id = border_fill.attrib.get("id", "")
        if fill_id:
            fills[fill_id] = _summarize_element(border_fill)
    return fills


def _summarize_element(elem: ET.Element) -> dict:
    summary: dict = {"attrs": dict(elem.attrib)}
    for child in list(elem):
        child_name = _local_name(child.tag)
        if len(list(child)):
            summary[child_name] = _summarize_element(child)
        else:
            summary[child_name] = dict(child.attrib)
    return summary


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _nearest_ancestor(elem: ET.Element, parent_map: dict[ET.Element, ET.Element], tag: str) -> ET.Element | None:
    current = elem
    while current in parent_map:
        current = parent_map[current]
        if current.tag == tag:
            return current
    return None


def _rewrite_section_xml(xml: bytes, replacements: list[str]) -> bytes:
    if not replacements:
        return xml
    root = ET.fromstring(xml)
    content_nodes = [elem for elem in root.iter(f"{{{HP_NS}}}t") if _classify_text(_clean_text(elem.text or "")) == "content"]
    if not content_nodes:
        content_nodes = [elem for elem in root.iter(f"{{{HP_NS}}}t") if _clean_text(elem.text or "")]

    for elem in content_nodes:
        elem.text = replacements.pop(0) if replacements else ""

    if replacements and content_nodes:
        _append_extra_paragraphs(root, content_nodes[-1], replacements)
        replacements.clear()

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _append_extra_paragraphs(root: ET.Element, anchor_text_node: ET.Element, paragraphs: list[str]) -> None:
    parent_map = {child: parent for parent in root.iter() for child in parent}
    paragraph = anchor_text_node
    while paragraph is not None and paragraph.tag != f"{{{HP_NS}}}p":
        paragraph = parent_map.get(paragraph)
    if paragraph is None:
        return

    root_children = list(root)
    try:
        insert_at = root_children.index(paragraph) + 1
    except ValueError:
        insert_at = len(root_children)

    for text in paragraphs:
        clone = copy.deepcopy(paragraph)
        for elem in clone.iter(f"{{{HP_NS}}}t"):
            elem.text = text
            break
        for elem in list(clone.iter(f"{{{HP_NS}}}t"))[1:]:
            elem.text = ""
        root.insert(insert_at, clone)
        insert_at += 1


def _rewrite_properties(xml: bytes, title: str) -> bytes:
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return xml
    for elem in root.iter():
        local_name = elem.tag.rsplit("}", 1)[-1]
        if local_name in {"title", "subject"}:
            elem.text = title
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _build_replacement_queue(draft: DraftContent) -> list[str]:
    values = [draft.title.strip()]
    values.extend(paragraph.strip() for paragraph in draft.paragraphs if paragraph.strip())
    if draft.attachments:
        values.append("붙임  " + ", ".join(draft.attachments))
    values.append("끝.")
    return [value for value in values if value]


def _draft_deterministic(raw_text: str, *, profile: object | None = None) -> DraftContent:
    raw_text, tables = _extract_markdown_tables(raw_text)
    lines = [_clean_text(line) for line in raw_text.splitlines()]
    lines = [line for line in lines if line]
    title = _guess_title(lines, raw_text)
    body_lines = lines[1:] if lines and lines[0] == title else lines
    paragraphs = _split_paragraphs("\n".join(body_lines) or raw_text)
    body_limit = _profile_body_slot_count(profile)
    if body_limit > 1 and len(paragraphs) > body_limit:
        paragraphs = paragraphs[: body_limit - 1] + [" ".join(paragraphs[body_limit - 1 :])]
    return DraftContent(title=title, paragraphs=paragraphs, attachments=[], tables=tables)


def _extract_markdown_tables(raw_text: str) -> tuple[str, list[list[list[str]]]]:
    lines = raw_text.splitlines()
    kept: list[str] = []
    tables: list[list[list[str]]] = []
    current: list[list[str]] = []
    for line in lines:
        if "|" in line:
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if cells and not all(re.fullmatch(r":?-{3,}:?", cell or "") for cell in cells):
                current.append(cells)
            continue
        if current:
            tables.append(current)
            current = []
        kept.append(line)
    if current:
        tables.append(current)
    return "\n".join(kept), tables


def _draft_with_ollama(
    raw_text: str,
    analysis: TemplateAnalysis,
    *,
    model: str | None = None,
    base_url: str | None = None,
    profile: object | None = None,
) -> DraftContent:
    endpoint = (base_url or "http://localhost:11434").rstrip("/")
    payload = {
        "model": model or DEFAULT_LOCAL_MODEL,
        "stream": False,
        "format": "json",
        "prompt": _ollama_prompt(raw_text, analysis, profile=profile),
        "options": {"temperature": 0.2},
    }
    req = urllib.request.Request(
        f"{endpoint}/api/generate",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        data = json.loads(response.read().decode("utf-8"))
    result = json.loads(data.get("response", "{}"))
    title = _clean_text(str(result.get("title") or "공문서"))
    paragraphs = [_clean_text(str(item)) for item in result.get("paragraphs", []) if _clean_text(str(item))]
    attachments = [_clean_text(str(item)) for item in result.get("attachments", []) if _clean_text(str(item))]
    if not paragraphs:
        paragraphs = _split_paragraphs(raw_text)
    tables = _normalize_llm_tables(result.get("tables", []))
    return DraftContent(title=title, paragraphs=paragraphs, attachments=attachments, tables=tables, llm_used=True)


def _normalize_llm_tables(value: object) -> list[list[list[str]]]:
    tables: list[list[list[str]]] = []
    if not isinstance(value, list):
        return tables
    for table in value:
        if isinstance(table, dict):
            rows = table.get("rows", [])
        else:
            rows = table
        if not isinstance(rows, list):
            continue
        normalized_rows = []
        for row in rows:
            if isinstance(row, list):
                normalized_rows.append([str(cell) for cell in row])
        if normalized_rows:
            tables.append(normalized_rows)
    return tables


def _ollama_prompt(raw_text: str, analysis: TemplateAnalysis) -> str:
    template_clues = "\n".join(analysis.content_candidates[:12])
    return f"""너는 한국 공공기관 공문서 작성 보조자다.
업로드된 HWPX 양식의 기존 본문 후보는 아래와 같다.

{template_clues}

사용자 원문을 이 양식에 들어갈 제목과 본문 문단으로 정리하라.
출력은 반드시 JSON만 반환한다.
스키마:
{{"title":"간결한 제목","paragraphs":["공문체 문단1","공문체 문단2"],"attachments":[]}}

원문:
{raw_text}
"""


def _profile_prompt_clues(profile: object | None) -> str:
    if profile is None:
        return "-"
    lines: list[str] = []
    slots = list(getattr(profile, "slots", []) or [])
    for slot in slots[:20]:
        style = getattr(slot, "style", {}) or {}
        char_style = style.get("char", {}) if isinstance(style, dict) else {}
        para_style = style.get("paragraph", {}) if isinstance(style, dict) else {}
        lines.append(
            "- slot "
            f"{getattr(slot, 'name', '')}: role={getattr(slot, 'role', '')}, "
            f"sample={getattr(slot, 'text', '')[:80]}, "
            f"font={char_style.get('fontFaceHangul', '')}, "
            f"size={char_style.get('height', '')}, "
            f"align={para_style.get('horizontalAlign', '')}"
        )
    tables = list(getattr(profile, "tables", []) or [])
    for index, table in enumerate(tables[:8], start=1):
        header_rows = getattr(table, "header_rows", 0) or 0
        cell_texts = getattr(table, "cell_texts", []) or []
        headers = cell_texts[:header_rows] if header_rows else cell_texts[:1]
        header_text = " / ".join(" | ".join(str(cell) for cell in row) for row in headers)
        lines.append(
            f"- table {index}: columns={getattr(table, 'column_count', 0)}, "
            f"header_rows={header_rows}, headers={header_text[:120]}"
        )
    return "\n".join(lines) if lines else "-"


def _profile_body_slot_count(profile: object | None) -> int:
    if profile is None:
        return 0
    return sum(1 for slot in (getattr(profile, "slots", []) or []) if getattr(slot, "role", "") == "body")


def _ollama_prompt(raw_text: str, analysis: TemplateAnalysis, *, profile: object | None = None) -> str:
    template_clues = "\n".join(analysis.content_candidates[:12])
    profile_clues = _profile_prompt_clues(profile)
    return f"""너는 한국 공공기관 공문서 작성 보조자다.
업로드된 HWPX 양식의 기존 본문 후보는 아래와 같다.

{template_clues}

학습된 양식 슬롯/표 프로필 요약은 아래와 같다.
{profile_clues}

사용자 원문을 해당 양식에 들어갈 제목, 본문 문단, 붙임, 표 데이터로 정리하라.
표 프로필이 있으면 원문의 표/목록을 tables 배열로 변환하라.
출력은 반드시 JSON만 반환한다.
스키마:
{{"title":"간결한 제목","paragraphs":["공문체 문단1","공문체 문단2"],"attachments":[],"tables":[[["헤더1","헤더2"],["값1","값2"]]]}}

원문:
{raw_text}
"""


def _preview_text(draft: DraftContent) -> str:
    return "\n".join(_build_replacement_queue(draft))


def _select_title_candidates(nodes: list[TextNodeInfo]) -> list[str]:
    candidates = [node.text for node in nodes if node.role == "content" and 4 <= len(node.text) <= 80]
    candidates.sort(key=lambda item: (0 if item.endswith(("계획", "보고", "요청", "안내")) else 1, len(item)))
    return candidates


def _classify_text(value: str) -> str:
    text = _clean_text(value)
    if not text:
        return "empty"
    if _is_metadata_text(text):
        return "metadata"
    return "content"


def _is_metadata_text(text: str) -> bool:
    if len(text) <= 1:
        return True
    exact = {
        "수신",
        "참조",
        "제목",
        "발신",
        "등록",
        "결재",
        "협조",
        "공개",
        "비공개",
        "붙임",
        "끝.",
        "끝",
    }
    if text in exact:
        return True
    if re.fullmatch(r"[\d\s.\-:/()]+", text):
        return True
    if re.search(r"(등록번호|문서번호|시행일자|접수일자|공개구분|담당자|전화번호|팩스번호)", text):
        return True
    if re.fullmatch(r"[가-힣A-Za-z]{1,4}\s*[:：]?", text):
        return True
    return False


def _guess_title(lines: list[str], raw_text: str) -> str:
    if lines:
        first = re.sub(r"^(제목|건명)\s*[:：]\s*", "", lines[0]).strip()
        if 4 <= len(first) <= 80:
            return first
    sentence = re.split(r"[.!?\n。]", raw_text.strip(), maxsplit=1)[0]
    sentence = _clean_text(sentence)
    return sentence[:60] or "공문서"


def _split_paragraphs(value: str) -> list[str]:
    chunks = [chunk.strip() for chunk in re.split(r"\n\s*\n|\r\n\s*\r\n", value) if chunk.strip()]
    if len(chunks) <= 1:
        lines = [_clean_text(line) for line in value.splitlines() if _clean_text(line)]
        chunks = lines if len(lines) > 1 else re.split(r"(?<=[.다요음함임])\s+", _clean_text(value))
    paragraphs = [_clean_text(chunk) for chunk in chunks if _clean_text(chunk)]
    return paragraphs[:30] or [_clean_text(value)]


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
