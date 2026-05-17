import json
import unittest
import zipfile
from pathlib import Path

from office_bumpis.profile_filler import _best_table_slot, fill_hwpx_with_profile
from office_bumpis.template_engine import DraftContent, StyleSummary
from office_bumpis.template_profile import LearnedTemplateProfile, SlotCandidate, TablePrototype, learn_template_profile, load_profile, save_profile


class ProfileFillerTests(unittest.TestCase):
    def test_fill_hwpx_with_profile_uses_title_and_body_slots(self):
        source = Path("outputs/plan_report.hwpx")
        if not source.exists():
            self.skipTest("sample HWPX output is not available")

        profile = learn_template_profile(source)
        output = Path("outputs/test_profile_filled.hwpx")
        report = fill_hwpx_with_profile(
            source,
            output,
            DraftContent("프로필 기반 제목", ["첫 번째 본문", "두 번째 본문"], ["붙임자료 1부"]),
            profile,
        )

        self.assertTrue(report.title_slot)
        self.assertTrue(report.body_slots)
        with zipfile.ZipFile(output) as zf:
            section = zf.read("Contents/section0.xml").decode("utf-8", errors="replace")
        self.assertIn("프로필 기반 제목", section)
        self.assertIn("첫 번째 본문", section)

    def test_fill_hwpx_with_profile_repeats_table_rows(self):
        source = Path("outputs/plan_report.hwpx")
        if not source.exists():
            self.skipTest("sample HWPX output is not available")

        profile = learn_template_profile(source)
        if not profile.tables:
            self.skipTest("sample profile has no data table")

        output = Path("outputs/test_profile_table_filled.hwpx")
        report = fill_hwpx_with_profile(
            source,
            output,
            DraftContent(
                "표 데이터 제목",
                ["본문"],
                [],
                tables=[
                    [
                        ["과제 A", "내용 A", "2026. 5."],
                        ["과제 B", "내용 B", "2026. 6."],
                    ]
                ],
            ),
            profile,
        )

        self.assertTrue(report.table_slots)
        with zipfile.ZipFile(output) as zf:
            section = zf.read("Contents/section0.xml").decode("utf-8", errors="replace")
        self.assertIn("과제 A", section)
        self.assertIn("과제 B", section)

    def test_fill_hwpx_with_profile_strips_markdown_table_header(self):
        source = Path("outputs/plan_report.hwpx")
        if not source.exists():
            self.skipTest("sample HWPX output is not available")

        profile = learn_template_profile(source)
        if not profile.tables:
            self.skipTest("sample profile has no data table")

        output = Path("outputs/test_profile_table_header_stripped.hwpx")
        report = fill_hwpx_with_profile(
            source,
            output,
            DraftContent(
                "Table title",
                ["Body text"],
                [],
                tables=[
                    [
                        ["Task", "Content", "Date"],
                        ["ROW-A", "VALUE-A", "2026-05"],
                        ["ROW-B", "VALUE-B", "2026-06"],
                    ]
                ],
            ),
            profile,
        )

        self.assertTrue(report.table_slots)
        with zipfile.ZipFile(output) as zf:
            section = zf.read("Contents/section0.xml").decode("utf-8", errors="replace")
        self.assertNotIn(">Task<", section)
        self.assertIn("ROW-A", section)
        self.assertIn("ROW-B", section)
        self.assertIn("VALUE-A", section)

    def test_best_table_slot_prefers_matching_column_count(self):
        profile = LearnedTemplateProfile(
            template_id="test",
            filename="test.hwpx",
            section_files=["Contents/section0.xml"],
            blocks=[],
            slots=[],
            tables=[
                TablePrototype("b0001", "Contents/section0.xml", 2, 4, 1, 1, [["A", "B", "C", "D"], ["", "", "", ""]]),
                TablePrototype("b0002", "Contents/section0.xml", 2, 2, 1, 1, [["Task", "Content"], ["", ""]]),
            ],
            style_summary=StyleSummary(0, 0, 0, 0, 0, {}, {}, []),
        )
        slots = [
            SlotCandidate("table_1", "table", "Contents/section0.xml", "b0001", "", "", "", 0.7),
            SlotCandidate("table_2", "table", "Contents/section0.xml", "b0002", "", "", "", 0.7),
        ]

        selected = _best_table_slot([["Task", "Content"], ["ROW-A", "VALUE-A"]], slots, profile)

        self.assertEqual(selected.block_id, "b0002")

    def test_profile_roundtrip_json(self):
        source = Path("outputs/plan_report.hwpx")
        if not source.exists():
            self.skipTest("sample HWPX output is not available")

        target = Path("outputs/test_profile_roundtrip.json")
        save_profile(target, learn_template_profile(source))
        loaded = load_profile(target)

        self.assertGreater(len(loaded.blocks), 0)
        self.assertGreater(len(loaded.slots), 0)
        self.assertIn("char", loaded.slots[0].style)


if __name__ == "__main__":
    unittest.main()
