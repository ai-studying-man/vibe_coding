import json
import subprocess
import sys
import unittest
import zipfile
from pathlib import Path


class CliTests(unittest.TestCase):
    def test_generate_from_template_creates_hwpx_and_reports_guard(self):
        source = Path("outputs/plan_report.hwpx")
        if not source.exists():
            self.skipTest("sample HWPX output is not available")

        text = Path("outputs/test_cli_generate_text.txt")
        output = Path("outputs/test_cli_generate_from_template.hwpx")
        guard = Path("outputs/test_cli_generate_from_template.guard.json")
        text.write_text(
            "Title: CLI profile generation\n\n"
            "First body paragraph.\n\n"
            "Second body paragraph.\n\n"
            "| Task | Content | Date |\n"
            "| --- | --- | --- |\n"
            "| CLI-A | Alpha | 2026 |\n",
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "office_bumpis",
                "generate-from-template",
                str(source),
                str(text),
                "-o",
                str(output),
                "--guard-json",
                str(guard),
            ],
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertTrue(output.exists())
        report = json.loads(guard.read_text(encoding="utf-8"))
        self.assertTrue(report["passed"])
        with zipfile.ZipFile(output) as zf:
            section = zf.read("Contents/section0.xml").decode("utf-8", errors="replace")
        self.assertIn("CLI-A", section)

    def test_generate_from_template_accepts_feature_operations_json_file(self):
        source = Path("outputs/plan_report.hwpx")
        if not source.exists():
            self.skipTest("sample HWPX output is not available")

        text = Path("outputs/test_cli_generate_json_ops_text.txt")
        ops = Path("outputs/test_cli_generate_json_ops.json")
        output = Path("outputs/test_cli_generate_json_ops.hwpx")
        text.write_text("Title: JSON operation generation\n\n본문 자동 생성 테스트", encoding="utf-8")
        ops.write_text(
            json.dumps(
                [
                    {"key": "font_color", "params": {"color": "#005BAC"}},
                    {"key": "document_blocks", "params": {"paragraphs": ["JSON feature block"]}},
                ],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "office_bumpis",
                "generate-from-template",
                str(source),
                str(text),
                "-o",
                str(output),
                "--features-json",
                str(ops),
            ],
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertTrue(output.exists())
        with zipfile.ZipFile(output) as zf:
            header = zf.read("Contents/header.xml").decode("utf-8", errors="replace")
            section = zf.read("Contents/section0.xml").decode("utf-8", errors="replace")
        self.assertIn("#005BAC", header)
        self.assertIn("JSON feature block", section)

    def test_apply_feature_accepts_inline_feature_operations_json(self):
        source = Path("outputs/plan_report.hwpx")
        if not source.exists():
            self.skipTest("sample HWPX output is not available")

        output = Path("outputs/test_cli_apply_inline_json_ops.hwpx")
        operations = json.dumps([{"key": "document_blocks", "params": {"paragraphs": ["Inline JSON operation"]}}])
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "office_bumpis",
                "apply-feature",
                str(source),
                "-o",
                str(output),
                "--features-json",
                operations,
            ],
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        with zipfile.ZipFile(output) as zf:
            section = zf.read("Contents/section0.xml").decode("utf-8", errors="replace")
        self.assertIn("Inline JSON operation", section)


if __name__ == "__main__":
    unittest.main()
