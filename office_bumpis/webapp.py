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

from .hwpx_features import apply_standard_features
from .llm_adapter import DEFAULT_LOCAL_MODEL
from .profile_filler import fill_hwpx_with_profile
from .structure_guard import guard_template_output
from .template_engine import analyze_hwpx_template, draft_from_text, fill_hwpx_template, load_analysis, save_analysis
from .template_profile import learn_template_profile, load_profile, render_profile_markdown, save_profile


RUNTIME_DIR = Path(".runtime")
TEMPLATE_DIR = RUNTIME_DIR / "templates"
OUTPUT_DIR = RUNTIME_DIR / "outputs"


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

    def _parse_form(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        content_type = self.headers.get("Content-Type", "")
        if content_type.startswith("multipart/form-data"):
            return _parse_multipart(body, content_type)
        payload = body.decode("utf-8")
        return {key: value[-1] for key, value in parse_qs(payload).items()}

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
