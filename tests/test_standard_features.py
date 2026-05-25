import unittest

from office_bumpis.standard_features import feature_inventory, normalize_whitespace


class StandardFeatureTests(unittest.TestCase):
    def test_text_cleanup_normalizes_spacing(self):
        self.assertEqual(normalize_whitespace("  A   B  \n\n C  ", remove_empty_lines=True), "A B\nC")

    def test_feature_inventory_contains_common_table_features(self):
        keys = {item["key"] for item in feature_inventory()}
        self.assertIn("transparent_table", keys)
        self.assertIn("table_background", keys)
        self.assertIn("font_family", keys)
        self.assertIn("cleanup_whitespace", keys)


if __name__ == "__main__":
    unittest.main()
