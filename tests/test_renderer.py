import unittest

from office_bumpis.formatting import amount_to_korean_won, official_date
from office_bumpis.models import OfficialDocument
from office_bumpis.profiles import build_profile_document
from office_bumpis.renderer import render_markdown


class RendererTests(unittest.TestCase):
    def test_official_date_formats_common_inputs(self):
        self.assertEqual(official_date("2026-05-17"), "2026. 5. 17.")
        self.assertEqual(official_date("20260517"), "2026. 5. 17.")

    def test_amount_to_korean_won(self):
        self.assertEqual(amount_to_korean_won(12340), "12,340원(금일만이천삼백사십원)")

    def test_render_markdown_contains_public_document_fields(self):
        doc = OfficialDocument.from_mapping(
            {
                "title": "테스트 공문",
                "sender": "행정과",
                "recipients": ["민원과"],
                "date": "2026-05-17",
                "body": ["본문입니다."],
                "attachments": ["붙임자료"],
            }
        )
        md = render_markdown(doc)
        self.assertIn("수신  민원과", md)
        self.assertIn("제목  테스트 공문", md)
        self.assertIn("붙임", md)
        self.assertTrue(md.rstrip().endswith("끝."))

    def test_render_markdown_numbers_text_blocks_without_counting_tables(self):
        doc = OfficialDocument.from_mapping(
            {
                "title": "테스트 공문",
                "sender": "행정과",
                "recipients": ["민원과"],
                "body": [
                    "첫 문단입니다.",
                    {"type": "table", "headers": ["구분"], "rows": [["내용"]]},
                    {"type": "list", "text": "둘째 문단", "items": ["세부"]},
                ],
            }
        )
        md = render_markdown(doc)
        self.assertIn("1. 첫 문단입니다.", md)
        self.assertIn("2. 둘째 문단", md)
        self.assertNotIn("3. 둘째 문단", md)

    def test_plan_report_profile_builds_extracted_workflow_sections(self):
        doc = build_profile_document(
            "plan_report",
            {
                "title": "계획 보고",
                "sender": "행정과",
                "recipients": ["기획과"],
                "background": "추진 배경입니다.",
            },
        )
        md = render_markdown(doc)
        self.assertIn("## 추진 배경", md)
        self.assertIn("## 추진 계획", md)
        self.assertIn("## 행정 사항", md)
        self.assertIn("추진 배경입니다.", md)


if __name__ == "__main__":
    unittest.main()
