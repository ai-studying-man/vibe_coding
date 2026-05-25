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

    def test_apply_font_family_creates_fontface_and_updates_runs(self):
        source = Path("outputs/plan_report.hwpx")
        if not source.exists():
            self.skipTest("sample HWPX output is not available")

        output = Path("outputs/test_font_family.hwpx")
        apply_standard_features(source, output, [{"key": "font_family", "params": {"face": "휴먼명조", "latin_face": "Times New Roman"}}])

        with zipfile.ZipFile(output) as zf:
            header = ET.fromstring(zf.read("Contents/header.xml"))
            section = ET.fromstring(zf.read("Contents/section0.xml"))

        hangul_font = [
            font
            for fontface in header.iter(f"{{{HH_NS}}}fontface")
            if fontface.attrib.get("lang") == "HANGUL"
            for font in fontface.findall(f"{{{HH_NS}}}font")
            if font.attrib.get("face") == "휴먼명조"
        ]
        self.assertTrue(hangul_font)
        new_font_id = hangul_font[-1].attrib["id"]
        matching_char_styles = []
        for char_pr in header.iter(f"{{{HH_NS}}}charPr"):
            font_ref = char_pr.find(f"{{{HH_NS}}}fontRef")
            if font_ref is not None and font_ref.attrib.get("hangul") == new_font_id:
                matching_char_styles.append(char_pr)
        self.assertTrue(matching_char_styles)
        new_char_id = matching_char_styles[-1].attrib["id"]
        runs = [run for run in section.iter(f"{{{HP_NS}}}run") if run.attrib.get("charPrIDRef") == new_char_id]
        self.assertTrue(runs)

    def test_apply_character_width_creates_ratio_style(self):
        source = Path("outputs/plan_report.hwpx")
        if not source.exists():
            self.skipTest("sample HWPX output is not available")

        output = Path("outputs/test_character_width.hwpx")
        apply_standard_features(source, output, [{"key": "character_width", "params": {"ratio": 92}}])

        with zipfile.ZipFile(output) as zf:
            header = ET.fromstring(zf.read("Contents/header.xml"))
            section = ET.fromstring(zf.read("Contents/section0.xml"))

        ratio_styles = []
        for char_pr in header.iter(f"{{{HH_NS}}}charPr"):
            ratio = char_pr.find(f"{{{HH_NS}}}ratio")
            if ratio is not None and ratio.attrib.get("hangul") == "92":
                ratio_styles.append(char_pr)
        self.assertTrue(ratio_styles)
        new_id = ratio_styles[-1].attrib["id"]
        runs = [run for run in section.iter(f"{{{HP_NS}}}run") if run.attrib.get("charPrIDRef") == new_id]
        self.assertTrue(runs)

    def test_apply_character_shadow_creates_shadow_style(self):
        source = Path("outputs/plan_report.hwpx")
        if not source.exists():
            self.skipTest("sample HWPX output is not available")

        output = Path("outputs/test_character_shadow.hwpx")
        apply_standard_features(
            source,
            output,
            [{"key": "character_shadow", "params": {"type": "DROP", "offset_x": 7, "offset_y": 9, "color": "#808080"}}],
        )

        with zipfile.ZipFile(output) as zf:
            header = ET.fromstring(zf.read("Contents/header.xml"))
            section = ET.fromstring(zf.read("Contents/section0.xml"))

        shadow_styles = []
        for char_pr in header.iter(f"{{{HH_NS}}}charPr"):
            shadow = char_pr.find(f"{{{HH_NS}}}shadow")
            if shadow is not None and shadow.attrib.get("type") == "DROP" and shadow.attrib.get("offsetX") == "7":
                shadow_styles.append(char_pr)
        self.assertTrue(shadow_styles)
        new_id = shadow_styles[-1].attrib["id"]
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

    def test_apply_page_layout_sets_page_margins(self):
        source = Path("_analysis/templates_ascii/template_1.hwpx")
        if not source.exists():
            self.skipTest("sample template is not available")

        output = Path("outputs/test_page_layout.hwpx")
        apply_standard_features(
            source,
            output,
            [{"key": "page_layout", "params": {"left": 20, "right": 18, "top": 15, "bottom": 12, "header": 10, "footer": 8}}],
        )

        with zipfile.ZipFile(output) as zf:
            section = ET.fromstring(zf.read("Contents/section0.xml"))

        margin = next(section.iter(f"{{{HP_NS}}}margin"))
        self.assertEqual(margin.attrib.get("left"), "5669")
        self.assertEqual(margin.attrib.get("right"), "5102")
        self.assertEqual(margin.attrib.get("header"), "2835")

    def test_apply_page_border_sets_border_fill_and_offsets(self):
        source = Path("_analysis/templates_ascii/template_1.hwpx")
        if not source.exists():
            self.skipTest("sample template is not available")

        output = Path("outputs/test_page_border.hwpx")
        apply_standard_features(
            source,
            output,
            [{"key": "page_border", "params": {"type": "SOLID", "width": "0.12 mm", "color": "#005BAC", "offset": 6}}],
        )

        with zipfile.ZipFile(output) as zf:
            header = ET.fromstring(zf.read("Contents/header.xml"))
            section = ET.fromstring(zf.read("Contents/section0.xml"))

        new_border = list(header.iter(f"{{{HH_NS}}}borderFill"))[-1]
        self.assertEqual(new_border.find(f"{{{HH_NS}}}leftBorder").attrib.get("color"), "#005BAC")
        page_border = next(section.iter(f"{{{HP_NS}}}pageBorderFill"))
        self.assertEqual(page_border.attrib.get("borderFillIDRef"), new_border.attrib["id"])
        offset = page_border.find(f"{{{HP_NS}}}offset")
        self.assertEqual(offset.attrib.get("left"), "1701")

    def test_apply_page_number_sets_start_and_visibility(self):
        source = Path("_analysis/templates_ascii/template_1.hwpx")
        if not source.exists():
            self.skipTest("sample template is not available")

        output = Path("outputs/test_page_number.hwpx")
        apply_standard_features(source, output, [{"key": "page_number", "params": {"mode": "hide", "start": 3}}])

        with zipfile.ZipFile(output) as zf:
            section = ET.fromstring(zf.read("Contents/section0.xml"))

        start_num = next(section.iter(f"{{{HP_NS}}}startNum"))
        visibility = next(section.iter(f"{{{HP_NS}}}visibility"))
        self.assertEqual(start_num.attrib.get("page"), "3")
        self.assertEqual(visibility.attrib.get("hideFirstPageNum"), "1")

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

    def test_table_rows_appends_values_and_updates_count(self):
        source = Path("_analysis/templates_ascii/template_1.hwpx")
        if not source.exists():
            self.skipTest("sample template is not available")

        with zipfile.ZipFile(source) as zf:
            before_section = ET.fromstring(zf.read("Contents/section0.xml"))
        before_table = next(before_section.iter(f"{{{HP_NS}}}tbl"))
        before_count = len(before_table.findall(f"{{{HP_NS}}}tr"))

        output = Path("outputs/test_table_rows_append.hwpx")
        apply_standard_features(
            source,
            output,
            [{"key": "table_rows", "params": {"mode": "append", "count": 1, "values": [["Added item", "Added value"]]}}],
        )

        with zipfile.ZipFile(output) as zf:
            section = ET.fromstring(zf.read("Contents/section0.xml"))
            section_text = zf.read("Contents/section0.xml").decode("utf-8", errors="replace")
        table = next(section.iter(f"{{{HP_NS}}}tbl"))
        rows = table.findall(f"{{{HP_NS}}}tr")

        self.assertEqual(len(rows), before_count + 1)
        self.assertEqual(table.attrib.get("rowCnt"), str(len(rows)))
        self.assertIn("Added item", section_text)

    def test_table_rows_deletes_data_row_preserving_header(self):
        source = Path("_analysis/templates_ascii/template_1.hwpx")
        if not source.exists():
            self.skipTest("sample template is not available")

        with zipfile.ZipFile(source) as zf:
            before_section = ET.fromstring(zf.read("Contents/section0.xml"))
        before_table = next(before_section.iter(f"{{{HP_NS}}}tbl"))
        before_count = len(before_table.findall(f"{{{HP_NS}}}tr"))

        output = Path("outputs/test_table_rows_delete.hwpx")
        apply_standard_features(source, output, [{"key": "table_rows", "params": {"mode": "delete", "count": 1, "header_rows": 1}}])

        with zipfile.ZipFile(output) as zf:
            section = ET.fromstring(zf.read("Contents/section0.xml"))
        table = next(section.iter(f"{{{HP_NS}}}tbl"))
        rows = table.findall(f"{{{HP_NS}}}tr")

        self.assertEqual(len(rows), max(1, before_count - 1))
        self.assertEqual(table.attrib.get("rowCnt"), str(len(rows)))

    def test_table_columns_appends_values_and_updates_count(self):
        source = Path("_analysis/templates_ascii/template_1.hwpx")
        if not source.exists():
            self.skipTest("sample template is not available")

        with zipfile.ZipFile(source) as zf:
            before_section = ET.fromstring(zf.read("Contents/section0.xml"))
        before_table = next(before_section.iter(f"{{{HP_NS}}}tbl"))
        before_count = int(before_table.attrib.get("colCnt", "0"))

        output = Path("outputs/test_table_columns_append.hwpx")
        apply_standard_features(
            source,
            output,
            [{"key": "table_columns", "params": {"mode": "append", "position": "right", "count": 1, "values": [["Added column"]]}}],
        )

        with zipfile.ZipFile(output) as zf:
            section = ET.fromstring(zf.read("Contents/section0.xml"))
            section_text = zf.read("Contents/section0.xml").decode("utf-8", errors="replace")
        table = next(section.iter(f"{{{HP_NS}}}tbl"))

        self.assertEqual(table.attrib.get("colCnt"), str(before_count + 1))
        self.assertIn("Added column", section_text)

    def test_table_columns_deletes_column_and_updates_count(self):
        source = Path("_analysis/templates_ascii/template_1.hwpx")
        if not source.exists():
            self.skipTest("sample template is not available")

        with zipfile.ZipFile(source) as zf:
            before_section = ET.fromstring(zf.read("Contents/section0.xml"))
        before_table = next(before_section.iter(f"{{{HP_NS}}}tbl"))
        before_count = int(before_table.attrib.get("colCnt", "0"))

        output = Path("outputs/test_table_columns_delete.hwpx")
        apply_standard_features(source, output, [{"key": "table_columns", "params": {"mode": "delete", "position": "right", "count": 1}}])

        with zipfile.ZipFile(output) as zf:
            section = ET.fromstring(zf.read("Contents/section0.xml"))
        table = next(section.iter(f"{{{HP_NS}}}tbl"))

        self.assertEqual(table.attrib.get("colCnt"), str(max(1, before_count - 1)))


if __name__ == "__main__":
    unittest.main()
