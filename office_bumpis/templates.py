from __future__ import annotations

import json
import re
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from xml.etree import ElementTree as ET


@dataclass
class HwpxTemplateInfo:
    name: str
    path: str
    size: int
    profile: str
    entries: int
    section_files: list[str]
    has_approval_table: bool
    has_cover: bool
    has_toc: bool
    placeholders: list[str]
    markers: list[str]
    preview_text: str


def inspect_hwpx_template(path: str | Path) -> HwpxTemplateInfo:
    source = Path(path)
    with zipfile.ZipFile(source) as zf:
        names = zf.namelist()
        section_files = sorted(name for name in names if name.startswith("Contents/section") and name.endswith(".xml"))
        text_chunks: list[str] = []
        for section in section_files:
            text_chunks.extend(_extract_section_text(zf.read(section)))

    normalized = _normalize_text(" ".join(text_chunks))
    markers = _detect_markers(normalized)
    return HwpxTemplateInfo(
        name=source.name,
        path=str(source),
        size=source.stat().st_size,
        profile=_detect_profile(normalized),
        entries=len(names),
        section_files=section_files,
        has_approval_table=any(marker in markers for marker in ["결재", "등록번호", "생산등록번호"]),
        has_cover="목차" in normalized or "추진계획" in normalized or "종합 추진계획" in normalized,
        has_toc="목차" in normalized or "목 차" in normalized,
        placeholders=_detect_placeholders(normalized),
        markers=markers,
        preview_text=normalized[:1000],
    )


def inspect_hwpx_templates(root: str | Path) -> list[HwpxTemplateInfo]:
    base = Path(root)
    if base.is_file():
        paths = [base]
    else:
        paths = sorted(base.rglob("*.hwpx"))
    return [inspect_hwpx_template(path) for path in paths]


def write_inventory(
    templates: list[HwpxTemplateInfo],
    *,
    json_path: str | Path | None = None,
    markdown_path: str | Path | None = None,
) -> None:
    if json_path:
        path = Path(json_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps([asdict(info) for info in templates], ensure_ascii=False, indent=2), encoding="utf-8")
    if markdown_path:
        path = Path(markdown_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_inventory_markdown(templates), encoding="utf-8")


def render_inventory_markdown(templates: list[HwpxTemplateInfo]) -> str:
    lines = [
        "# HWPX Template Inventory",
        "",
        "| Template | Profile | Approval | Cover/TOC | Placeholders | Markers |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in templates:
        cover = "/".join(part for part, enabled in [("cover", item.has_cover), ("toc", item.has_toc)] if enabled) or "-"
        lines.append(
            "| "
            + " | ".join(
                [
                    item.name,
                    item.profile,
                    "yes" if item.has_approval_table else "no",
                    cover,
                    ", ".join(item.placeholders[:8]) or "-",
                    ", ".join(item.markers[:8]) or "-",
                ]
            )
            + " |"
        )
    lines.append("")
    for item in templates:
        lines.extend(
            [
                f"## {item.name}",
                "",
                f"- Path: `{item.path}`",
                f"- Size: {item.size:,} bytes",
                f"- Profile: `{item.profile}`",
                f"- Sections: {', '.join(item.section_files)}",
                "",
                "Preview:",
                "",
                "```text",
                item.preview_text,
                "```",
                "",
            ]
        )
    return "\n".join(lines)


def _extract_section_text(xml: bytes) -> list[str]:
    root = ET.fromstring(xml)
    chunks: list[str] = []
    for elem in root.iter():
        if elem.tag.endswith("}t") and elem.text:
            chunks.append(elem.text)
    return chunks


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _detect_markers(text: str) -> list[str]:
    candidates = [
        "생산등록번호",
        "등록번호",
        "등록일",
        "등록일자",
        "결재일",
        "결재일자",
        "공개구분",
        "공개 구분",
        "협조",
        "협 조",
        "제목",
        "목차",
        "추진 배경",
        "추진방향",
        "주요 내용",
        "향후 계획",
        "행정 사항",
        "붙임",
        "끝",
        "보고자",
    ]
    return [candidate for candidate in candidates if candidate in text]


def _detect_placeholders(text: str) -> list[str]:
    placeholders = set(re.findall(r"[○0]{2,}[A-Za-z가-힣]*", text))
    placeholders.update(re.findall(r"20\d{2}\.\s*\d{0,2}\.\s*\d{0,2}\.", text))
    return sorted(placeholders)[:30]


def _detect_profile(text: str) -> str:
    if "종합 추진계획" in text:
        return "comprehensive_plan"
    if "업무참고용" in text:
        return "work_reference"
    if "정책간담회" in text or "실시사항" in text:
        return "meeting_brief"
    if "세부계획 보고" in text or "추진 계획" in text:
        return "plan_report"
    if "생산등록번호" in text and "제목" in text:
        return "approval_sheet"
    return "generic_hwpx"
