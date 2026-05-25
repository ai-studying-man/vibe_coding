from __future__ import annotations

import argparse
import html
import io
import json
import mimetypes
import re
import shutil
import uuid
import zipfile
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from xml.etree import ElementTree as ET

from .hwpx_features import apply_standard_features
from .llm_adapter import DEFAULT_LOCAL_MODEL, OpenCompatibleLLM
from .profile_filler import fill_hwpx_with_profile
from .structure_guard import guard_template_output
from .template_engine import analyze_hwpx_template, draft_from_text, fill_hwpx_template, load_analysis, save_analysis
from .template_profile import learn_template_profile, load_profile, render_profile_markdown, save_profile


RUNTIME_DIR = Path(".runtime")
TEMPLATE_DIR = RUNTIME_DIR / "templates"
OUTPUT_DIR = RUNTIME_DIR / "outputs"
ATTACHMENT_DIR = RUNTIME_DIR / "attachments"

TEXT_ATTACHMENT_EXTENSIONS = {
    ".txt",
    ".md",
    ".markdown",
    ".json",
    ".csv",
    ".tsv",
    ".xml",
    ".html",
    ".css",
    ".js",
    ".py",
    ".toml",
    ".yaml",
    ".yml",
    ".log",
}
MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024
MAX_ATTACHMENT_TEXT_CHARS = 12000

AGENT_SYSTEM_PROMPT = """You are a local Korean SLM agent running on Qwen3-4B.
Answer the user's questions directly and practically.
When the user asks about HWPX or public-office document automation, explain the available local workflow:
upload one HWPX form, analyze the XML/profile, enter text, generate a new HWPX, then download it.
Do not claim that you can access external services unless the user provides that context.
"""


WEB_FEATURE_OPTIONS: tuple[tuple[str, str, bool], ...] = (
    ("cleanup_whitespace", "공백정리", True),
    ("remove_empty_lines", "빈 줄 정리", False),
    ("font_size", "글자크기", False),
    ("font_color", "글자색", False),
    ("text_background", "글자 배경색", False),
    ("strike_or_underline", "밑줄/취소선", False),
    ("character_emphasis", "볼드/이탤릭", False),
    ("superscript_subscript", "위첨자", False),
    ("character_spacing", "자간", False),
    ("paragraph_alignment", "문단 정렬", False),
    ("paragraph_spacing", "문단 간격", False),
    ("table_background", "표 배경색", False),
    ("table_border", "표 테두리", False),
    ("transparent_table", "투명표", False),
    ("table_dimensions", "표 여백", False),
    ("table_merge_split", "셀 병합", False),
    ("table_rows", "표 행 추가/삭제", False),
    ("table_sort", "표 정렬", False),
    ("document_blocks", "검토 블록 추가", False),
    ("control_characters", "탭/줄바꿈 토큰", False),
    ("page_break", "쪽 나누기", False),
    ("numeric_calculation", "증감계산", False),
)


@dataclass
class UploadedFile:
    filename: str
    value: bytes

    @property
    def file(self) -> io.BytesIO:
        return io.BytesIO(self.value)


