import unittest
from pathlib import Path

from office_bumpis.hwpx_features import apply_standard_features
from office_bumpis.profile_filler import fill_hwpx_with_profile
from office_bumpis.structure_guard import guard_template_output
from office_bumpis.template_engine import DraftContent
from office_bumpis.template_profile import learn_template_profile


class StructureGuardTests(unittest.TestCase):
    def test_guard_passes_for_profile_filled_hwpx(self):
        source = Path("outputs/plan_report.hwpx")
        if not source.exists():
            self.skipTest("sample HWPX output is not available")

        profile = learn_template_profile(source)
        output = Path("outputs/test_structure_guard_filled.hwpx")
        fill_hwpx_with_profile(
            source,
            output,
            DraftContent("Guard title", ["Guard body"], [], tables=[[["A", "B", "C"]]]),
            profile,
        )

        report = guard_template_output(source, output, profile=profile)

        self.assertTrue(report.passed, report.to_dict())
        self.assertGreater(report.slot_style_checks, 0)
        self.assertGreater(report.table_style_checks, 0)

    def test_guard_reports_style_changes(self):
        source = Path("outputs/plan_report.hwpx")
        if not source.exists():
            self.skipTest("sample HWPX output is not available")

        output = Path("outputs/test_structure_guard_style_changed.hwpx")
        apply_standard_features(source, output, [{"key": "font_color", "params": {"color": "#005BAC"}}])

        report = guard_template_output(source, output, profile=learn_template_profile(source))

        self.assertFalse(report.passed)
        self.assertTrue(any(issue.code == "char_style_count" for issue in report.issues))


if __name__ == "__main__":
    unittest.main()
