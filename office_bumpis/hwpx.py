from __future__ import annotations

import json
import shutil
import subprocess
import zipfile
from pathlib import Path

from .models import OfficialDocument
from .renderer import render_markdown


class HwpxExportError(RuntimeError):
    pass


def export_hwpx(
    document: OfficialDocument,
    output_path: str | Path,
    *,
    markdown_path: str | Path | None = None,
    timeout: int = 180,
) -> Path:
    markdown = render_markdown(document)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if markdown_path:
        md_path = Path(markdown_path)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(markdown, encoding="utf-8")
    markdown_to_hwpx(markdown, output, timeout=timeout)
    verify_hwpx(output)
    return output


def markdown_to_hwpx(markdown: str, output_path: Path, *, timeout: int = 180) -> None:
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if not npx:
        raise HwpxExportError("npx was not found. Install Node.js or add npx to PATH before exporting HWPX.")
    script = f"""
import {{ markdownToHwpx }} from "kordoc";
import {{ writeFileSync }} from "node:fs";

const markdown = {json.dumps(markdown, ensure_ascii=False)};
const outputPath = {json.dumps(str(output_path), ensure_ascii=False)};
const hwpx = await markdownToHwpx(markdown);
writeFileSync(outputPath, Buffer.from(hwpx));
"""
    cmd = [
        npx,
        "--yes",
        "--package",
        "kordoc",
        "--package",
        "pdfjs-dist",
        "node",
        "--input-type=module",
        "-",
    ]
    result = subprocess.run(
        cmd,
        input=script,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        raise HwpxExportError(result.stderr.strip() or result.stdout.strip() or "HWPX export failed")


def verify_hwpx(path: Path) -> None:
    if not path.exists() or path.stat().st_size == 0:
        raise HwpxExportError(f"HWPX file was not created: {path}")
    try:
        with zipfile.ZipFile(path) as zf:
            names = set(zf.namelist())
            required = {"mimetype", "Contents/header.xml", "Contents/section0.xml", "Contents/content.hpf"}
            missing = required - names
            if missing:
                raise HwpxExportError(f"HWPX package is missing entries: {', '.join(sorted(missing))}")
            mimetype = zf.read("mimetype").decode("utf-8", errors="replace").strip()
            if mimetype != "application/hwp+zip":
                raise HwpxExportError(f"unexpected HWPX mimetype: {mimetype}")
    except zipfile.BadZipFile as exc:
        raise HwpxExportError(f"invalid HWPX zip package: {path}") from exc
