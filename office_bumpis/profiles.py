from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .models import Attachment, BodyBlock, OfficialDocument


PROFILE_ALIASES = {
    "approval": "approval_sheet",
    "approval_sheet": "approval_sheet",
    "결재서식": "approval_sheet",
    "plan": "plan_report",
    "plan_report": "plan_report",
    "계획보고": "plan_report",
    "reference": "work_reference",
    "work_reference": "work_reference",
    "업무참고": "work_reference",
    "meeting": "meeting_brief",
    "meeting_brief": "meeting_brief",
    "간담회": "meeting_brief",
    "comprehensive": "comprehensive_plan",
    "comprehensive_plan": "comprehensive_plan",
    "종합보고": "comprehensive_plan",
}


PROFILE_DESCRIPTIONS = {
    "approval_sheet": "Single official approval document with overview, main content, future plan, attachment, and approval metadata.",
    "plan_report": "Plan report with background, goal, direction, implementation plan, schedule, and administrative matters.",
    "work_reference": "Short work-reference brief for sharing operational context, main content, and future plan.",
    "meeting_brief": "Meeting/event brief with completed matters, scheduled matters, purpose, date, attendees, and key content.",
    "comprehensive_plan": "Long-form comprehensive plan with cover/TOC style sections, strategy, key tasks, administrative matters, and attachments.",
}


def normalize_profile(profile: str) -> str:
    key = profile.strip()
    normalized = PROFILE_ALIASES.get(key) or PROFILE_ALIASES.get(key.lower())
    if not normalized:
        raise ValueError(f"unknown document profile: {profile}")
    return normalized


def profile_names() -> list[str]:
    return sorted(PROFILE_DESCRIPTIONS)


def build_profile_document(profile: str, seed: dict[str, Any]) -> OfficialDocument:
    normalized = normalize_profile(profile)
    seed = {**seed, "profile": normalized}
    common = _common_fields(seed)
    body = _profile_body(normalized, seed)
    attachments = seed.get("attachments")
    if attachments is None and normalized in {"approval_sheet", "plan_report", "comprehensive_plan"}:
        attachments = [{"title": "세부 추진계획", "count": "1부"}]
    return OfficialDocument.from_mapping({**common, "body": body, "attachments": attachments or []})


def build_profile_mapping(profile: str, seed: dict[str, Any]) -> dict[str, Any]:
    return asdict(build_profile_document(profile, seed))


def profile_prompt(profile: str) -> str:
    normalized = normalize_profile(profile)
    if normalized == "approval_sheet":
        keys = "overview, main_items, future_plan"
    elif normalized == "plan_report":
        keys = "background, directions, plan_items, schedule, admin_matters"
    elif normalized == "work_reference":
        keys = "purpose, main_points, future_plan"
    elif normalized == "meeting_brief":
        keys = "completed_items, purpose, event_date, attendees, main_content, meeting_items"
    elif normalized == "comprehensive_plan":
        keys = "background, directions, key_tasks, admin_matters, appendix_notes"
    else:
        keys = "body"
    return (
        f"Use the `{normalized}` official-document profile. "
        "Return JSON seed data, not Markdown. Include common fields title, sender, recipients, date, "
        "registration_number, reference, classification, approval, attachments, contact when known. "
        f"For this profile, prefer these content keys: {keys}."
    )


def _common_fields(seed: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": seed.get("title") or "공문 제목을 입력하세요",
        "sender": seed.get("sender") or seed.get("department") or "담당부서",
        "recipients": seed.get("recipients") or seed.get("recipient") or ["수신기관"],
        "date": seed.get("date"),
        "registration_number": seed.get("registration_number") or seed.get("doc_no") or "",
        "reference": seed.get("reference", ""),
        "classification": seed.get("classification", "공개"),
        "via": seed.get("via", ""),
        "approval": seed.get("approval") or _default_approval(seed),
        "contact": seed.get("contact", ""),
        "metadata": {**dict(seed.get("metadata", {})), "profile": seed.get("profile", "")},
    }


def _default_approval(seed: dict[str, Any]) -> list[dict[str, str]]:
    roles = seed.get("approval_roles") or ["담당", "팀장", "과장"]
    return [{"role": str(role), "name": ""} for role in roles]


def _profile_body(profile: str, seed: dict[str, Any]) -> list[dict[str, Any]]:
    explicit_body = seed.get("body")
    if explicit_body:
        return explicit_body
    if profile == "approval_sheet":
        return _approval_body(seed)
    if profile == "plan_report":
        return _plan_report_body(seed)
    if profile == "work_reference":
        return _work_reference_body(seed)
    if profile == "meeting_brief":
        return _meeting_brief_body(seed)
    if profile == "comprehensive_plan":
        return _comprehensive_plan_body(seed)
    raise ValueError(f"unknown document profile: {profile}")


