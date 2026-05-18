import unittest
import zipfile
from pathlib import Path

from office_bumpis.hwpx_features import apply_standard_features
from office_bumpis.llm_adapter import DEFAULT_LOCAL_MODEL
from office_bumpis.profile_filler import fill_hwpx_with_profile
from office_bumpis.standard_features import feature_inventory
from office_bumpis.template_engine import DraftContent
from office_bumpis.template_profile import learn_template_profile, save_profile
from office_bumpis.webapp import (
    TEMPLATE_DIR,
    WEB_FEATURE_OPTIONS,
    _guard_generated_output,
    _index_html,
    _template_artifact_path,
    _web_feature_params,
    _write_template_xml_bundle,
)


class WebAppFeatureTests(unittest.TestCase):
    def test_web_ui_exposes_all_implemented_standard_features(self):
        implemented = {item["key"] for item in feature_inventory() if item["implemented"]}
        web_keys = {key for key, _label, _checked in WEB_FEATURE_OPTIONS}
        html = _index_html()

        self.assertEqual(implemented, web_keys)
        for key in implemented:
            self.assertIn(f'value="{key}"', html)

    def test_web_ui_is_agent_layout_with_hwpx_panel(self):
        html = _index_html()

        self.assertIn("Qwen SLM Agent", html)
        self.assertIn("conversationList", html)
        self.assertIn("chatMessages", html)
        self.assertIn("chatInput", html)
        self.assertIn("progressLog", html)
        self.assertIn("HWPX 자동화", html)
        self.assertIn(DEFAULT_LOCAL_MODEL, html)

    def test_web_feature_defaults_can_be_applied_to_hwpx(self):
        source = Path("outputs/plan_report.hwpx")
        if not source.exists():
            self.skipTest("sample HWPX output is not available")

        output = Path("outputs/test_web_feature_defaults.hwpx")
        operations = [{"key": key, "params": _web_feature_params(key)} for key, _label, _checked in WEB_FEATURE_OPTIONS]
        apply_standard_features(source, output, operations)

        self.assertTrue(output.exists())
        with zipfile.ZipFile(output) as zf:
            names = zf.namelist()
            section = zf.read("Contents/section0.xml").decode("utf-8", errors="replace")
        self.assertIn("Contents/header.xml", names)
        self.assertIn("추가 검토사항", section)

    def test_web_guard_generated_output_returns_structure_report(self):
        source = Path("outputs/plan_report.hwpx")
        if not source.exists():
            self.skipTest("sample HWPX output is not available")

        profile = learn_template_profile(source)
        profile_path = Path("outputs/test_web_guard.profile.json")
        output = Path("outputs/test_web_guard_generated.hwpx")
        save_profile(profile_path, profile)
        fill_hwpx_with_profile(source, output, DraftContent("Web guard title", ["Web guard body"], []), profile)

        report = _guard_generated_output(source, output, profile_path)

        self.assertTrue(report["passed"])
        self.assertGreater(report["slot_style_checks"], 0)

    def test_template_artifact_path_allows_only_profile_artifacts(self):
        valid = _template_artifact_path("0123456789abcdef0123456789abcdef.profile.json")
        xml_bundle = _template_artifact_path("0123456789abcdef0123456789abcdef.xml.zip")
        invalid = _template_artifact_path("../secret.json")

        self.assertIsNotNone(valid)
        self.assertIsNotNone(xml_bundle)
        self.assertIsNone(invalid)
        self.assertIn("profile_json_url", _index_html())
        self.assertIn("xml_bundle_url", _index_html())

    def test_write_template_xml_bundle_contains_xml_and_profiles(self):
        source = Path("outputs/plan_report.hwpx")
        if not source.exists():
            self.skipTest("sample HWPX output is not available")

        template_id = "0123456789abcdef0123456789abcdea"
        TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
        (TEMPLATE_DIR / f"{template_id}.json").write_text("{}", encoding="utf-8")
        (TEMPLATE_DIR / f"{template_id}.profile.json").write_text("{}", encoding="utf-8")
        (TEMPLATE_DIR / f"{template_id}.profile.md").write_text("# profile", encoding="utf-8")

        bundle = _write_template_xml_bundle(template_id, source)

        with zipfile.ZipFile(bundle) as zf:
            names = set(zf.namelist())
        self.assertIn("Contents/header.xml", names)
        self.assertIn("Contents/section0.xml", names)
        self.assertIn(f"{template_id}.profile.json", names)
        self.assertIn(f"{template_id}.profile.md", names)


if __name__ == "__main__":
    unittest.main()
