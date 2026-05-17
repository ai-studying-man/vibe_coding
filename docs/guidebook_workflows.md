# Guidebook Workflow Synthesis

The guidebook was converted to Markdown at `_analysis/converted/guidebook.md`. The PDF has 78 pages; local parsing found text on 76 pages. The extracted text is mostly readable Korean, with only a small number of replacement/question characters, so the guidebook is usable as workflow evidence without OCR.

## Core Usage Pattern

The user opens the target Hancom Office document first, then launches 범정부오피스 and applies commands to the current cursor position, selected text block, selected cells, or active table.

This confirms the executable analysis: 범정부오피스 is primarily a Hancom Office editing command surface, not a standalone document database. Its functions assume an existing HWP/HWPX editing context.

## Basic Formatting

The guidebook repeatedly describes this pattern:

- Place the cursor at the desired location and click a button to insert a report title, subtitle, 참고 block, text box, logo, progress table, or report-author block.
- Select text and click a button to convert it into a standardized public-document bullet style.
- Common styles include `□` headings, `○` main bullets, `-` sub bullets, `※` reference notes, parenthesized emphasis, highlighted emphasis, and reset-to-default text.
- Date and amount conversion are treated as first-class automation tasks, including official date formatting and Korean won amount expansion.

Implementation mapping:

- `office_bumpis.formatting` handles official dates and Korean won amount strings.
- `office_bumpis.renderer` emits consistent 공문 Markdown with sender, metadata, 수신, 제목, body, 붙임, and 끝.
- `office_bumpis.profiles` turns guidebook-style repeated structures into deterministic JSON skeletons.

## Table Workflows

The guidebook emphasizes table cleanup and standardization:

- Apply public-office table styling to arbitrary tables.
- Normalize captions.
- Insert or remove rows/columns.
- Merge cells and adjust width/height.
- Apply comma formatting, sums, averages, percentages, reverse horizontal/vertical sums, and numeric ordering.
- Convert selected table ranges into cleaner public-document form.

Implementation mapping:

- Current implementation supports table blocks in the normalized JSON model and Markdown/HWPX export.
- The original fine-grained Hancom table editing commands are documented as extracted workflow requirements but are not reimplemented as COM actions; the new path generates clean tables from structured data.

## Template/Form Workflows

The extracted bundled HWPX files and guidebook both point to these reusable document shapes:

- Approval sheet: registration number, approval line, registration/approval dates, disclosure status, cooperation line, title, overview, main content, future plan, attachment, end marker.
- Plan report: registration metadata, approval line, background, purpose/direction, implementation plan, schedule, administrative matters, attachments.
- Work reference: short brief with purpose, main content, future plan, and reporter.
- Meeting brief: completed matters, scheduled matters, purpose, date/place, attendees, main content.
- Comprehensive plan: cover/table-of-contents style long-form plan with background, direction, key tasks, administrative matters, and appendices.

Implementation mapping:

- `docs/template_inventory.md` records the extracted HWPX template profiles.
- `office_bumpis.profiles` maps those profiles to deterministic document skeletons.
- `python -m office_bumpis preset <profile>` creates normalized JSON from those skeletons.

## AI/LLM Safety Guidance

The guidebook includes explicit warnings for ChatGPT-style use:

- Do not input non-public information.
- Do not input personal information.
- Do not input information that has not been externally disclosed or is not approved for export.
- Do not use generated answers without fact checking.

Implementation mapping:

- `office_bumpis.llm_adapter` confines LLM output to JSON.
- `draft --profile` uses the LLM for seed content and then applies deterministic profile expansion, keeping the official-document structure in code.
- Human review is still required before official use.

## Resulting Automation Strategy

The practical target is not to clone every UI button. The stable path is:

1. Gather draft facts from a user or local OpenAI-compatible LLM.
2. Normalize those facts into `OfficialDocument` JSON.
3. Select a profile when the document matches an extracted workflow.
4. Render Markdown for review.
5. Export HWPX and validate the package structure.

This gives the user an agent-friendly public-document generation pipeline while preserving the guidebook's main workflow intent: reduce repetitive official-document formatting and keep generated content reviewable.