def _approval_body(seed: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _heading("개요(추진배경/목적)"),
        _paragraph(seed, "overview", "추진 배경과 목적을 간결하게 작성합니다."),
        _heading("주요 내용"),
        _table(seed, "main_items", ["구분", "내용"], [["주요 내용", "핵심 추진 내용을 작성합니다."]]),
        _heading("향후 계획"),
        _list(seed, "future_plan", "향후 계획", ["세부 일정과 후속 조치 계획을 작성합니다."]),
    ]


def _plan_report_body(seed: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _heading("추진 배경"),
        _paragraph(seed, "background", "사업 또는 정책을 추진하게 된 배경을 작성합니다."),
        _heading("목적 및 추진 방향"),
        _list(seed, "directions", "추진 방향", ["목표", "대상", "추진 원칙"]),
        _heading("추진 계획"),
        _table(seed, "plan_items", ["과제", "주요 내용", "일정"], [["세부 과제", "추진 내용을 작성합니다.", "추진 일정"]]),
        _heading("향후 일정"),
        _list(seed, "schedule", "향후 일정", ["계획 수립", "시행", "결과 보고"]),
        _heading("행정 사항"),
        _list(seed, "admin_matters", "행정 사항", ["부서별 협조 사항을 작성합니다."]),
    ]


def _work_reference_body(seed: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _heading("목적"),
        _paragraph(seed, "purpose", "업무 참고자료의 목적을 작성합니다."),
        _heading("주요 내용"),
        _list(seed, "main_points", "주요 내용", ["공유할 업무 경험, 산출물, 적용 방안을 작성합니다."]),
        _heading("향후 계획"),
        _list(seed, "future_plan", "향후 계획", ["후속 조치 또는 적용 계획을 작성합니다."]),
    ]


def _meeting_brief_body(seed: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _heading("실시사항"),
        _list(seed, "completed_items", "실시사항", ["완료된 협의 또는 준비 사항을 작성합니다."]),
        _heading("예정사항"),
        _table(
            seed,
            "meeting_items",
            ["구분", "내용"],
            [
                ["목적", seed.get("purpose", "간담회 목적을 작성합니다.")],
                ["일시", seed.get("event_date", "일시를 작성합니다.")],
                ["참석 대상", seed.get("attendees", "참석 대상을 작성합니다.")],
                ["주요 내용", seed.get("main_content", "주요 논의 내용을 작성합니다.")],
            ],
        ),
    ]


def _comprehensive_plan_body(seed: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _heading("추진배경"),
        _paragraph(seed, "background", "종합계획 수립 배경을 작성합니다."),
        _heading("추진방향"),
        _list(seed, "directions", "추진방향", ["비전", "목표", "추진전략"]),
        _heading("중점과제"),
        _table(seed, "key_tasks", ["연번", "중점과제", "주요 내용"], [["1", "중점과제명", "세부 내용을 작성합니다."]]),
        _heading("행정사항"),
        _list(seed, "admin_matters", "행정사항", ["기관 및 부서별 이행 사항을 작성합니다."]),
        _heading("붙임"),
        _list(seed, "appendix_notes", "붙임", ["세부 자료 목록을 작성합니다."]),
    ]


def _heading(text: str, level: int = 2) -> dict[str, Any]:
    return asdict(BodyBlock(type="heading", text=text, level=level))


def _paragraph(seed: dict[str, Any], key: str, fallback: str) -> dict[str, Any]:
    return asdict(BodyBlock(type="paragraph", text=str(seed.get(key) or fallback)))


def _list(seed: dict[str, Any], key: str, text: str, fallback: list[str]) -> dict[str, Any]:
    value = seed.get(key) or fallback
    items = value if isinstance(value, list) else [str(value)]
    return asdict(BodyBlock(type="list", text=text, items=[str(item) for item in items]))


def _table(seed: dict[str, Any], key: str, headers: list[str], fallback_rows: list[list[str]]) -> dict[str, Any]:
    rows = seed.get(key) or fallback_rows
    return asdict(BodyBlock(type="table", headers=headers, rows=[[str(cell) for cell in row] for row in rows]))


def attachment_mappings(values: list[Attachment]) -> list[dict[str, Any]]:
    return [asdict(value) for value in values]
