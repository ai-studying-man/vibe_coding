from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .hwpx import export_hwpx
from .llm_adapter import OpenCompatibleLLM
from .models import OfficialDocument
from .profiles import build_profile_document, profile_names, profile_prompt
from .renderer import render_markdown
from .templates import inspect_hwpx_templates, render_inventory_markdown, write_inventory


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="office-bumpis")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Generate Markdown/HWPX from normalized JSON.")
    gen.add_argument("json_path")
    gen.add_argument("-o", "--output", required=True)
    gen.add_argument("--markdown")

    draft = sub.add_parser("draft", help="Draft normalized JSON with an OpenAI-compatible local LLM, then export.")
    draft.add_argument("prompt_path")
    draft.add_argument("-o", "--output", required=True)
    draft.add_argument("--json", dest="json_output")
    draft.add_argument("--markdown")
    draft.add_argument("--base-url")
    draft.add_argument("--model")
    draft.add_argument("--profile", choices=profile_names(), help="Expand LLM seed output with a deterministic document profile.")

    md = sub.add_parser("markdown", help="Render normalized JSON to Markdown only.")
    md.add_argument("json_path")
    md.add_argument("-o", "--output", required=True)

    inventory = sub.add_parser("inspect-templates", help="Inspect HWPX templates and write a reusable inventory.")
    inventory.add_argument("path")
    inventory.add_argument("-o", "--output", help="JSON output path.")
    inventory.add_argument("--markdown", help="Markdown output path.")

    learn = sub.add_parser("learn-template", help="Learn slots, blocks, and styles from one HWPX template.")
    learn.add_argument("path")
    learn.add_argument("-o", "--output", required=True, help="JSON profile output path.")
    learn.add_argument("--markdown", help="Markdown summary output path.")

    generate_from_template = sub.add_parser(
        "generate-from-template",
        help="Generate an HWPX directly from one HWPX template and raw text.",
    )
    generate_from_template.add_argument("template")
    generate_from_template.add_argument("text_path")
    generate_from_template.add_argument("-o", "--output", required=True)
    generate_from_template.add_argument("--profile-out", help="Optional learned profile JSON output path.")
    generate_from_template.add_argument("--analysis-out", help="Optional template analysis JSON output path.")
    generate_from_template.add_argument("--markdown-profile", help="Optional learned profile Markdown output path.")
    generate_from_template.add_argument("--draft-json", help="Optional generated DraftContent JSON output path.")
    generate_from_template.add_argument("--base-url")
    generate_from_template.add_argument("--model")
    generate_from_template.add_argument("--use-llm", action="store_true")
    generate_from_template.add_argument("--feature", action="append", default=[], help="Feature key. Repeat for multiple features.")
    generate_from_template.add_argument(
        "--features-json",
        action="append",
        default=[],
        help="Feature operation JSON array, @file, or JSON file path. Repeat to concatenate operations.",
    )
    generate_from_template.add_argument("--color", help="Color for font/table features, e.g. #005BAC.")
    generate_from_template.add_argument("--points", type=float, help="Font size in points for font_size.")
    generate_from_template.add_argument("--font-face", help="Font face for font_family, e.g. 함초롬바탕 or 휴먼명조.")
    generate_from_template.add_argument("--latin-font-face", help="Optional Latin font face for font_family.")
    generate_from_template.add_argument("--character-width", help="Character width ratio for character_width, e.g. 92 or 100.")
    generate_from_template.add_argument("--page-margin", type=float, help="Default page margin in millimeters for page_layout.")
    generate_from_template.add_argument("--page-left", type=float, help="Left page margin in millimeters for page_layout.")
    generate_from_template.add_argument("--page-right", type=float, help="Right page margin in millimeters for page_layout.")
    generate_from_template.add_argument("--page-top", type=float, help="Top page margin in millimeters for page_layout.")
    generate_from_template.add_argument("--page-bottom", type=float, help="Bottom page margin in millimeters for page_layout.")
    generate_from_template.add_argument("--page-header", type=float, help="Header margin in millimeters for page_layout.")
    generate_from_template.add_argument("--page-footer", type=float, help="Footer margin in millimeters for page_layout.")
    generate_from_template.add_argument("--page-orientation", choices=["portrait", "landscape"], help="Page orientation for page_layout.")
    generate_from_template.add_argument("--page-border-offset", type=float, help="Page border offset in millimeters for page_border.")
    generate_from_template.add_argument("--page-border-color", help="Page border color for page_border.")
    generate_from_template.add_argument("--page-border-width", default="0.1 mm", help="Page border width for page_border.")
    generate_from_template.add_argument("--page-border-type", default="SOLID", help="Page border type for page_border.")
    generate_from_template.add_argument("--remove-page-border", action="store_true", help="Remove page border lines for page_border.")
    generate_from_template.add_argument("--page-number-mode", choices=["show", "hide", "reset"], default="show", help="Mode for page_number.")
    generate_from_template.add_argument("--page-number-start", type=int, help="Start page number for page_number.")
    generate_from_template.add_argument("--row-mode", choices=["append", "delete"], default="append", help="Mode for table_rows.")
    generate_from_template.add_argument("--row-count", type=int, default=1, help="Number of rows for table_rows.")
    generate_from_template.add_argument("--row-values", action="append", help="Pipe-delimited row values for table_rows. Repeat for multiple rows.")
    generate_from_template.add_argument("--column-mode", choices=["append", "delete"], default="append", help="Mode for table_columns.")
    generate_from_template.add_argument("--column-position", choices=["left", "right"], default="right", help="Side for table_columns.")
    generate_from_template.add_argument("--column-count", type=int, default=1, help="Number of columns for table_columns.")
    generate_from_template.add_argument("--column-values", action="append", help="Pipe-delimited column cell values for table_columns. Repeat for multiple columns.")
    generate_from_template.add_argument("--all-tables", action="store_true", help="Apply table row/column operations to every table instead of the first table.")
    generate_from_template.add_argument("--guard-json", help="Optional structure guard JSON report output path.")

    preset = sub.add_parser("preset", help="Create normalized official-document JSON from an extracted workflow profile.")
    preset.add_argument("profile", choices=profile_names())
    preset.add_argument("-o", "--output", required=True, help="JSON output path.")
    preset.add_argument("--seed", help="Optional seed JSON with title, sender, recipients, and section content.")
    preset.add_argument("--title")
    preset.add_argument("--sender")
    preset.add_argument("--recipient", action="append", dest="recipients")
    preset.add_argument("--date")
    preset.add_argument("--registration-number")
    preset.add_argument("--contact")

    serve = sub.add_parser("serve", help="Run the local HWPX template automation web app.")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)

    features = sub.add_parser("features", help="List normalized standard features recovered from the EXE.")
    features.add_argument("--json", action="store_true")

    coverage = sub.add_parser("feature-coverage", help="Analyze recovered EXE symbols against standard feature groups.")
    coverage.add_argument("source_root", nargs="?", default="recovered_source")
    coverage.add_argument("-o", "--output", help="JSON report output path.")
    coverage.add_argument("--markdown", help="Markdown report output path.")

    apply_feature = sub.add_parser("apply-feature", help="Apply normalized standard HWPX features to a document.")
    apply_feature.add_argument("input")
    apply_feature.add_argument("-o", "--output", required=True)
    apply_feature.add_argument("--feature", action="append", default=[], help="Feature key. Repeat for multiple features.")
    apply_feature.add_argument(
        "--features-json",
        action="append",
        default=[],
        help="Feature operation JSON array, @file, or JSON file path. Repeat to concatenate operations.",
    )
    apply_feature.add_argument("--color", help="Color for font/table features, e.g. #005BAC.")
    apply_feature.add_argument("--points", type=float, help="Font size in points for font_size.")
    apply_feature.add_argument("--font-face", help="Font face for font_family, e.g. 함초롬바탕 or 휴먼명조.")
    apply_feature.add_argument("--latin-font-face", help="Optional Latin font face for font_family.")
    apply_feature.add_argument("--page-margin", type=float, help="Default page margin in millimeters for page_layout.")
    apply_feature.add_argument("--page-left", type=float, help="Left page margin in millimeters for page_layout.")
    apply_feature.add_argument("--page-right", type=float, help="Right page margin in millimeters for page_layout.")
    apply_feature.add_argument("--page-top", type=float, help="Top page margin in millimeters for page_layout.")
    apply_feature.add_argument("--page-bottom", type=float, help="Bottom page margin in millimeters for page_layout.")
    apply_feature.add_argument("--page-header", type=float, help="Header margin in millimeters for page_layout.")
    apply_feature.add_argument("--page-footer", type=float, help="Footer margin in millimeters for page_layout.")
    apply_feature.add_argument("--page-orientation", choices=["portrait", "landscape"], help="Page orientation for page_layout.")
    apply_feature.add_argument("--page-border-offset", type=float, help="Page border offset in millimeters for page_border.")
    apply_feature.add_argument("--page-border-color", help="Page border color for page_border.")
    apply_feature.add_argument("--page-border-width", default="0.1 mm", help="Page border width for page_border.")
    apply_feature.add_argument("--page-border-type", default="SOLID", help="Page border type for page_border.")
    apply_feature.add_argument("--remove-page-border", action="store_true", help="Remove page border lines for page_border.")
    apply_feature.add_argument("--page-number-mode", choices=["show", "hide", "reset"], default="show", help="Mode for page_number.")
    apply_feature.add_argument("--page-number-start", type=int, help="Start page number for page_number.")
    apply_feature.add_argument("--border-width", default="0.1 mm")
    apply_feature.add_argument("--border-type", default="SOLID")
    apply_feature.add_argument("--strike", action="store_true")
    apply_feature.add_argument("--no-underline", action="store_true")
    apply_feature.add_argument("--character-width", help="Character width ratio for character_width, e.g. 92 or 100.")
    apply_feature.add_argument("--horizontal", default="CENTER", help="Paragraph alignment for paragraph_alignment.")
    apply_feature.add_argument("--line-spacing", default="160", help="Line spacing value for paragraph_spacing.")
    apply_feature.add_argument("--margin", help="Cell margin for table_dimensions.")
    apply_feature.add_argument("--cell-width", help="Cell width for table_dimensions.")
    apply_feature.add_argument("--cell-height", help="Cell height for table_dimensions.")
    apply_feature.add_argument("--numeric", action="store_true", help="Use numeric table sort.")
    apply_feature.add_argument("--descending", action="store_true", help="Sort descending for table_sort.")
    apply_feature.add_argument("--header-rows", type=int, default=1)
    apply_feature.add_argument("--paragraph", action="append", help="Paragraph text to append with document_blocks.")
    apply_feature.add_argument("--merge-cols", type=int, default=2)
    apply_feature.add_argument("--merge-rows", type=int, default=1)
    apply_feature.add_argument("--split", action="store_true", help="Split merged cells for table_merge_split.")
    apply_feature.add_argument("--row-mode", choices=["append", "delete"], default="append", help="Mode for table_rows.")
    apply_feature.add_argument("--row-count", type=int, default=1, help="Number of rows for table_rows.")
    apply_feature.add_argument("--row-values", action="append", help="Pipe-delimited row values for table_rows. Repeat for multiple rows.")
    apply_feature.add_argument("--column-mode", choices=["append", "delete"], default="append", help="Mode for table_columns.")
    apply_feature.add_argument("--column-position", choices=["left", "right"], default="right", help="Side for table_columns.")
    apply_feature.add_argument("--column-count", type=int, default=1, help="Number of columns for table_columns.")
    apply_feature.add_argument("--column-values", action="append", help="Pipe-delimited column cell values for table_columns. Repeat for multiple columns.")
    apply_feature.add_argument("--all-tables", action="store_true", help="Apply table row/column operations to every table instead of the first table.")

    fill_profile = sub.add_parser("fill-profile", help="Fill an HWPX template using a learned slot profile.")
    fill_profile.add_argument("template")
    fill_profile.add_argument("profile")
    fill_profile.add_argument("json_path")
    fill_profile.add_argument("-o", "--output", required=True)

    guard_output = sub.add_parser("guard-output", help="Verify that a generated HWPX preserves the learned template structure.")
    guard_output.add_argument("template")
    guard_output.add_argument("output")
    guard_output.add_argument("--profile", help="Optional learned profile JSON. If omitted, the template is learned on the fly.")
    guard_output.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "generate":
        document = _load_document(args.json_path)
        export_hwpx(document, args.output, markdown_path=args.markdown)
        print(f"created {args.output}")
    elif args.command == "draft":
        prompt = Path(args.prompt_path).read_text(encoding="utf-8")
        client = OpenCompatibleLLM(base_url=args.base_url, model=args.model)
        if args.profile:
            prompt = prompt + "\n\n" + profile_prompt(args.profile)
        data = client.draft_document_json(prompt)
        document = build_profile_document(args.profile, data) if args.profile else OfficialDocument.from_mapping(data)
        normalized_data = asdict(document)
        if args.json_output:
            out = Path(args.json_output)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(normalized_data, ensure_ascii=False, indent=2), encoding="utf-8")
        export_hwpx(document, args.output, markdown_path=args.markdown)
        print(f"created {args.output}")
    elif args.command == "markdown":
        document = _load_document(args.json_path)
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_markdown(document), encoding="utf-8")
        print(f"created {args.output}")
    elif args.command == "inspect-templates":
        templates = inspect_hwpx_templates(args.path)
        if args.output or args.markdown:
            write_inventory(templates, json_path=args.output, markdown_path=args.markdown)
            if args.output:
                print(f"created {args.output}")
            if args.markdown:
                print(f"created {args.markdown}")
        else:
            print(render_inventory_markdown(templates))
    elif args.command == "learn-template":
        from .template_profile import learn_template_profile, render_profile_markdown, save_profile

        profile = learn_template_profile(args.path)
        save_profile(args.output, profile)
        print(f"created {args.output}")
        if args.markdown:
            out = Path(args.markdown)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(render_profile_markdown(profile), encoding="utf-8")
            print(f"created {args.markdown}")
    elif args.command == "generate-from-template":
        from .hwpx_features import apply_standard_features
        from .profile_filler import fill_hwpx_with_profile
        from .structure_guard import guard_template_output
        from .template_engine import analyze_hwpx_template, draft_from_text, save_analysis
        from .template_profile import learn_template_profile, render_profile_markdown, save_profile

        template = Path(args.template)
        text = Path(args.text_path).read_text(encoding="utf-8")
        output = Path(args.output)
        analysis = analyze_hwpx_template(template)
        profile = learn_template_profile(template)
        feature_operations = _feature_operations_from_args(args)
        draft_content = draft_from_text(
            text,
            analysis,
            model=args.model,
            base_url=args.base_url,
            use_llm=args.use_llm,
            profile=profile,
        )
        raw_output = output.with_suffix(".raw.hwpx") if feature_operations else output
        report = fill_hwpx_with_profile(template, raw_output, draft_content, profile)
        guard = guard_template_output(template, raw_output, profile=profile)
        if not guard.passed:
            raise SystemExit(json.dumps(guard.to_dict(), ensure_ascii=False, indent=2))
        if feature_operations:
            apply_standard_features(raw_output, output, feature_operations)
        if args.profile_out:
            save_profile(args.profile_out, profile)
            print(f"created {args.profile_out}")
        if args.analysis_out:
            save_analysis(args.analysis_out, analysis)
            print(f"created {args.analysis_out}")
        if args.markdown_profile:
            out = Path(args.markdown_profile)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(render_profile_markdown(profile), encoding="utf-8")
            print(f"created {args.markdown_profile}")
        if args.draft_json:
            out = Path(args.draft_json)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(asdict(draft_content), ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"created {args.draft_json}")
        if args.guard_json:
            out = Path(args.guard_json)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(guard.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"created {args.guard_json}")
        print(f"created {args.output}")
        print(json.dumps({"fill": asdict(report), "guard": guard.to_dict()}, ensure_ascii=False))
    elif args.command == "preset":
        seed = _load_seed(args.seed)
        for key in ["title", "sender", "date", "contact"]:
            value = getattr(args, key)
            if value:
                seed[key] = value
        if args.recipients:
            seed["recipients"] = args.recipients
        if args.registration_number:
            seed["registration_number"] = args.registration_number
        document = build_profile_document(args.profile, seed)
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(asdict(document), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"created {args.output}")
    elif args.command == "serve":
        from .webapp import run

        run(args.host, args.port)
    elif args.command == "features":
        from .standard_features import feature_inventory

        inventory = feature_inventory()
        if args.json:
            print(json.dumps(inventory, ensure_ascii=False, indent=2))
        else:
            for item in inventory:
                status = "implemented" if item["implemented"] else "planned"
                print(f"{item['key']}\t{item['category']}\t{status}\t{item['label']}")
    elif args.command == "feature-coverage":
        from .feature_coverage import analyze_recovered_feature_coverage, render_coverage_markdown

        report = analyze_recovered_feature_coverage(args.source_root)
        if args.output:
            out = Path(args.output)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(report.to_json(), encoding="utf-8")
            print(f"created {args.output}")
        if args.markdown:
            out = Path(args.markdown)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(render_coverage_markdown(report), encoding="utf-8")
            print(f"created {args.markdown}")
        if not args.output and not args.markdown:
            print(report.to_json())
    elif args.command == "apply-feature":
        from .hwpx_features import apply_standard_features

        operations = _feature_operations_from_args(args)
        if not operations:
            raise SystemExit("at least one --feature or --features-json operation is required")
        apply_standard_features(args.input, args.output, operations)
        print(f"created {args.output}")
    elif args.command == "fill-profile":
        from .profile_filler import fill_hwpx_with_profile
        from .template_engine import DraftContent
        from .template_profile import load_profile

        data = json.loads(Path(args.json_path).read_text(encoding="utf-8-sig"))
        draft_content = DraftContent(
            title=str(data.get("title") or ""),
            paragraphs=[str(item) for item in data.get("paragraphs", data.get("body", []))],
            attachments=[str(item) for item in data.get("attachments", [])],
            tables=_normalize_tables(data.get("tables", [])),
        )
        report = fill_hwpx_with_profile(args.template, args.output, draft_content, load_profile(args.profile))
        print(f"created {args.output}")
        print(json.dumps(asdict(report), ensure_ascii=False))
    elif args.command == "guard-output":
        from .structure_guard import guard_template_output

        report = guard_template_output(args.template, args.output, profile=args.profile)
        if args.json:
            print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
        else:
            status = "passed" if report.passed else "failed"
            print(f"structure guard {status}")
            print(f"slots checked: {report.slot_style_checks}, tables checked: {report.table_style_checks}")
            for issue in report.issues:
                print(f"{issue.code}: {issue.message}")
        if not report.passed:
            raise SystemExit(1)


