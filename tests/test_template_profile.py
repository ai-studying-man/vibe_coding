import unittest
from pathlib import Path

from office_bumpis.template_profile import learn_template_profile, render_profile_markdown


class TemplateProfileTests(unittest.TestCase):
    def test_learn_template_profile_extracts_blocks_and_slots(self):
        source = Path("outputs/plan_report.hwpx")
        if not source.exists():
            self.skipTest("sample HWPX output is not available")

        profile = learn_template_profile(source)

        self.assertGreater(len(profile.blocks), 0)
        self.assertGreater(len(profile.slots), 0)
        self.assertTrue(any(slot.role == "title" for slot in profile.slots))
        title_slot = next(slot for slot in profile.slots if slot.role == "title")
        self.assertNotEqual(title_slot.text, "추진 배경")
        self.assertGreaterEqual(len(profile.tables), 1)
        self.assertGreaterEqual(profile.style_summary.char_pr_count, 1)
        self.assertTrue(profile.tables[0].cell_attrs)
        self.assertIn("cellSpan", profile.tables[0].cell_attrs[0][0])
        self.assertIn("char", title_slot.style)
        self.assertIn("paragraph", title_slot.style)
        self.assertEqual(title_slot.style["charPrIDRef"], title_slot.char_pr_id)
        self.assertEqual(title_slot.style["paraPrIDRef"], title_slot.para_pr_id)
        self.assertTrue(title_slot.style["char"].get("fontFaceHangul"))
        self.assertIn("marginIndent", title_slot.style["paragraph"])
        self.assertIn("borderFillIDRef", title_slot.style["paragraph"])

    def test_render_profile_markdown_mentions_slots(self):
        source = Path("outputs/plan_report.hwpx")
        if not source.exists():
            self.skipTest("sample HWPX output is not available")

        markdown = render_profile_markdown(learn_template_profile(source))

        self.assertIn("## Slots", markdown)
        self.assertIn("## Style Profile", markdown)
        self.assertIn("Hangul Font", markdown)
        self.assertIn("## Paragraph Styles", markdown)
        self.assertIn("BorderFill", markdown)
        self.assertIn("Align", markdown)
        self.assertIn("## Blocks", markdown)


if __name__ == "__main__":
    unittest.main()
