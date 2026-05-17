from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


BlockType = Literal["paragraph", "heading", "list", "table"]


@dataclass
class BodyBlock:
    type: BlockType = "paragraph"
    text: str = ""
    level: int = 1
    items: list[str] = field(default_factory=list)
    headers: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)

    @classmethod
    def from_any(cls, value: Any) -> "BodyBlock":
        if isinstance(value, str):
            return cls(text=value)
        if not isinstance(value, dict):
            return cls(text=str(value))
        return cls(
            type=value.get("type", "paragraph"),
            text=str(value.get("text", "")),
            level=int(value.get("level", 1) or 1),
            items=[str(x) for x in value.get("items", [])],
            headers=[str(x) for x in value.get("headers", [])],
            rows=[[str(cell) for cell in row] for row in value.get("rows", [])],
        )


@dataclass
class Attachment:
    title: str
    count: str = "1부"

    @classmethod
    def from_any(cls, value: Any) -> "Attachment":
        if isinstance(value, str):
            return cls(title=value)
        return cls(title=str(value.get("title", "")), count=str(value.get("count", "1부")))


@dataclass
class ApprovalStep:
    role: str
    name: str = ""

    @classmethod
    def from_any(cls, value: Any) -> "ApprovalStep":
        if isinstance(value, str):
            return cls(role=value)
        return cls(role=str(value.get("role", "")), name=str(value.get("name", "")))


@dataclass
class OfficialDocument:
    title: str
    sender: str
    recipients: list[str]
    body: list[BodyBlock]
    date: str | None = None
    registration_number: str = ""
    reference: str = ""
    classification: str = "공개"
    via: str = ""
    attachments: list[Attachment] = field(default_factory=list)
    approval: list[ApprovalStep] = field(default_factory=list)
    contact: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "OfficialDocument":
        recipients = data.get("recipients") or data.get("recipient") or data.get("to") or []
        if isinstance(recipients, str):
            recipients = [recipients]
        body = data.get("body") or data.get("content") or []
        if isinstance(body, str):
            body = [body]
        return cls(
            title=str(data.get("title", "")).strip(),
            sender=str(data.get("sender", data.get("from", ""))).strip(),
            recipients=[str(x).strip() for x in recipients if str(x).strip()],
            body=[BodyBlock.from_any(x) for x in body],
            date=data.get("date"),
            registration_number=str(data.get("registration_number", data.get("doc_no", ""))),
            reference=str(data.get("reference", "")),
            classification=str(data.get("classification", "공개")),
            via=str(data.get("via", "")),
            attachments=[Attachment.from_any(x) for x in data.get("attachments", [])],
            approval=[ApprovalStep.from_any(x) for x in data.get("approval", [])],
            contact=str(data.get("contact", "")),
            metadata=dict(data.get("metadata", {})),
        )

    def validate(self) -> None:
        missing = []
        if not self.title:
            missing.append("title")
        if not self.sender:
            missing.append("sender")
        if not self.recipients:
            missing.append("recipients")
        if not self.body:
            missing.append("body")
        if missing:
            raise ValueError("missing required document fields: " + ", ".join(missing))
