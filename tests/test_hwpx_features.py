import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from office_bumpis.hwpx_features import apply_standard_features
from office_bumpis.template_engine import HH_NS, HP_NS


class HwpxFeatureTests(unittest.TestCase):
    def test_apply_font_color_creates_char_style_and_updates_runs(self):
        source = Path("outputs/plan_report.hwpx")
        if not source.exists():
            self.skipTest("sample HWPX output is not available")

        output = Path("outputs/test_font_color.hwpx")
        apply_standard_features(source, output, [{"key": "font_color", "params": {"color": "#005BAC"}}])

        with zipfile.ZipFile(output) as zf:
            header = ET.fromstring(zf.read("Contents/header.xml"))
            section = ET.fromstring(zf.read("Contents/section0.xml"))

        colored = [item for item in header.iter(f"{{{HH_NS}}}charPr") if item.attrib.get("textColor") == "#005BAC"]
        self.assertTrue(colored)
        new_id = colored[-1].attrib["id"]
        runs = [run for run in section.iter(f"{{{HP_NS}}}run") if run.attrib.get("charPrIDRef") == new_id]
        self.assertTrue(runs)

    def test_apply_transparent_table_sets_cell_border_fill(self):
        source = Path("_analysis/templates_ascii/template_1.hwpx")
        if not source.exists():
            self.skipTest("sample template is not available")

        output = Path("outputs/test_transparent_table.hwpx")
        apply_standard_features(source, output, ["transparent_table"])

        with zipfile.ZipFile(output) as zf:
            header = ET.fromstring(zf.read("Contents/header.xml"))
            section = ET.fromstring(zf.read("Contents/section0.xml"))

        border_fills = list(header.iter(f"{{{HH_NS}}}borderFill"))
        new_border = border_fills[-1]
        new_id = new_border.attrib["id"]
        for name in ["leftBorder", "rightBorder", "topBorder", "bottomBorder"]:
            border = new_border.find(f"{{{HH_NS}}}{name}")
            self.assertIsNotNone(border)
            self.assertEqual(border.attrib.get("type"), "NONE")

        cells = list(section.iter(f"{{{HP_NS}}}tc"))
        self.assertTrue(cells)
        self.assertTrue(all(cell.attrib.get("borderFillIDRef") == new_id for cell in cells))

    def test_apply_paragraph_alignment_creates_para_style(self):
        source = Path("outputs/plan_report.hwpx")
        if not source.exists():
            self.skipTest("sample HWPX output is not available")

        output = Path("outputs/test_paragraph_alignment.hwpx")
        apply_standard_features(source, output, [{"key": "paragraph_alignment", "params": {"horizontal": "CENTER"}}])

        with zipfile.ZipFile(output) as zf:
            header = ET.fromstring(zf.read("Contents/header.xml"))
            section = ET.fromstring(zf.read("Contents/section0.xml"))

        centered = [
            para_pr
            for para_pr in header.iter(f"{{{HH_NS}}}paraPr")
            if (para_pr.find(f"{{{HH_NS}}}align") is not None and para_pr.find(f"{{{HH_NS}}}align").attrib.get("horizontal") == "CENTER")
        ]
        self.assertTrue(centered)
        new_id = centered[-1].attrib["id"]
        paragraphs = [paragraph for paragraph in section.iter(f"{{{HP_NS}}}p") if paragraph.attrib.get("paraPrIDRef") == new_id]
        self.assertTrue(paragraphs)

    def test_apply_table_dimensions_sets_cell_margin(self):
        source = Path("_analysis/templates_ascii/template_1.hwpx")
        if not source.exists():
            self.skipTest("sample template is not available")

        output = Path("outputs/test_table_dimensions.hwpx")
        apply_standard_features(source, output, [{"key": "table_dimensions", "params": {"margin": "0", "cell_spacing": "0"}}])

        with zipfile.ZipFile(output) as zf:
            section = ET.fromstring(zf.read("Contents/section0.xml"))

        margins = list(section.iter(f"{{{HP_NS}}}cellMargin"))
        self.assertTrue(margins)
        self.assertTrue(all(margin.attrib.get("left") == "0" for margin in margins))

    def test_numeric_calculation_expands_arrow_change(self):
        source = Path("outputs/plan_report.hwpx")
        if not source.exists():
            self.skipTest("sample HWPX output is not available")

        seeded = Path("outputs/test_numeric_seed.hwpx")
        calculated = Path("outputs/test_numeric_calculation.hwpx")
        with zipfile.ZipFile(source, "r") as src, zipfile.ZipFile(seeded, "w", compression=zipfile.ZIP_DEFLATED) as dst:
            for info in src.infolist():
                data = src.read(info.filename)
                if info.filename == "Contents/section0.xml":
                    section = ET.fromstring(data)
                    first_text = next(section.iter(f"{{{HP_NS}}}t"))
                    first_text.text = "100 -> 120"
                    data = ET.tostring(section, encoding="utf-8", xml_declaration=True)
                dst.writestr(info, data)

        apply_standard_features(seeded, calculated, ["numeric_calculation"])

        with zipfile.ZipFile(calculated) as zf:
            section_text = zf.read("Contents/section0.xml").decode("utf-8", errors="replace")
        self.assertIn("(+20, +20.0%)", section_text)

    def test_document_blocks_appends_paragraph_clone(self):
        source = Path("outputs/plan_report.hwpx")
        if not source.exists():
            self.skipTest("sample HWPX output is not available")

        output = Path("outputs/test_document_blocks.hwpx")
        apply_standard_features(source, output, [{"key": "document_blocks", "params": {"paragraphs": ["추가 검토사항"]}}])

        with zipfile.ZipFile(output) as zf:
            section_text = zf.read("Contents/section0.xml").decode("utf-8", errors="replace")
        self.assertIn("추가 검토사항", section_text)

    def test_table_merge_split_updates_cell_span(self):
        source = Path("_analysis/templates_ascii/template_1.hwpx")
        if not source.exists():
            self.skipTest("sample template is not available")

        output = Path("outputs/test_table_merge.hwpx")
        apply_standard_features(source, output, [{"key": "table_merge_split", "params": {"cols": 2, "rows": 1}}])

        with zipfile.ZipFile(output) as zf:
            section = ET.fromstring(zf.read("Contents/section0.xml"))
        first_span = next(section.iter(f"{{{HP_NS}}}cellSpan"))
        self.assertEqual(first_span.attrib.get("colSpan"), "2")


if __name__ == "__main__":
    unittest.main()
