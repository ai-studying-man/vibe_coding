# Implementable Document-Automation Features

This document maps the currently implementable features in this workspace to the Python modules that support them. The practical goal is to move staff time away from repeatedly matching official-document formatting and toward writing/reviewing the actual content.

## Summary

The workspace has two code sources:

- `office_bumpis/`: implemented automation pipeline for normalized JSON, Markdown, HWPX export, template inspection, profiles, and local LLM integration.
- `recovered_source/`: decompiled reference source from the original EXE. This is useful for rebuilding Hancom Office editing commands, but some functions include `Decompyle incomplete` markers and should be treated as reference material rather than directly copied runtime code.

## Implemented Now

| Feature | Staff Benefit | Primary Files | Key APIs |
| --- | --- | --- | --- |
| Normalize public-document data into one schema | Staff enter facts once instead of manually reshaping every document | `office_bumpis/models.py` | `OfficialDocument`, `BodyBlock`, `Attachment`, `ApprovalStep` |
| Render public-document Markdown for review | Staff can review content before opening HWPX/Hancom Office | `office_bumpis/renderer.py` | `render_markdown()` |
| Generate HWPX from normalized document data | Staff do not manually recreate the document shell | `office_bumpis/hwpx.py` | `export_hwpx()`, `markdown_to_hwpx()` |
| Validate generated HWPX package structure | Prevent broken HWPX files from being handed to staff | `office_bumpis/hwpx.py` | `verify_hwpx()` |
| Convert common public-document dates | Enforce official date display without manual editing | `office_bumpis/formatting.py` | `official_date()` |
| Convert amounts to Korean won text | Avoid repeated manual amount formatting | `office_bumpis/formatting.py` | `amount_to_korean_won()` |
| Inspect HWPX template files | Learn what kind of document/form a given HWPX resembles | `office_bumpis/templates.py` | `inspect_hwpx_template()`, `inspect_hwpx_templates()` |
| Produce template inventory JSON/Markdown | Build reusable knowledge of agency/form-specific templates | `office_bumpis/templates.py`, `office_bumpis/cli.py` | `write_inventory()`, `inspect-templates` |
| Generate profile-based document skeletons | Staff choose “plan report” or “approval sheet” and fill content, not layout | `office_bumpis/profiles.py` | `build_profile_document()`, `build_profile_mapping()` |
| Support extracted document profiles | Reuse workflow patterns found in the EXE/PDF/templates | `office_bumpis/profiles.py` | `approval_sheet`, `plan_report`, `work_reference`, `meeting_brief`, `comprehensive_plan` |
| Use local OpenAI-compatible LLMs | LLM drafts content while deterministic code keeps document structure stable | `office_bumpis/llm_adapter.py`, `office_bumpis/cli.py` | `OpenCompatibleLLM`, `draft --profile` |
| Command-line workflow | Non-developers or batch jobs can run document operations | `office_bumpis/cli.py` | `generate`, `markdown`, `draft`, `preset`, `inspect-templates` |

## Implementable From Recovered EXE Source

These are not all productionized in `office_bumpis/` yet, but the recovered EXE source gives enough reference to rebuild them. Start from the listed files and convert each function group into tested, explicit modules rather than copying incomplete decompiled code blindly.

| Feature Group | What It Automates | Reference Files | Notes |
| --- | --- | --- | --- |
| Hancom Office COM connection | Attach to running Hangul/Hancom Office document | `recovered_source/hancom_library.py` | Class `기본한컴`; recovered source has 89 incomplete markers overall |
| Character style controls | Font size, bold, underline, superscript, color, reset styles | `recovered_source/hancom_library.py` | Many `HAction.Run()` and `CreateAction('CharShape')` references |
| Paragraph style controls | Alignment, indentation, line spacing, bullet-like formatting | `recovered_source/hancom_library.py` | Useful for rebuilding style presets independent of HWPX XML |
| Table navigation/editing | Move between cells, select table, merge cells, append cells, resize | `recovered_source/hancom_library.py` | Functions around `표...`, `TableCellBlock`, `TableMergeCell`, `TableResize...` |
| Table cleanup/standardization | Apply border, background, width/height, caption and public-office table styles | `recovered_source/hancom_library.py` | Should be reimplemented as structured table transformations where possible |
| Document boilerplate insertion | Titles, subtitles, reference blocks, attachments, report-author areas | `recovered_source/hancom_library.py`, `recovered_source/main.py` | The UI routes in `main.py` show which buttons call which library methods |
| Mail merge / repeated field insertion | Insert repeated fields or generated values across a document | `recovered_source/main.py`, `recovered_source/hancom_library.py` | Good candidate for JSON-driven batch generation |
| Excel-to-document workflows | Excel active object, paste values, autofit, data cleanup | `recovered_source/excel_library.py` | Class `엑셀`; recovered source has 5 incomplete markers |
| Tkinter UI component patterns | Recreate lightweight desktop controls if needed | `recovered_source/interface.py`, `recovered_source/main.py` | Better treated as reference; a modern web/CLI workflow may be simpler |

## Directly Useful Commands

Create a normalized JSON skeleton from an extracted workflow profile:

```powershell
python -m office_bumpis preset plan_report --seed examples\plan_report_seed.json -o outputs\plan_report.json
```

Generate HWPX and review Markdown from JSON:

```powershell
python -m office_bumpis generate outputs\plan_report.json -o outputs\plan_report.hwpx --markdown outputs\plan_report.md
```

Inspect agency/form HWPX templates:

```powershell
python -m office_bumpis inspect-templates _analysis\pyi_extract -o docs\template_inventory.json --markdown docs\template_inventory.md
```

Use a local OpenAI-compatible LLM with a deterministic profile:

```powershell
python -m office_bumpis draft prompt.txt --profile plan_report -o outputs\draft_plan.hwpx --json outputs\draft_plan.json --markdown outputs\draft_plan.md
```

## Best Next Features For The User’s Goal

These should be implemented next because they directly reduce agency-formatting effort.

1. `template_learning.py`
   - Input: one agency HWPX document.
   - Output: a `TemplateProfile` containing XML sections, text runs, paragraph IDs, table structures, images, and slot candidates.
   - Related existing code: `office_bumpis/templates.py`.

2. `slot_mapper.py`
   - Detect slots such as title, recipient, sender, date, approval line, sections, tables, attachments, and end marker.
   - Use heuristics first; use LLM only to suggest ambiguous mappings.
   - Related existing code: `office_bumpis/models.py`, `office_bumpis/llm_adapter.py`.

3. `template_filler.py`
   - Copy the original HWPX package, preserve style XML and binary assets, and replace only selected text/table slots.
   - Related existing code: `office_bumpis/hwpx.py`.

4. `style_model.py`
   - Represent paragraph, character, table, and cell styles in a stable Python model.
   - Related existing code: `office_bumpis/templates.py`, `recovered_source/hancom_library.py`.

5. `document_agent.py`
   - Orchestrate LLM content generation with deterministic template filling.
   - LLM should return JSON, not HWPX XML.
   - Related existing code: `office_bumpis/llm_adapter.py`, `office_bumpis/profiles.py`.

## Product Direction

The intended workflow should be:

1. Staff upload an existing agency document form `A.hwpx`.
2. The system learns layout, style, tables, images, and slots from `A.hwpx`.
3. Staff provide only the new content or ask a local LLM to draft it.
4. The LLM returns structured JSON.
5. The deterministic engine fills the learned template.
6. The system exports `A_prime.hwpx` with the same agency-specific format.

This keeps staff focused on content, review, and factual accuracy while the software handles repetitive formatting.
