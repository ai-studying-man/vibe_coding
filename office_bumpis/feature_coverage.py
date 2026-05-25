from __future__ import annotations

import ast
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .standard_features import STANDARD_FEATURES


@dataclass
class RecoveredSymbol:
    name: str
    kind: str
    file: str
    line: int
    actions: list[str] = field(default_factory=list)
    matched_features: list[str] = field(default_factory=list)


@dataclass
class FeatureCoverageReport:
    source_root: str
    recovered_symbol_count: int
    haction_count: int
    matched_symbol_count: int
    unmatched_symbol_count: int
    feature_hits: dict[str, int]
    category_hits: dict[str, int]
    haction_hits: dict[str, int]
    symbols: list[RecoveredSymbol]

    def to_dict(self) -> dict:
        data = asdict(self)
        data["symbols"] = [asdict(symbol) for symbol in self.symbols]
        return data

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


def analyze_recovered_feature_coverage(source_root: str | Path) -> FeatureCoverageReport:
    root = Path(source_root)
    symbols: list[RecoveredSymbol] = []
    haction_hits: Counter[str] = Counter()
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=str(path))
        action_by_function = _actions_by_function(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                actions = action_by_function.get(node, [])
                haction_hits.update(actions)
                matched = _match_features(node.name, actions)
                symbols.append(
                    RecoveredSymbol(
                        name=node.name,
                        kind="function",
                        file=str(path),
                        line=node.lineno,
                        actions=actions,
                        matched_features=matched,
                    )
                )
        for call in _button_calls(tree):
            name = _button_name(call)
            if not name:
                continue
            actions = _hactions_in_node(call)
            haction_hits.update(actions)
            matched = _match_features(name, actions)
            symbols.append(
                RecoveredSymbol(
                    name=name,
                    kind="button",
                    file=str(path),
                    line=getattr(call, "lineno", 0),
                    actions=actions,
                    matched_features=matched,
                )
            )

    feature_hits: Counter[str] = Counter()
    category_hits: Counter[str] = Counter()
    feature_category = {feature.key: feature.category.value for feature in STANDARD_FEATURES}
    for symbol in symbols:
        for key in symbol.matched_features:
            feature_hits[key] += 1
            category_hits[feature_category.get(key, "unknown")] += 1

    matched = sum(1 for symbol in symbols if symbol.matched_features)
    return FeatureCoverageReport(
        source_root=str(root),
        recovered_symbol_count=len(symbols),
        haction_count=sum(haction_hits.values()),
        matched_symbol_count=matched,
        unmatched_symbol_count=len(symbols) - matched,
        feature_hits=dict(sorted(feature_hits.items())),
        category_hits=dict(sorted(category_hits.items())),
        haction_hits=dict(haction_hits.most_common()),
        symbols=symbols,
    )


def render_coverage_markdown(report: FeatureCoverageReport) -> str:
    lines = [
        "# Recovered Feature Coverage",
        "",
        "## Summary",
        "",
        f"- Source root: `{report.source_root}`",
        f"- Recovered symbols: {report.recovered_symbol_count}",
        f"- Matched symbols: {report.matched_symbol_count}",
        f"- Unmatched symbols: {report.unmatched_symbol_count}",
        f"- HAction calls: {report.haction_count}",
        "",
        "## Feature Hits",
        "",
        "| Feature | Hits |",
        "| --- | ---: |",
    ]
    for key, count in report.feature_hits.items():
        lines.append(f"| {key} | {count} |")
    lines.extend(["", "## Top HActions", "", "| HAction | Hits |", "| --- | ---: |"])
    for key, count in list(report.haction_hits.items())[:40]:
        lines.append(f"| {key} | {count} |")
    lines.extend(["", "## Matched Symbols", "", "| Kind | Name | Features | File:Line |", "| --- | --- | --- | --- |"])
    for symbol in [item for item in report.symbols if item.matched_features][:120]:
        lines.append(
            f"| {symbol.kind} | {symbol.name} | {', '.join(symbol.matched_features)} | "
            f"{Path(symbol.file).name}:{symbol.line} |"
        )
    return "\n".join(lines) + "\n"


def _actions_by_function(tree: ast.AST) -> dict[ast.FunctionDef, list[str]]:
    result: dict[ast.FunctionDef, list[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            result[node] = _hactions_in_node(node)
    return result


def _button_calls(tree: ast.AST) -> list[ast.Call]:
    calls: list[ast.Call] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id in {"버튼", "토글버튼"}:
            calls.append(node)
    return calls


def _button_name(call: ast.Call) -> str:
    for arg in call.args:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            return Path(arg.value).stem
    return ""


def _hactions_in_node(node: ast.AST) -> list[str]:
    actions: list[str] = []
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        if _is_haction_call(child) and child.args:
            first = child.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                actions.append(first.value)
    return actions


def _is_haction_call(call: ast.Call) -> bool:
    func = call.func
    return isinstance(func, ast.Attribute) and func.attr in {"Run", "Execute", "GetDefault", "CreateAction"}


def _match_features(name: str, actions: list[str]) -> list[str]:
    haystack = " ".join([name, *actions]).lower()
    matched: set[str] = set()
    rules = {
        "cleanup_whitespace": ["공백", "space", "blank"],
        "remove_empty_lines": ["빈줄", "빈 줄", "emptyline"],
        "font_size": ["글자크기", "fontsize", "charshapeheight", "charshapesize"],
        "font_color": ["글자색", "색", "textcolor", "charshape"],
        "font_family": ["폰트", "글씨체", "글꼴", "fontface", "facename", "charshape"],
        "text_background": ["음영", "배경", "shade", "fillbrush"],
        "strike_or_underline": ["밑줄", "취소선", "underline", "strikeout", "charshapeunderline"],
        "paragraph_alignment": ["정렬", "align", "paragraphshapealign"],
        "paragraph_spacing": ["줄간격", "문단", "linespacing", "paragraphshape"],
        "paragraph_background": ["문단음영", "winbrushfacecolor"],
        "page_layout": ["문서여백", "문서용지", "pagesetup", "leftmargin", "rightmargin", "headerlen", "footerlen"],
        "page_border": ["문서테두리", "pageborder", "pageborderfill", "applytopageborderfill"],
        "table_background": ["표배경", "셀배경", "cellfill", "tablecell"],
        "table_border": ["테두리", "border", "cellborder"],
        "table_diagonal": ["대각선", "slashflag"],
        "transparent_table": ["투명", "transparent"],
        "table_dimensions": ["표크기", "셀크기", "resize", "width", "height", "tablepropertydialog"],
        "table_merge_split": ["병합", "나누기", "merge", "split", "tablemergecell"],
        "table_rows": ["행추가", "행삭제", "tablerightcellappend", "tableinsertlowerrow", "tabledeleterow", "appendrow", "deleterow"],
        "table_columns": ["열추가", "열삭제", "tableinsertleftcolumn", "tableinsertrightcolumn", "tabledeletecolumn", "appendcolumn", "deletecolumn"],
        "table_sort": ["오름차순", "내림차순", "sort"],
        "character_emphasis": ["charshapebold", "charshapenormal", "bold", "italic"],
        "superscript_subscript": ["charshapesuperscript", "charshapesubscript", "superscript", "subscript"],
        "character_spacing": ["charshapespacingincrease", "spacingincrease", "characterspacing"],
        "character_width": ["글자장평", "장평", "charshapewidthincrease", "charshapewidthdecrease", "ratiohangul"],
        "character_shadow": ["글자그림자", "shadowtype", "shadowoffset", "charshadowtype"],
        "control_characters": ["inserttab", "insertfixedwidthspace", "breakpara"],
        "page_break": ["breakpage", "pagebreak"],
        "page_number": ["쪽번호", "pagenumpos", "newnumber", "pagehiding", "hidefirstpagenum", "deletectrls"],
        "document_blocks": ["제목", "소제목", "붙임", "개요", "보고", "공문", "문장", "블록"],
        "numeric_calculation": ["계산", "금액", "비율", "증감", "sum", "formula"],
    }
    for feature in STANDARD_FEATURES:
        terms = list(rules.get(feature.key, [])) + [str(item).lower() for item in feature.recovered_names]
        if any(term and term.lower() in haystack for term in terms):
            matched.add(feature.key)
    return sorted(matched)