def _load_document(path: str | Path) -> OfficialDocument:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return OfficialDocument.from_mapping(data)


def _load_seed(path: str | None) -> dict:
    if not path:
        return {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("seed JSON must be an object")
    return data


def _normalize_tables(value) -> list[list[list[str]]]:
    if not isinstance(value, list):
        return []
    tables: list[list[list[str]]] = []
    for table in value:
        rows = table.get("rows", []) if isinstance(table, dict) else table
        if not isinstance(rows, list):
            continue
        normalized = []
        for row in rows:
            if isinstance(row, list):
                normalized.append([str(cell) for cell in row])
        if normalized:
            tables.append(normalized)
    return tables


def _feature_params_from_args(feature: str, args) -> dict:
    params = {}
    if getattr(args, "color", None):
        params["color"] = args.color
    if getattr(args, "points", None):
        params["points"] = args.points
    if feature == "table_border":
        params["width"] = getattr(args, "border_width", None) or "0.1 mm"
        params["type"] = getattr(args, "border_type", None) or "SOLID"
    if feature == "font_family":
        params["face"] = getattr(args, "font_face", None) or "함초롬바탕"
        if getattr(args, "latin_font_face", None):
            params["latin_face"] = args.latin_font_face
    if feature == "page_layout":
        if getattr(args, "page_margin", None) is not None:
            params["margin"] = args.page_margin
        for name, attr in [
            ("left", "page_left"),
            ("right", "page_right"),
            ("top", "page_top"),
            ("bottom", "page_bottom"),
            ("header", "page_header"),
            ("footer", "page_footer"),
        ]:
            value = getattr(args, attr, None)
            if value is not None:
                params[name] = value
        if getattr(args, "page_orientation", None):
            params["orientation"] = args.page_orientation
    if feature == "page_border":
        params["type"] = getattr(args, "page_border_type", "SOLID")
        params["width"] = getattr(args, "page_border_width", "0.1 mm")
        if getattr(args, "page_border_color", None):
            params["color"] = args.page_border_color
        if getattr(args, "page_border_offset", None) is not None:
            params["offset"] = args.page_border_offset
        if getattr(args, "remove_page_border", False):
            params["remove"] = True
    if feature == "page_number":
        params["mode"] = getattr(args, "page_number_mode", "show")
        if getattr(args, "page_number_start", None) is not None:
            params["start"] = args.page_number_start
    if feature == "strike_or_underline":
        params["strike"] = bool(getattr(args, "strike", False))
        params["underline"] = not bool(getattr(args, "no_underline", False))
    if feature == "character_width":
        params["ratio"] = getattr(args, "character_width", None) or "100"
    if feature == "paragraph_alignment":
        params["horizontal"] = getattr(args, "horizontal", None) or "CENTER"
    if feature == "paragraph_spacing":
        params["line_spacing_value"] = getattr(args, "line_spacing", None) or "160"
    if feature == "table_dimensions":
        if getattr(args, "cell_width", None):
            params["cell_width"] = args.cell_width
        if getattr(args, "cell_height", None):
            params["cell_height"] = args.cell_height
        if getattr(args, "margin", None):
            params["margin"] = args.margin
    if feature == "table_sort":
        params["numeric"] = bool(getattr(args, "numeric", False))
        params["descending"] = bool(getattr(args, "descending", False))
        params["header_rows"] = getattr(args, "header_rows", 1)
    if feature == "document_blocks" and getattr(args, "paragraph", None):
        params["paragraphs"] = args.paragraph
    if feature == "table_merge_split":
        params["mode"] = "split" if getattr(args, "split", False) else "merge"
        params["cols"] = getattr(args, "merge_cols", 2)
        params["rows"] = getattr(args, "merge_rows", 1)
    if feature == "table_rows":
        params["mode"] = getattr(args, "row_mode", "append")
        params["count"] = getattr(args, "row_count", 1)
        params["header_rows"] = getattr(args, "header_rows", 1)
        if getattr(args, "row_values", None):
            params["values"] = [[cell.strip() for cell in row.split("|")] for row in args.row_values]
        if getattr(args, "all_tables", False):
            params["all_tables"] = True
    if feature == "table_columns":
        params["mode"] = getattr(args, "column_mode", "append")
        params["position"] = getattr(args, "column_position", "right")
        params["count"] = getattr(args, "column_count", 1)
        if getattr(args, "column_values", None):
            params["values"] = [[cell.strip() for cell in column.split("|")] for column in args.column_values]
        if getattr(args, "all_tables", False):
            params["all_tables"] = True
    return params


def _feature_operations_from_args(args) -> list[dict]:
    operations = [{"key": feature, "params": _feature_params_from_args(feature, args)} for feature in (getattr(args, "feature", []) or [])]
    operations.extend(_feature_operations_from_json(getattr(args, "features_json", []) or []))
    return operations


def _feature_operations_from_json(values: list[str]) -> list[dict]:
    from .hwpx_features import load_operations_json

    operations: list[dict] = []
    for value in values:
        operations.extend(load_operations_json(_read_json_argument(value)))
    return operations


def _read_json_argument(value: str) -> str:
    path_value = value[1:] if value.startswith("@") else value
    try:
        path = Path(path_value)
        if path.exists():
            return path.read_text(encoding="utf-8-sig")
    except OSError:
        pass
    return value
