from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

from .hwpx import verify_hwpx
from .template_profile import LearnedTemplateProfile, learn_template_profile, load_profile


@dataclass
class GuardIssue:
    code: str
    message: str


@dataclass
class StructureGuardReport:
    template: str
    output: str
    passed: bool
    issues: list[GuardIssue] = field(default_factory=list)
    section_files: list[str] = field(default_factory=list)
    template_block_count: int = 0
    output_block_count: int = 0
    template_table_count: int = 0
    output_table_count: int = 0
    slot_style_checks: int = 0
    table_style_checks: int = 0

    def to_dict(self) -> dict:
        data = asdict(self)
        data["issues"] = [asdict(issue) for issue in self.issues]
        return data


def guard_template_output(
    template_path: str | Path,
    output_path: str | Path,
    *,
    profile: LearnedTemplateProfile | str | Path | None = None,
) -> StructureGuardReport:
    template = Path(template_path)
    output = Path(output_path)
    verify_hwpx(template)
    verify_hwpx(output)

    template_profile = _resolve_profile(template, profile)
    output_profile = learn_template_profile(output, template_id=template_profile.template_id)

    report = StructureGuardReport(
        template=str(template),
        output=str(output),
        passed=True,
        section_files=template_profile.section_files,
        template_block_count=len(template_profile.blocks),
        output_block_count=len(output_profile.blocks),
        template_table_count=template_profile.style_summary.table_count,
        output_table_count=output_profile.style_summary.table_count,
    )

    _check_equal(report, "section_files", template_profile.section_files, output_profile.section_files)
    _check_equal(report, "char_style_count", template_profile.style_summary.char_pr_count, output_profile.style_summary.char_pr_count)
    _check_equal(report, "para_style_count", template_profile.style_summary.para_pr_count, output_profile.style_summary.para_pr_count)
    _check_equal(report, "border_fill_count", template_profile.style_summary.border_fill_count, output_profile.style_summary.border_fill_count)
    _check_equal(report, "table_count", template_profile.style_summary.table_count, output_profile.style_summary.table_count)

    if len(output_profile.blocks) < len(template_profile.blocks):
        _add_issue(
            report,
            "block_count_shrank",
            f"Output has fewer learned blocks ({len(output_profile.blocks)}) than template ({len(template_profile.blocks)}).",
        )

    _check_slot_styles(report, template_profile, output_profile)
    _check_table_styles(report, template_profile, output_profile)
    report.passed = not report.issues
    return report


def _resolve_profile(template: Path, profile: LearnedTemplateProfile | str | Path | None) -> LearnedTemplateProfile:
    if isinstance(profile, LearnedTemplateProfile):
        return profile
    if profile is not None:
        return load_profile(profile)
    return learn_template_profile(template)


def _check_slot_styles(
    report: StructureGuardReport,
    template_profile: LearnedTemplateProfile,
    output_profile: LearnedTemplateProfile,
) -> None:
    output_blocks = {block.block_id: block for block in output_profile.blocks}
    for slot in template_profile.slots:
        output_block = output_blocks.get(slot.block_id)
        if output_block is None:
            _add_issue(report, "slot_missing", f"Slot {slot.name} ({slot.block_id}) was not found in the output profile.")
            continue
        report.slot_style_checks += 1
        if slot.char_pr_id and slot.char_pr_id not in output_block.char_pr_ids:
            _add_issue(
                report,
                "slot_char_style_changed",
                f"Slot {slot.name} expected charPr {slot.char_pr_id}, got {output_block.char_pr_ids or '-'}",
            )
        if slot.para_pr_id and slot.para_pr_id not in output_block.para_pr_ids:
            _add_issue(
                report,
                "slot_para_style_changed",
                f"Slot {slot.name} expected paraPr {slot.para_pr_id}, got {output_block.para_pr_ids or '-'}",
            )


def _check_table_styles(
    report: StructureGuardReport,
    template_profile: LearnedTemplateProfile,
    output_profile: LearnedTemplateProfile,
) -> None:
    output_tables = {table.block_id: table for table in output_profile.tables}
    for table in template_profile.tables:
        output_table = output_tables.get(table.block_id)
        if output_table is None:
            _add_issue(report, "table_missing", f"Table {table.block_id} was not found in the output profile.")
            continue
        report.table_style_checks += 1
        if table.column_count != output_table.column_count:
            _add_issue(
                report,
                "table_column_count_changed",
                f"Table {table.block_id} expected {table.column_count} columns, got {output_table.column_count}.",
            )
        if table.header_rows != output_table.header_rows:
            _add_issue(
                report,
                "table_header_rows_changed",
                f"Table {table.block_id} expected {table.header_rows} header rows, got {output_table.header_rows}.",
            )
        if table.header_rows and table.cell_attrs:
            expected = table.cell_attrs[: table.header_rows]
            actual = output_table.cell_attrs[: table.header_rows]
            if expected != actual:
                _add_issue(report, "table_header_style_changed", f"Table {table.block_id} header cell attributes changed.")


def _check_equal(report: StructureGuardReport, code: str, expected, actual) -> None:
    if expected != actual:
        _add_issue(report, code, f"Expected {expected!r}, got {actual!r}.")


def _add_issue(report: StructureGuardReport, code: str, message: str) -> None:
    report.issues.append(GuardIssue(code=code, message=message))
