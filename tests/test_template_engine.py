import unittest
from types import SimpleNamespace
from pathlib import Path

from office_bumpis.template_engine import analyze_hwpx_template, draft_from_text, fill_hwpx_template, _ollama_prompt
from office_bumpis.template_profile import learn_template_profile


class TemplateEngineTests(unittest.TestCase):
    def test_analyze_and_fill_existing_hwpx_template(self):
        source = Path("outputs/plan_report.hwpx")
        if not source.exists():
            self.skipTest("sample HWPX output is not available")

        analysis = analyze_hwpx_template(source, template_id="test")
        self.assertGreater(len(analysis.text_nodes), 0)
        self.assertIsNotNone(analysis.style_summary)
        self.assertGreaterEqual(analysis.style_summary.char_pr_count, 1)
        self.assertIn("hangul", analysis.style_summary.font_faces)
        self.assertTrue(any(style.get("fontFaceHangul") for style in analysis.style_summary.char_styles.values()))
        self.assertGreaterEqual(len(analysis.style_summary.border_fills), 1)

        draft = draft_from_text(
            "Title: Civil petition handling improvement plan\n"
            "Prepare a report covering background, key actions, and the follow-up schedule.",
            analysis,
            use_llm=False,
        )
        output = Path("outputs/test_template_engine.hwpx")
        fill_hwpx_template(source, output, draft, analysis=analysis)

        self.assertTrue(output.exists())
        self.assertGreater(output.stat().st_size, 0)

    def test_draft_from_text_extracts_markdown_table(self):
        analysis = analyze_hwpx_template("outputs/plan_report.hwpx")
        draft = draft_from_text(
            "Title: Table test\n\n| 과제 | 내용 |\n| --- | --- |\n| A | B |",
            analysis,
            use_llm=False,
        )

        self.assertEqual(draft.tables, [[["과제", "내용"], ["A", "B"]]])

    def test_ollama_prompt_includes_learned_profile_clues(self):
        source = Path("outputs/plan_report.hwpx")
        if not source.exists():
            self.skipTest("sample HWPX output is not available")

        analysis = analyze_hwpx_template(source)
        profile = learn_template_profile(source)
        prompt = _ollama_prompt("raw instruction", analysis, profile=profile)

        self.assertIn("slot title", prompt)
        self.assertIn("font=", prompt)
        self.assertIn("table 1", prompt)
        self.assertIn("tables", prompt)

    def test_draft_from_text_can_fit_body_slot_count(self):
        analysis = analyze_hwpx_template("outputs/plan_report.hwpx")
        profile = SimpleNamespace(
            slots=[
                SimpleNamespace(role="body"),
                SimpleNamespace(role="body"),
            ]
        )

        draft = draft_from_text("Title\none\n\ntwo\n\nthree", analysis, use_llm=False, profile=profile)

        self.assertEqual(len(draft.paragraphs), 2)
        self.assertIn("three", draft.paragraphs[-1])


if __name__ == "__main__":
    unittest.main()
