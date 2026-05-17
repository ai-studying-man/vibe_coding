import unittest
from pathlib import Path

from office_bumpis.feature_coverage import analyze_recovered_feature_coverage, render_coverage_markdown


class FeatureCoverageTests(unittest.TestCase):
    def test_analyze_recovered_feature_coverage_finds_standard_groups(self):
        source = Path("recovered_source")
        if not source.exists():
            self.skipTest("recovered source is not available")

        report = analyze_recovered_feature_coverage(source)

        self.assertGreater(report.recovered_symbol_count, 0)
        self.assertGreater(report.haction_count, 0)
        self.assertGreater(report.feature_hits.get("paragraph_alignment", 0), 0)
        self.assertGreater(report.feature_hits.get("table_merge_split", 0), 0)
        self.assertGreater(report.feature_hits.get("document_blocks", 0), 0)

        markdown = render_coverage_markdown(report)
        self.assertIn("## Feature Hits", markdown)
        self.assertIn("paragraph_alignment", markdown)


if __name__ == "__main__":
    unittest.main()