class BumpisRequestHandler(BaseHTTPRequestHandler):
    server_version = "OfficeBumpis/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_html(_index_html())
            return
        if parsed.path == "/favicon.ico":
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()
            return
        if parsed.path.startswith("/download/"):
            self._send_download(parsed.path.removeprefix("/download/"))
            return
        if parsed.path.startswith("/profile/"):
            self._send_profile_download(parsed.path.removeprefix("/profile/"))
            return
        self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/analyze":
            self._handle_analyze()
            return
        if parsed.path == "/api/generate":
            self._handle_generate()
            return
        if parsed.path == "/api/chat":
            self._handle_chat()
            return
        if parsed.path == "/api/attachment":
            self._handle_attachment()
            return
        self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args) -> None:
        print("%s - %s" % (self.address_string(), format % args))

    def _handle_analyze(self) -> None:
        try:
            fields = self._parse_form()
            upload = fields.get("template")
            if upload is None or not getattr(upload, "filename", ""):
                raise ValueError("문서 양식 HWPX 파일을 업로드해야 합니다.")
            if not upload.filename.lower().endswith(".hwpx"):
                raise ValueError("현재 업로드 양식은 .hwpx 파일만 지원합니다.")

            template_id = uuid.uuid4().hex
            template_path = TEMPLATE_DIR / f"{template_id}.hwpx"
            TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
            with template_path.open("wb") as target:
                shutil.copyfileobj(upload.file, target)

            analysis = analyze_hwpx_template(template_path, template_id=template_id)
            save_analysis(TEMPLATE_DIR / f"{template_id}.json", analysis)
            profile = learn_template_profile(template_path, template_id=template_id)
            save_profile(TEMPLATE_DIR / f"{template_id}.profile.json", profile)
            (TEMPLATE_DIR / f"{template_id}.profile.md").write_text(render_profile_markdown(profile), encoding="utf-8")
            _write_template_xml_bundle(template_id, template_path)
            self._send_json(
                {
                    "template_id": template_id,
                    "filename": upload.filename,
                    "section_files": analysis.section_files,
                    "text_node_count": len(analysis.text_nodes),
                    "style_summary": analysis.style_summary.__dict__ if analysis.style_summary else {},
                    "slots": [slot.__dict__ for slot in profile.slots[:12]],
                    "block_count": len(profile.blocks),
                    "title_candidates": analysis.title_candidates,
                    "content_candidates": analysis.content_candidates[:8],
                    "preview_text": analysis.preview_text,
                    "analysis_json_url": f"/profile/{template_id}.json",
                    "profile_json_url": f"/profile/{template_id}.profile.json",
                    "profile_markdown_url": f"/profile/{template_id}.profile.md",
                    "xml_bundle_url": f"/profile/{template_id}.xml.zip",
                }
            )
        except Exception as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def _handle_generate(self) -> None:
        try:
            fields = self._parse_form()
            template_id = _field_value(fields, "template_id")
            raw_text = _field_value(fields, "text")
            model = _field_value(fields, "model") or None
            use_llm = _field_value(fields, "use_llm") != "false"
            feature_keys = [key for key in _field_value(fields, "features").split(",") if key]
            if not template_id:
                raise ValueError("먼저 문서 양식을 업로드해야 합니다.")
            template_path = TEMPLATE_DIR / f"{template_id}.hwpx"
            analysis_path = TEMPLATE_DIR / f"{template_id}.json"
            if not template_path.exists() or not analysis_path.exists():
                raise ValueError("업로드된 문서 양식을 찾을 수 없습니다.")

            analysis = load_analysis(analysis_path)
            profile_path = TEMPLATE_DIR / f"{template_id}.profile.json"
            profile = load_profile(profile_path) if profile_path.exists() else None
            draft = draft_from_text(raw_text, analysis, model=model, use_llm=use_llm, profile=profile)
            output_id = uuid.uuid4().hex
            output_path = OUTPUT_DIR / f"{output_id}.hwpx"
            guard_report = {}
            if feature_keys:
                raw_output = OUTPUT_DIR / f"{output_id}.raw.hwpx"
                if profile is not None:
                    fill_hwpx_with_profile(template_path, raw_output, draft, profile)
                else:
                    fill_hwpx_template(template_path, raw_output, draft, analysis=analysis)
                guard_report = _guard_generated_output(template_path, raw_output, profile_path)
                operations = [{"key": key, "params": _web_feature_params(key)} for key in feature_keys]
                apply_standard_features(raw_output, output_path, operations)
            else:
                if profile is not None:
                    fill_hwpx_with_profile(template_path, output_path, draft, profile)
                else:
                    fill_hwpx_template(template_path, output_path, draft, analysis=analysis)
                guard_report = _guard_generated_output(template_path, output_path, profile_path)
            self._send_json(
                {
                    "output_id": output_id,
                    "download_url": f"/download/{output_id}.hwpx",
                    "title": draft.title,
                    "paragraph_count": len(draft.paragraphs),
                    "features": feature_keys,
                    "llm_used": draft.llm_used,
                    "structure_guard": guard_report,
                    "preview_text": "\n".join([draft.title, *draft.paragraphs[:8]]),
                }
            )
        except Exception as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def _handle_chat(self) -> None:
        try:
            payload = self._parse_json_body()
            messages = payload.get("messages", [])
            if not isinstance(messages, list):
                raise ValueError("messages must be an array")
            model = str(payload.get("model") or DEFAULT_LOCAL_MODEL)
            client = OpenCompatibleLLM(base_url="http://localhost:11434/v1", model=model, timeout=180)
            answer = client.chat(messages, system_prompt=AGENT_SYSTEM_PROMPT)
            self._send_json(
                {
                    "model": model,
                    "answer": answer,
                    "progress": [
                        "사용자 질문 수신",
                        f"Qwen 모델 호출: {model}",
                        "응답 생성 완료",
                    ],
                }
            )
        except Exception as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def _handle_attachment(self) -> None:
        try:
            fields = self._parse_form()
            upload = fields.get("file")
            if upload is None or not getattr(upload, "filename", ""):
                raise ValueError("첨부할 파일을 선택해야 합니다.")
            if len(upload.value) > MAX_ATTACHMENT_BYTES:
                raise ValueError("첨부 파일은 5MB 이하만 지원합니다.")

            ATTACHMENT_DIR.mkdir(parents=True, exist_ok=True)
            attachment_id = uuid.uuid4().hex
            safe_name = Path(upload.filename).name
            stored_path = ATTACHMENT_DIR / f"{attachment_id}_{safe_name}"
            stored_path.write_bytes(upload.value)
            extracted_text = _extract_attachment_text(safe_name, upload.value)
            self._send_json(
                {
                    "attachment_id": attachment_id,
                    "filename": safe_name,
                    "size": len(upload.value),
                    "text": extracted_text,
                    "preview": extracted_text[:1000],
                    "truncated": len(extracted_text) >= MAX_ATTACHMENT_TEXT_CHARS,
                }
            )
        except Exception as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def _parse_form(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        content_type = self.headers.get("Content-Type", "")
        if content_type.startswith("multipart/form-data"):
            return _parse_multipart(body, content_type)
        payload = body.decode("utf-8")
        return {key: value[-1] for key, value in parse_qs(payload).items()}

    def _parse_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        data = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("JSON body must be an object")
        return data

    def _send_html(self, value: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = value.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, value: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_download(self, name: str) -> None:
        safe_name = Path(name).name
        target = OUTPUT_DIR / safe_name
        if not target.exists():
            self._send_json({"error": "file not found"}, HTTPStatus.NOT_FOUND)
            return
        data = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mimetypes.guess_type(target.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Disposition", f"attachment; filename={html.escape(target.name)}")
        self.end_headers()
        self.wfile.write(data)

    def _send_profile_download(self, name: str) -> None:
        target = _template_artifact_path(name)
        if target is None or not target.exists():
            self._send_json({"error": "file not found"}, HTTPStatus.NOT_FOUND)
            return
        data = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mimetypes.guess_type(target.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Disposition", f"attachment; filename={html.escape(target.name)}")
        self.end_headers()
        self.wfile.write(data)


def run(host: str = "127.0.0.1", port: int = 8765) -> None:
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ATTACHMENT_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((host, port), BumpisRequestHandler)
    print(f"Office Bumpis web app running at http://{host}:{port}")
    server.serve_forever()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="office-bumpis-web")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    run(args.host, args.port)


def _field_value(fields: dict, key: str) -> str:
    value = fields.get(key)
    if value is None:
        return ""
    if hasattr(value, "value"):
        return str(value.value).strip()
    return str(value).strip()


def _template_artifact_path(name: str) -> Path | None:
    safe_name = Path(name).name
    if safe_name != name or not re.fullmatch(r"[0-9a-f]{32}(?:\.profile)?\.(?:json|md)|[0-9a-f]{32}\.xml\.zip", safe_name):
        return None
    return TEMPLATE_DIR / safe_name


def _write_template_xml_bundle(template_id: str, template_path: Path) -> Path:
    bundle_path = TEMPLATE_DIR / f"{template_id}.xml.zip"
    with zipfile.ZipFile(template_path) as source, zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for name in source.namelist():
            if name == "Contents/header.xml" or (name.startswith("Contents/section") and name.endswith(".xml")):
                target.writestr(name, source.read(name))
        for suffix in [".json", ".profile.json", ".profile.md"]:
            artifact = TEMPLATE_DIR / f"{template_id}{suffix}"
            if artifact.exists():
                target.write(artifact, arcname=artifact.name)
    return bundle_path


def _extract_attachment_text(filename: str, data: bytes) -> str:
    extension = Path(filename).suffix.lower()
    if extension == ".hwpx":
        return _extract_hwpx_attachment_text(data)
    if extension in TEXT_ATTACHMENT_EXTENSIONS:
        return _decode_text_attachment(data)[:MAX_ATTACHMENT_TEXT_CHARS]
    raise ValueError("지원하지 않는 첨부 형식입니다. txt, md, json, csv, xml, py, hwpx 파일을 사용하세요.")


def _decode_text_attachment(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _extract_hwpx_attachment_text(data: bytes) -> str:
    chunks: list[str] = []
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        section_files = sorted(name for name in zf.namelist() if name.startswith("Contents/section") and name.endswith(".xml"))
        for section in section_files:
            root = ET.fromstring(zf.read(section))
            for text in root.iter():
                if text.tag.endswith("}t") and text.text and text.text.strip():
                    chunks.append(text.text.strip())
    return "\n".join(chunks)[:MAX_ATTACHMENT_TEXT_CHARS]


def _web_feature_params(key: str) -> dict:
    if key == "font_size":
        return {"points": 12}
    if key == "table_background":
        return {"color": "#F2F5FA"}
    if key == "table_border":
        return {"type": "SOLID", "width": "0.12 mm", "color": "#404A5A"}
    if key == "font_color":
        return {"color": "#1F2933"}
    if key == "text_background":
        return {"color": "#FFF2CC"}
    if key == "strike_or_underline":
        return {"underline": True, "strike": False}
    if key == "character_emphasis":
        return {"bold": True}
    if key == "superscript_subscript":
        return {"type": "SUPERSCRIPT"}
    if key == "character_spacing":
        return {"spacing": "5"}
    if key == "paragraph_alignment":
        return {"horizontal": "JUSTIFY"}
    if key == "paragraph_spacing":
        return {"line_spacing_value": "160", "margin_left": "0", "margin_right": "0"}
    if key == "table_dimensions":
        return {"margin": "141", "cell_spacing": "0", "no_adjust": True}
    if key == "table_sort":
        return {"header_rows": 1}
    if key == "table_merge_split":
        return {"mode": "merge", "rows": 1, "cols": 2}
    if key == "table_rows":
        return {"mode": "append", "count": 1}
    if key == "document_blocks":
        return {"paragraphs": ["추가 검토사항"]}
    if key == "control_characters":
        return {}
    if key == "page_break":
        return {"insert_blank": True}
    return {}


def _guard_generated_output(template_path: Path, output_path: Path, profile_path: Path) -> dict:
    profile = profile_path if profile_path.exists() else None
    report = guard_template_output(template_path, output_path, profile=profile)
    if not report.passed:
        issue_text = "; ".join(f"{issue.code}: {issue.message}" for issue in report.issues[:5])
        raise ValueError(f"생성된 HWPX가 템플릿 구조 검증을 통과하지 못했습니다. {issue_text}")
    return report.to_dict()


def _feature_controls_html() -> str:
    controls = []
    for key, label, checked in WEB_FEATURE_OPTIONS:
        checked_attr = " checked" if checked else ""
        controls.append(f'<label class="toggle"><input class="feature" type="checkbox" value="{key}"{checked_attr}> {label}</label>')
    return "\n          ".join(controls)


def _parse_multipart(body: bytes, content_type: str) -> dict:
    match = re.search(r'boundary="?([^";]+)"?', content_type)
    if not match:
        raise ValueError("multipart boundary가 없습니다.")
    boundary = ("--" + match.group(1)).encode("utf-8")
    fields: dict[str, str | UploadedFile] = {}
    for raw_part in body.split(boundary):
        part = raw_part.strip(b"\r\n")
        if not part or part == b"--":
            continue
        if part.endswith(b"--"):
            part = part[:-2].rstrip(b"\r\n")
        if b"\r\n\r\n" not in part:
            continue
        header_blob, content = part.split(b"\r\n\r\n", 1)
        headers = header_blob.decode("utf-8", errors="replace")
        disposition = next((line for line in headers.split("\r\n") if line.lower().startswith("content-disposition:")), "")
        name_match = re.search(r'name="([^"]+)"', disposition)
        if not name_match:
            continue
        name = name_match.group(1)
        filename_match = re.search(r'filename="([^"]*)"', disposition)
        if filename_match:
            fields[name] = UploadedFile(filename=filename_match.group(1), value=content)
        else:
            fields[name] = content.decode("utf-8", errors="replace")
    return fields


def _index_html() -> str:
    return """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Qwen HWPX Agent</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #eef1f5;
      --panel: #ffffff;
      --panel-soft: #f7f9fc;
      --text: #17202c;
      --muted: #667085;
      --line: #d8dee8;
      --accent: #145fbf;
      --accent-strong: #0f4d9a;
      --ok: #0f766e;
      --err: #b42318;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      height: 100vh;
      overflow: hidden;
      font-family: "Segoe UI", "Malgun Gothic", Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
    }
    .app {
      display: grid;
      grid-template-columns: 260px minmax(420px, 1fr) 360px;
      height: 100vh;
      min-height: 640px;
    }
    aside, main, .right {
      min-height: 0;
      border-right: 1px solid var(--line);
      background: var(--panel);
    }
    .right { border-right: 0; border-left: 1px solid var(--line); }
    .sidebar, .right, main {
      display: flex;
      flex-direction: column;
    }
    .topbar {
      min-height: 64px;
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
    }
    h1, h2, h3 { margin: 0; letter-spacing: 0; }
    h1 { font-size: 17px; font-weight: 750; }
    h2 { font-size: 15px; font-weight: 750; }
    h3 { font-size: 13px; font-weight: 750; }
    .model {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 9px 10px;
      font: inherit;
      font-size: 12px;
      color: var(--text);
      background: white;
    }
    button, .button {
      border: 1px solid var(--accent);
      background: var(--accent);
      color: #fff;
      border-radius: 6px;
      padding: 9px 12px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 38px;
      white-space: nowrap;
    }
    button:hover, .button:hover { background: var(--accent-strong); }
    button.secondary {
      background: white;
      color: var(--accent);
    }
    button.secondary:hover { color: white; }
    button:disabled, .button.disabled {
      opacity: .45;
      pointer-events: none;
    }
    .small { font-size: 12px; color: var(--muted); line-height: 1.45; }
    .conversation-list {
      padding: 10px;
      overflow: auto;
      display: grid;
      gap: 8px;
    }
    .conversation {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      background: var(--panel-soft);
      text-align: left;
      color: var(--text);
      cursor: pointer;
    }
    .conversation.active {
      border-color: var(--accent);
      background: #eef5ff;
    }
    .conversation .title {
      font-size: 13px;
      font-weight: 700;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .conversation .meta { margin-top: 4px; font-size: 11px; color: var(--muted); }
    .chat {
      flex: 1;
      min-height: 0;
      overflow: auto;
      padding: 18px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      background: linear-gradient(#fbfcfe, #f4f7fb);
    }
    .message {
      width: min(760px, 92%);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px 14px;
      white-space: pre-wrap;
      line-height: 1.55;
      font-size: 14px;
      background: white;
    }
    .message.user {
      align-self: flex-end;
      background: #eaf3ff;
      border-color: #c8dcf5;
    }
    .message.assistant { align-self: flex-start; }
    .composer {
      border-top: 1px solid var(--line);
      padding: 12px;
      background: var(--panel);
      display: grid;
      grid-template-columns: auto 1fr auto;
      gap: 10px;
      align-items: end;
    }
    .attach-button {
      min-width: 42px;
      padding: 9px 10px;
    }
    .chat-file {
      display: none;
    }
    .attachment-chip {
      grid-column: 1 / -1;
      display: none;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      border: 1px solid #bcd7f5;
      border-radius: 6px;
      background: #eef6ff;
      color: var(--accent);
      padding: 8px 10px;
      font-size: 12px;
    }
    .attachment-chip.visible {
      display: flex;
    }
    .attachment-chip button {
      min-height: 28px;
      padding: 4px 8px;
      font-size: 12px;
    }
    textarea, input[type="file"], input[type="text"] {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      font: inherit;
      background: white;
      color: var(--text);
    }
    textarea {
      resize: none;
      min-height: 58px;
      max-height: 160px;
      padding: 10px 12px;
      line-height: 1.5;
    }
    input[type="file"], input[type="text"] { padding: 9px 10px; }
    .panel {
      border-bottom: 1px solid var(--line);
      padding: 14px;
    }
    .panel.grow {
      flex: 1;
      min-height: 0;
      overflow: auto;
    }
    .progress {
      display: grid;
      gap: 8px;
      margin-top: 12px;
    }
    .progress div {
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--panel-soft);
      padding: 8px 10px;
      font-size: 12px;
      color: var(--muted);
    }
    .progress div.ok { color: var(--ok); border-color: #b7e4dc; background: #eefaf7; }
    .progress div.err { color: var(--err); border-color: #f0b8b2; background: #fff4f2; }
    .status {
      min-height: 20px;
      margin-top: 10px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
      white-space: pre-wrap;
    }
    .status.ok { color: var(--ok); }
    .status.err { color: var(--err); }
    .preview {
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--panel-soft);
      padding: 10px;
      min-height: 90px;
      max-height: 170px;
      overflow: auto;
      white-space: pre-wrap;
      font-size: 12px;
      line-height: 1.5;
      color: var(--muted);
    }
    label {
      display: block;
      margin: 12px 0 6px;
      font-size: 12px;
      font-weight: 700;
    }
    .feature-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 6px 8px;
      max-height: 160px;
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px;
      background: var(--panel-soft);
    }
    .toggle {
      display: flex;
      align-items: center;
      gap: 6px;
      margin: 0;
      font-size: 12px;
      font-weight: 500;
      color: var(--muted);
    }
    .actions {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 10px;
    }
    .links a { color: var(--accent); text-decoration: none; margin-right: 8px; }
    @media (max-width: 980px) {
      body { overflow: auto; height: auto; }
      .app { grid-template-columns: 1fr; height: auto; min-height: 100vh; }
      aside, .right { min-height: 260px; }
      .chat { min-height: 420px; }
    }
  </style>
</head>
<body>
  <div class="app">
    <aside class="sidebar">
      <div class="topbar">
        <div>
          <h1>Qwen SLM Agent</h1>
          <div class="small">로컬 Qwen3-4B 기반</div>
        </div>
      </div>
      <div class="panel">
        <button id="newChatBtn" type="button">새 대화</button>
        <label for="model">모델</label>
        <input id="model" class="model" type="text" value="__DEFAULT_LOCAL_MODEL__" autocomplete="off">
      </div>
      <div id="conversationList" class="conversation-list"></div>
    </aside>

    <main>
      <div class="topbar">
        <div>
          <h2>기본 질문 답변 에이전트</h2>
          <div class="small">일반 질문은 채팅으로 답변하고, 공문서 생성은 우측 HWPX 자동화에서 처리합니다.</div>
        </div>
      </div>
      <div id="chatMessages" class="chat"></div>
      <form id="chatForm" class="composer">
        <button id="attachBtn" class="secondary attach-button" type="button" title="파일 첨부">첨부</button>
        <input id="chatFile" class="chat-file" type="file" accept=".txt,.md,.markdown,.json,.csv,.tsv,.xml,.html,.css,.js,.py,.toml,.yaml,.yml,.log,.hwpx">
        <textarea id="chatInput" placeholder="Qwen 에이전트에게 질문하세요. 예: 이 공문 작성 절차를 정리해줘."></textarea>
        <button id="sendBtn" type="submit">전송</button>
        <div id="attachmentChip" class="attachment-chip">
          <span id="attachmentText"></span>
          <button id="clearAttachmentBtn" class="secondary" type="button">제거</button>
        </div>
      </form>
    </main>

    <section class="right">
      <div class="panel">
        <h2>진행 상황</h2>
        <div id="progressLog" class="progress"></div>
      </div>

      <div class="panel grow">
        <h2>HWPX 자동화</h2>
        <form id="uploadForm">
          <label for="templateFile">문서 양식 업로드</label>
          <input id="templateFile" name="template" type="file" accept=".hwpx" required>
          <div class="actions">
            <button type="submit">양식 분석</button>
          </div>
        </form>
        <div id="uploadStatus" class="status"></div>
        <div id="templateLinks" class="links small"></div>
        <label>양식 분석 미리보기</label>
        <div id="templatePreview" class="preview"></div>

        <label class="toggle" style="margin-top:12px;"><input id="useLlm" type="checkbox" checked> Qwen으로 공문체 재가공</label>
        <label>공통 표준 기능</label>
        <div class="feature-grid">
          __FEATURE_CONTROLS__
        </div>
        <label for="docText">새 문서에 넣을 텍스트</label>
        <textarea id="docText" placeholder="팀장 지시사항, 보고 내용, 표 데이터를 입력하세요. Markdown 표도 사용할 수 있습니다."></textarea>
        <div class="actions">
          <button id="generateBtn" type="button" disabled>생성하기</button>
          <a id="saveBtn" class="button disabled" href="#">저장하기</a>
        </div>
        <div id="generateStatus" class="status"></div>
        <label>생성 미리보기</label>
        <div id="resultPreview" class="preview"></div>
      </div>
    </section>
  </div>

  <script>
    const defaultModel = "__DEFAULT_LOCAL_MODEL__";
    let templateId = "";
    let conversations = loadConversations();
    let activeId = conversations[0]?.id || createConversation().id;

    const conversationList = document.getElementById("conversationList");
    const chatMessages = document.getElementById("chatMessages");
    const chatForm = document.getElementById("chatForm");
    const chatInput = document.getElementById("chatInput");
    const modelInput = document.getElementById("model");
    const progressLog = document.getElementById("progressLog");
    const uploadForm = document.getElementById("uploadForm");
    const uploadStatus = document.getElementById("uploadStatus");
    const templateLinks = document.getElementById("templateLinks");
    const templatePreview = document.getElementById("templatePreview");
    const generateBtn = document.getElementById("generateBtn");
    const generateStatus = document.getElementById("generateStatus");
    const resultPreview = document.getElementById("resultPreview");
    const saveBtn = document.getElementById("saveBtn");
    const attachBtn = document.getElementById("attachBtn");
    const chatFile = document.getElementById("chatFile");
    const attachmentChip = document.getElementById("attachmentChip");
    const attachmentText = document.getElementById("attachmentText");
    const clearAttachmentBtn = document.getElementById("clearAttachmentBtn");
    let pendingAttachment = null;

    document.getElementById("newChatBtn").addEventListener("click", () => {
      activeId = createConversation().id;
      saveConversations();
      renderAll();
      setProgress(["새 대화를 시작했습니다."], "ok");
    });

    attachBtn.addEventListener("click", () => chatFile.click());
    clearAttachmentBtn.addEventListener("click", () => {
      pendingAttachment = null;
      chatFile.value = "";
      renderAttachment();
      setProgress(["첨부 파일을 제거했습니다."], "ok");
    });
    chatFile.addEventListener("change", async () => {
      const file = chatFile.files && chatFile.files[0];
      if (!file) return;
      setProgress(["파일 첨부 중", file.name], "ok");
      const data = new FormData();
      data.append("file", file);
      try {
        const res = await fetch("/api/attachment", { method: "POST", body: data });
        const json = await res.json();
        if (!res.ok) throw new Error(json.error || "첨부 실패");
        pendingAttachment = json;
        renderAttachment();
        setProgress(["파일 첨부 완료", `${json.filename} (${json.size} bytes)`, json.truncated ? "일부 내용만 문맥에 포함됩니다." : "전체 추출 텍스트를 문맥에 포함합니다."], "ok");
      } catch (error) {
        pendingAttachment = null;
        chatFile.value = "";
        renderAttachment();
        setProgress(["파일 첨부 실패", error.message], "err");
      }
    });

    chatForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      let content = chatInput.value.trim();
      if (pendingAttachment) {
        content = `${content || "첨부파일을 분석해줘."}\n\n[첨부파일: ${pendingAttachment.filename}]\n${pendingAttachment.text || "(추출 가능한 텍스트가 없습니다.)"}`;
      }
      if (!content) return;
      const conversation = activeConversation();
      conversation.messages.push({ role: "user", content });
      conversation.title = conversation.title === "새 대화" ? content.slice(0, 32) : conversation.title;
      chatInput.value = "";
      pendingAttachment = null;
      chatFile.value = "";
      renderAttachment();
      renderAll();
      setProgress(["질문 수신", "Qwen3-4B 호출 중"], "ok");
      try {
        const res = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ model: modelInput.value || defaultModel, messages: conversation.messages.slice(-12) })
        });
        const json = await res.json();
        if (!res.ok) throw new Error(json.error || "응답 생성 실패");
        conversation.messages.push({ role: "assistant", content: json.answer });
        saveConversations();
        renderAll();
        setProgress(json.progress || ["응답 생성 완료"], "ok");
      } catch (error) {
        conversation.messages.push({ role: "assistant", content: "오류: " + error.message });
        saveConversations();
        renderAll();
        setProgress(["응답 생성 실패", error.message], "err");
      }
    });

    uploadForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      uploadStatus.className = "status";
      uploadStatus.textContent = "양식을 분석하는 중입니다.";
      setProgress(["HWPX 양식 업로드", "XML 구조 분석 중"], "ok");
      const data = new FormData(uploadForm);
      const res = await fetch("/api/analyze", { method: "POST", body: data });
      const json = await res.json();
      if (!res.ok) {
        uploadStatus.className = "status err";
        uploadStatus.textContent = json.error || "업로드 실패";
        setProgress(["양식 분석 실패", uploadStatus.textContent], "err");
        return;
      }
      templateId = json.template_id;
      uploadStatus.className = "status ok";
      uploadStatus.textContent = `분석 완료: 텍스트 노드 ${json.text_node_count}개, 블록 ${json.block_count || 0}개`;
      templatePreview.textContent = json.preview_text || "";
      templateLinks.innerHTML = [
        `<a href="${json.profile_json_url}">profile_json_url</a>`,
        `<a href="${json.profile_markdown_url}">Markdown</a>`,
        `<a href="${json.analysis_json_url}">분석 JSON</a>`,
        `<a href="${json.xml_bundle_url}">xml_bundle_url</a>`
      ].join("");
      generateBtn.disabled = false;
      setProgress(["양식 저장 완료", "header.xml/section XML 분석 완료", "슬롯/스타일 프로필 생성 완료"], "ok");
    });

    generateBtn.addEventListener("click", async () => {
      generateStatus.className = "status";
      generateStatus.textContent = "HWPX를 생성하는 중입니다.";
      saveBtn.classList.add("disabled");
      setProgress(["텍스트 수신", "Qwen 공문체 재가공", "템플릿 슬롯 채우기"], "ok");
      const data = new FormData();
      data.append("template_id", templateId);
      data.append("text", document.getElementById("docText").value);
      data.append("model", modelInput.value || defaultModel);
      data.append("use_llm", document.getElementById("useLlm").checked ? "true" : "false");
      data.append("features", Array.from(document.querySelectorAll(".feature:checked")).map(el => el.value).join(","));
      const res = await fetch("/api/generate", { method: "POST", body: data });
      const json = await res.json();
      if (!res.ok) {
        generateStatus.className = "status err";
        generateStatus.textContent = json.error || "생성 실패";
        setProgress(["HWPX 생성 실패", generateStatus.textContent], "err");
        return;
      }
      const guard = json.structure_guard || {};
      generateStatus.className = "status ok";
      generateStatus.textContent = `생성 완료 / 공통 기능 ${(json.features || []).length}개 / 구조검증 ${guard.passed ? "통과" : "미확인"}`;
      resultPreview.textContent = json.preview_text || "";
      saveBtn.href = json.download_url;
      saveBtn.classList.remove("disabled");
      setProgress(["HWPX 생성 완료", `구조검증: 슬롯 ${guard.slot_style_checks || 0}개, 표 ${guard.table_style_checks || 0}개`, "저장 준비 완료"], "ok");
    });

    function createConversation() {
      const item = { id: crypto.randomUUID(), title: "새 대화", messages: [
        { role: "assistant", content: "Qwen3-4B 로컬 에이전트입니다. 일반 질문에 답변하고, 우측 HWPX 자동화 패널로 공문서 양식 분석과 새 문서 생성을 도와드립니다." }
      ] };
      conversations.unshift(item);
      return item;
    }
    function activeConversation() {
      return conversations.find(item => item.id === activeId) || conversations[0];
    }
    function renderAll() {
      renderConversationList();
      renderMessages();
    }
    function renderConversationList() {
      conversationList.innerHTML = conversations.map(item => `
        <div class="conversation ${item.id === activeId ? "active" : ""}" data-id="${item.id}">
          <div class="title">${escapeHtml(item.title)}</div>
          <div class="meta">${item.messages.length}개 메시지</div>
        </div>
      `).join("");
      conversationList.querySelectorAll(".conversation").forEach(el => {
        el.addEventListener("click", () => {
          activeId = el.dataset.id;
          renderAll();
        });
      });
    }
    function renderMessages() {
      const conversation = activeConversation();
      chatMessages.innerHTML = conversation.messages.map(message => `<div class="message ${message.role}">${escapeHtml(message.content)}</div>`).join("");
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    function renderAttachment() {
      if (!pendingAttachment) {
        attachmentChip.classList.remove("visible");
        attachmentText.textContent = "";
        return;
      }
      attachmentChip.classList.add("visible");
      attachmentText.textContent = `${pendingAttachment.filename} 첨부됨`;
    }
    function setProgress(items, tone) {
      progressLog.innerHTML = items.map(item => `<div class="${tone || ""}">${escapeHtml(item)}</div>`).join("");
    }
    function loadConversations() {
      try {
        const value = JSON.parse(localStorage.getItem("qwen-agent-conversations") || "[]");
        return Array.isArray(value) ? value : [];
      } catch {
        return [];
      }
    }
    function saveConversations() {
      localStorage.setItem("qwen-agent-conversations", JSON.stringify(conversations.slice(0, 20)));
    }
    function escapeHtml(value) {
      return String(value).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
    }
    renderAll();
    setProgress(["대기 중", "Qwen3-4B 기본 모델 준비", "HWPX 자동화 준비"], "ok");
  </script>
</body>
</html>""".replace("__FEATURE_CONTROLS__", _feature_controls_html()).replace("__DEFAULT_LOCAL_MODEL__", html.escape(DEFAULT_LOCAL_MODEL))
    return """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>범피스 오피스 HWPX 자동화</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --text: #1f2933;
      --muted: #6b7280;
      --line: #d9dee7;
      --accent: #1f6feb;
      --accent-strong: #1558c0;
      --ok: #0f7b54;
      --err: #b42318;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", "Malgun Gothic", Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
    }
    header {
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }
    .wrap {
      width: min(1120px, calc(100vw - 32px));
      margin: 0 auto;
    }
    header .wrap {
      display: flex;
      align-items: center;
      justify-content: space-between;
      min-height: 64px;
      gap: 16px;
    }
    h1 {
      margin: 0;
      font-size: 20px;
      font-weight: 700;
      letter-spacing: 0;
    }
    main {
      padding: 24px 0 40px;
    }
    .grid {
      display: grid;
      grid-template-columns: 360px 1fr;
      gap: 16px;
      align-items: start;
    }
    section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
    }
    h2 {
      margin: 0 0 12px;
      font-size: 16px;
      font-weight: 700;
    }
    label {
      display: block;
      margin: 14px 0 6px;
      font-size: 13px;
      font-weight: 600;
    }
    input[type="file"], input[type="text"], textarea {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      color: var(--text);
      font: inherit;
    }
    input[type="file"] { padding: 10px; }
    input[type="text"] { padding: 10px 12px; }
    textarea {
      min-height: 420px;
      resize: vertical;
      padding: 12px;
      line-height: 1.55;
    }
    .actions {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 14px;
    }
    button, .button {
      border: 1px solid var(--accent);
      background: var(--accent);
      color: white;
      border-radius: 6px;
      padding: 10px 14px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 40px;
    }
    button.secondary {
      background: #fff;
      color: var(--accent);
    }
    button:disabled, .button.disabled {
      opacity: .45;
      pointer-events: none;
      cursor: default;
    }
    button:hover, .button:hover { background: var(--accent-strong); }
    button.secondary:hover { color: #fff; }
    .status {
      margin-top: 12px;
      min-height: 22px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.5;
      white-space: pre-wrap;
    }
    .status.ok { color: var(--ok); }
    .status.err { color: var(--err); }
    .preview {
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fbfcfe;
      padding: 12px;
      min-height: 160px;
      max-height: 360px;
      overflow: auto;
      white-space: pre-wrap;
      font-size: 13px;
      line-height: 1.55;
    }
    .meta {
      display: grid;
      gap: 8px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.5;
    }
    .toggle {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-top: 12px;
      color: var(--muted);
      font-size: 13px;
    }
    .feature-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      column-gap: 12px;
    }
    @media (max-width: 860px) {
      .grid { grid-template-columns: 1fr; }
      textarea { min-height: 300px; }
    }
  </style>
</head>
<body>
  <header>
    <div class="wrap">
      <h1>범피스 오피스 HWPX 자동화</h1>
      <div class="meta">업로드 양식 기반 생성</div>
    </div>
  </header>
  <main class="wrap">
    <div class="grid">
      <section>
        <h2>문서 양식 업로드</h2>
        <form id="uploadForm">
          <input id="templateFile" name="template" type="file" accept=".hwpx" required>
          <div class="actions">
            <button type="submit">문서 양식 업로드</button>
          </div>
        </form>
        <div id="uploadStatus" class="status"></div>
        <label>양식 분석 결과</label>
        <div id="templateMeta" class="meta"></div>
        <label>양식 텍스트 미리보기</label>
        <div id="templatePreview" class="preview"></div>
      </section>

      <section>
        <h2>텍스트 입력</h2>
        <label for="model">Ollama 모델</label>
        <input id="model" type="text" value="__DEFAULT_LOCAL_MODEL__" autocomplete="off">
        <label class="toggle"><input id="useLlm" type="checkbox" checked> Ollama로 공문체 재가공</label>
        <label>공통 표준 기능</label>
        <div class="feature-grid">
          __FEATURE_CONTROLS__
        </div>
        <label for="textInput">팀장 지시사항 또는 원문</label>
        <textarea id="textInput" placeholder="여기에 작성할 내용을 붙여넣으세요."></textarea>
        <div class="actions">
          <button id="generateBtn" disabled>생성하기</button>
          <a id="saveBtn" class="button disabled" href="#">저장하기</a>
        </div>
        <div id="generateStatus" class="status"></div>
        <label>생성 미리보기</label>
        <div id="resultPreview" class="preview"></div>
      </section>
    </div>
  </main>
  <script>
    let templateId = "";
    const uploadForm = document.getElementById("uploadForm");
    const uploadStatus = document.getElementById("uploadStatus");
    const templateMeta = document.getElementById("templateMeta");
    const templatePreview = document.getElementById("templatePreview");
    const generateBtn = document.getElementById("generateBtn");
    const generateStatus = document.getElementById("generateStatus");
    const resultPreview = document.getElementById("resultPreview");
    const saveBtn = document.getElementById("saveBtn");

    uploadForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      uploadStatus.className = "status";
      uploadStatus.textContent = "양식을 분석하는 중입니다.";
      const data = new FormData(uploadForm);
      const res = await fetch("/api/analyze", { method: "POST", body: data });
      const json = await res.json();
      if (!res.ok) {
        uploadStatus.className = "status err";
        uploadStatus.textContent = json.error || "업로드 실패";
        return;
      }
      templateId = json.template_id;
      uploadStatus.className = "status ok";
      uploadStatus.textContent = "양식 분석 완료";
      templateMeta.innerHTML = [
        `파일: ${escapeHtml(json.filename)}`,
        `섹션: ${json.section_files.length}개`,
        `텍스트 노드: ${json.text_node_count}개`,
        `블록: ${json.block_count || 0}개 / 슬롯 후보: ${(json.slots || []).length}개`,
        `글자 스타일: ${json.style_summary.char_pr_count || 0}개 / 문단 스타일: ${json.style_summary.para_pr_count || 0}개`,
        `표: ${json.style_summary.table_count || 0}개 / 셀: ${json.style_summary.cell_count || 0}개`,
        `제목 후보: ${escapeHtml((json.title_candidates || []).slice(0, 3).join(", ") || "-")}`,
        `양식 프로필: <a href="${json.profile_json_url}">JSON</a> / <a href="${json.profile_markdown_url}">Markdown</a> / <a href="${json.analysis_json_url}">분석 JSON</a> / <a href="${json.xml_bundle_url}">XML ZIP</a>`
      ].map(item => `<div>${item}</div>`).join("");
      templatePreview.textContent = json.preview_text || "";
      generateBtn.disabled = false;
    });

    generateBtn.addEventListener("click", async () => {
      generateStatus.className = "status";
      generateStatus.textContent = "HWPX를 생성하는 중입니다.";
      saveBtn.classList.add("disabled");
      const data = new FormData();
      data.append("template_id", templateId);
      data.append("text", document.getElementById("textInput").value);
      data.append("model", document.getElementById("model").value);
      data.append("use_llm", document.getElementById("useLlm").checked ? "true" : "false");
      data.append("features", Array.from(document.querySelectorAll(".feature:checked")).map(el => el.value).join(","));
      const res = await fetch("/api/generate", { method: "POST", body: data });
      const json = await res.json();
      if (!res.ok) {
        generateStatus.className = "status err";
        generateStatus.textContent = json.error || "생성 실패";
        return;
      }
      generateStatus.className = "status ok";
      const featureText = (json.features || []).length ? ` / 공통 기능 ${json.features.length}개 적용` : "";
      const guard = json.structure_guard || {};
      const guardText = guard.passed ? ` / 구조검증 통과(${guard.slot_style_checks || 0} 슬롯, ${guard.table_style_checks || 0} 표)` : "";
      generateStatus.textContent = (json.llm_used ? "Ollama 재가공 후 HWPX 생성 완료" : "기본 파서로 HWPX 생성 완료") + featureText + guardText;
      resultPreview.textContent = json.preview_text || "";
      saveBtn.href = json.download_url;
      saveBtn.classList.remove("disabled");
    });

    function escapeHtml(value) {
      return String(value).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
    }
  </script>
</body>
</html>""".replace("__FEATURE_CONTROLS__", _feature_controls_html()).replace("__DEFAULT_LOCAL_MODEL__", html.escape(DEFAULT_LOCAL_MODEL))


if __name__ == "__main__":
    main()
