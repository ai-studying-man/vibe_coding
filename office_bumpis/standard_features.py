from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Callable


class FeatureCategory(str, Enum):
    TEXT_CLEANUP = "text_cleanup"
    CHARACTER_STYLE = "character_style"
    PARAGRAPH_STYLE = "paragraph_style"
    TABLE_STYLE = "table_style"
    TABLE_STRUCTURE = "table_structure"
    TEMPLATE_BLOCK = "template_block"
    CALCULATION = "calculation"


@dataclass(frozen=True)
class StandardFeature:
    key: str
    label: str
    category: FeatureCategory
    recovered_names: tuple[str, ...]
    hwpx_strategy: str
    implemented: bool = False


STANDARD_FEATURES: tuple[StandardFeature, ...] = (
    StandardFeature(
        "cleanup_whitespace",
        "공백정리",
        FeatureCategory.TEXT_CLEANUP,
        ("블록엔터정리공백정리", "블록엔터제거공백정리", "셀공백제거"),
        "hp:t 텍스트 값 정규화",
        True,
    ),
    StandardFeature(
        "remove_empty_lines",
        "빈 줄 정리",
        FeatureCategory.TEXT_CLEANUP,
        ("블록엔터제거공백정리",),
        "연속 개행/빈 hp:p 정리",
        True,
    ),
    StandardFeature(
        "font_size",
        "글자크기",
        FeatureCategory.CHARACTER_STYLE,
        ("글자크기", "글자크기찾기"),
        "Contents/header.xml의 hh:charPr height 복제/참조",
        True,
    ),
    StandardFeature(
        "font_color",
        "글자색",
        FeatureCategory.CHARACTER_STYLE,
        ("글자색", "글자색찾기"),
        "hh:charPr textColor 또는 새 charPr 생성",
        True,
    ),
    StandardFeature(
        "font_family",
        "글씨체",
        FeatureCategory.CHARACTER_STYLE,
        ("폰트", "휴먼명조", "중고딕", "CharShape"),
        "hh:fontface에 글꼴을 등록하고 hh:charPr fontRef를 새 글꼴 ID로 갱신",
        True,
    ),
    StandardFeature(
        "text_background",
        "글자음영",
        FeatureCategory.CHARACTER_STYLE,
        ("글자음영",),
        "hh:charPr shadeColor/borderFillIDRef 분석 후 적용",
        True,
    ),
    StandardFeature(
        "strike_or_underline",
        "취소선/밑줄",
        FeatureCategory.CHARACTER_STYLE,
        ("취소선", "밑줄", "CharShapeUnderline"),
        "hh:charPr 내부 밑줄/취소선 속성 생성",
        True,
    ),
    StandardFeature(
        "character_emphasis",
        "볼드/이탤릭/기본글자",
        FeatureCategory.CHARACTER_STYLE,
        ("CharShapeBold", "CharShapeNormal", "진하게", "기본글자"),
        "hh:charPr bold/italic 요소를 복제/제거하고 run 참조를 갱신",
        True,
    ),
    StandardFeature(
        "superscript_subscript",
        "위첨자/아래첨자",
        FeatureCategory.CHARACTER_STYLE,
        ("CharShapeSuperscript", "위첨자", "아래첨자"),
        "hh:charPr supscript type을 SUPERSCRIPT/SUBSCRIPT/NONE으로 설정",
        True,
    ),
    StandardFeature(
        "character_spacing",
        "자간",
        FeatureCategory.CHARACTER_STYLE,
        ("CharShapeSpacingIncrease", "자간넓게", "글자간격"),
        "hh:charPr spacing 속성을 언어별로 동일 적용",
        True,
    ),
    StandardFeature(
        "character_width",
        "장평",
        FeatureCategory.CHARACTER_STYLE,
        ("글자장평", "CharShapeWidthIncrease", "CharShapeWidthDecrease", "장평"),
        "hh:charPr ratio 속성을 언어별로 동일 적용",
        True,
    ),
    StandardFeature(
        "paragraph_alignment",
        "문단 정렬",
        FeatureCategory.PARAGRAPH_STYLE,
        ("가운데정렬", "배분정렬", "기본정렬"),
        "hh:paraPr align 속성 복제/참조",
        True,
    ),
    StandardFeature(
        "paragraph_spacing",
        "문단 여백/간격",
        FeatureCategory.PARAGRAPH_STYLE,
        ("문단여백", "문단아래", "줄간격"),
        "hh:paraPr margin/lineSpacing 분석 후 적용",
        True,
    ),
    StandardFeature(
        "page_layout",
        "문서 여백/용지",
        FeatureCategory.TEMPLATE_BLOCK,
        ("문서여백", "문서여백새페이지", "문서용지복사", "문서용지붙임", "PageSetup"),
        "hp:secPr/hp:pagePr의 용지 방향, 크기, left/right/top/bottom/header/footer 여백을 HWP 단위로 적용",
        True,
    ),
    StandardFeature(
        "page_border",
        "문서 테두리",
        FeatureCategory.TEMPLATE_BLOCK,
        ("문서테두리", "PageBorder", "PageBorderFillBoth"),
        "hh:borderFill을 생성하고 hp:pageBorderFill의 borderFillIDRef와 offset을 갱신",
        True,
    ),
    StandardFeature(
        "table_background",
        "표 배경색/배경제거",
        FeatureCategory.TABLE_STYLE,
        ("표배경색", "표배경제거", "표배경그라데이션"),
        "hh:borderFill fillBrush 또는 cell borderFillIDRef 적용",
        True,
    ),
    StandardFeature(
        "table_border",
        "표 테두리/내부선",
        FeatureCategory.TABLE_STYLE,
        ("표테두리굵기", "표테두리색", "표테두리타입", "표내부선굵기", "표내부선색", "표내부선타입"),
        "hh:borderFill left/right/top/bottom/inside 속성 적용",
        True,
    ),
    StandardFeature(
        "transparent_table",
        "투명표",
        FeatureCategory.TABLE_STYLE,
        ("투명표", "표배경제거", "표테두리타입"),
        "테두리 NONE + 채우기 없음 borderFill 프로필 적용",
        True,
    ),
    StandardFeature(
        "table_dimensions",
        "표 크기/여백",
        FeatureCategory.TABLE_STRUCTURE,
        ("표전체크기", "표밖여백제로", "셀높이동일", "셀넓이동일", "셀최소높이"),
        "hp:tbl, hp:tc, hp:cellSz, cellMargin 속성 조정",
        True,
    ),
    StandardFeature(
        "table_merge_split",
        "셀 병합/분할",
        FeatureCategory.TABLE_STRUCTURE,
        ("셀병합", "반갈셀", "TableMergeCell"),
        "rowSpan/colSpan과 셀 구조 변환",
        True,
    ),
    StandardFeature(
        "table_rows",
        "표 행 추가/삭제",
        FeatureCategory.TABLE_STRUCTURE,
        ("TableRightCellAppend", "TableInsertLowerRow", "TableDeleteRow", "row append", "row delete"),
        "hp:tr 행을 복제하거나 삭제하고 rowCnt와 cellAddr 행 인덱스를 갱신",
        True,
    ),
    StandardFeature(
        "table_columns",
        "표 열 추가/삭제",
        FeatureCategory.TABLE_STRUCTURE,
        ("TableInsertLeftColumn", "TableInsertRightColumn", "TableDeleteColumn", "column append", "column delete"),
        "hp:tc 열을 행별로 복제하거나 삭제하고 colCnt와 cellAddr 열 인덱스를 갱신",
        True,
    ),
    StandardFeature(
        "table_sort",
        "표 정렬",
        FeatureCategory.TABLE_STRUCTURE,
        ("문자오름차순", "문자내림차순", "숫자오름차순", "숫자내림차순"),
        "표 행 데이터를 파싱해 hp:tr 순서 재배치",
        True,
    ),
    StandardFeature(
        "document_blocks",
        "제목/소제목/붙임/참고 블록",
        FeatureCategory.TEMPLATE_BLOCK,
        ("문장", "기본서식표", "기본서식회색점선박스", "광주북구표준소제목"),
        "학습한 hp:p/hp:tbl 블록을 슬롯 템플릿으로 복제",
        True,
    ),
    StandardFeature(
        "control_characters",
        "탭/고정폭공백/줄바꿈 토큰",
        FeatureCategory.TEMPLATE_BLOCK,
        ("InsertTab", "InsertFixedWidthSpace", "BreakPara"),
        "본문 토큰을 hp:tab, hp:lineBreak, 고정폭 공백 문자로 변환",
        True,
    ),
    StandardFeature(
        "page_break",
        "쪽 나누기",
        FeatureCategory.TEMPLATE_BLOCK,
        ("BreakPage",),
        "지정 위치의 hp:p pageBreak 속성을 설정하거나 마지막 문단을 복제",
        True,
    ),
    StandardFeature(
        "page_number",
        "쪽번호 표시/숨김/새 번호",
        FeatureCategory.TEMPLATE_BLOCK,
        ("쪽번호", "쪽새번호", "쪽번호숨기기", "쪽번호보이기", "쪽번호초기화", "PageNumPos", "NewNumber", "PageHiding"),
        "hp:startNum page 값과 hp:visibility hideFirstPageNum 속성을 갱신",
        True,
    ),
    StandardFeature(
        "numeric_calculation",
        "금액/증감/비율 계산",
        FeatureCategory.CALCULATION,
        ("금액비율", "증감계산", "셀합계", "TableFormulaSumVer"),
        "텍스트/표 셀 값을 계산한 뒤 hp:t에 반영",
        True,
    ),
)


def normalize_whitespace(text: str, *, remove_empty_lines: bool = False) -> str:
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    if remove_empty_lines:
        lines = [line for line in lines if line]
    return "\n".join(lines).strip()


IMPLEMENTED_TEXT_FEATURES: dict[str, Callable[[str], str]] = {
    "cleanup_whitespace": normalize_whitespace,
    "remove_empty_lines": lambda value: normalize_whitespace(value, remove_empty_lines=True),
}


def feature_inventory() -> list[dict[str, str | bool]]:
    return [
        {
            "key": feature.key,
            "label": feature.label,
            "category": feature.category.value,
            "recovered_names": ", ".join(feature.recovered_names),
            "hwpx_strategy": feature.hwpx_strategy,
            "implemented": feature.implemented,
        }
        for feature in STANDARD_FEATURES
    ]
