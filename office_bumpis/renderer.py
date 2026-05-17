from __future__ import annotations

from .formatting import official_date
from .models import BodyBlock, OfficialDocument


def render_markdown(document: OfficialDocument) -> str:
    document.validate()
    lines: list[str] = []

    if document.sender:
        lines.append(f"# {document.sender}")
        lines.append("")

    lines.extend(_metadata_table(document))
    lines.append("")
    lines.append(f"수신  {', '.join(document.recipients)}")
    if document.via:
        lines.append(f"(경유)  {document.via}")
    lines.append(f"제목  {document.title}")
    lines.append("")

    paragraph_index = 1
    for block in document.body:
        lines.extend(_render_block(block, paragraph_index))
        if block.type in {"paragraph", "list"} and block.text and not block.text.lstrip().startswith(("-", "ㅇ", "※")):
            paragraph_index += 1
        if lines and lines[-1] != "":
            lines.append("")

    if document.attachments:
        lines.append("붙임")
        for idx, attachment in enumerate(document.attachments, start=1):
            lines.append(f"{idx}. {attachment.title} {attachment.count}")
        lines.append("")

    lines.append("끝.")
    if document.contact:
        lines.append("")
        lines.append(f"담당자  {document.contact}")
    return "\n".join(lines).strip() + "\n"


def _metadata_table(document: OfficialDocument) -> list[str]:
    rows = [
        ("문서번호", document.registration_number or "-"),
        ("시행일", official_date(document.date)),
        ("공개구분", document.classification or "공개"),
    ]
    if document.reference:
        rows.append(("관련", document.reference))
    if document.approval:
        rows.append(("결재", " → ".join(step.role if not step.name else f"{step.role} {step.name}" for step in document.approval)))
    return [
        "| 구분 | 내용 |",
        "| --- | --- |",
        *[f"| {key} | {value} |" for key, value in rows],
    ]


def _render_block(block: BodyBlock, index: int) -> list[str]:
    if block.type == "heading":
        level = min(max(block.level, 2), 4)
        return [f"{'#' * level} {block.text}"]
    if block.type == "list":
        return [f"{index}. {block.text}"] + [f"   - {item}" for item in block.items]
    if block.type == "table":
        headers = block.headers or _infer_headers(block.rows)
        rows = block.rows
        if not headers:
            return []
        width = len(headers)
        normalized = [row + [""] * (width - len(row)) for row in rows]
        return [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * width) + " |",
            *["| " + " | ".join(row[:width]) + " |" for row in normalized],
        ]
    prefix = f"{index}. " if not block.text.lstrip().startswith(("-", "ㅇ", "※")) else ""
    return [prefix + block.text]


def _infer_headers(rows: list[list[str]]) -> list[str]:
    if not rows:
        return []
    return [f"항목{i + 1}" for i in range(max(len(row) for row in rows))]
