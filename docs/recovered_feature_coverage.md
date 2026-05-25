# Recovered Feature Coverage

## Summary

- Source root: `recovered_source`
- Recovered symbols: 2593
- Matched symbols: 1075
- Unmatched symbols: 1518
- HAction calls: 5712

## Feature Hits

| Feature | Hits |
| --- | ---: |
| character_emphasis | 181 |
| character_shadow | 1 |
| character_spacing | 9 |
| character_width | 8 |
| cleanup_whitespace | 19 |
| control_characters | 369 |
| document_blocks | 468 |
| font_color | 235 |
| font_family | 223 |
| font_size | 13 |
| numeric_calculation | 40 |
| page_border | 3 |
| page_break | 30 |
| page_layout | 29 |
| page_number | 5 |
| paragraph_alignment | 304 |
| paragraph_spacing | 323 |
| remove_empty_lines | 1 |
| strike_or_underline | 9 |
| superscript_subscript | 7 |
| table_background | 144 |
| table_border | 15 |
| table_columns | 12 |
| table_dimensions | 77 |
| table_merge_split | 104 |
| table_rows | 75 |
| table_sort | 7 |
| text_background | 42 |
| transparent_table | 10 |

## Top HActions

| HAction | Hits |
| --- | ---: |
| BreakPara | 1199 |
| TableCellBlockExtend | 560 |
| TableRightCellAppend | 477 |
| TableCellBlock | 431 |
| ParagraphShapeAlignCenter | 397 |
| CharShapeBold | 329 |
| ParagraphShapeAlignJustify | 315 |
| TableMergeCell | 276 |
| MoveRight | 270 |
| CharShapeNormal | 223 |
| Cancel | 179 |
| InsertFixedWidthSpace | 134 |
| TableResizeExLeft | 92 |
| ParagraphShapeAlignRight | 88 |
| InsertTab | 68 |
| TableLeftCell | 61 |
| TableUpperCell | 60 |
| BreakPage | 40 |
| ParagraphShapeAlignDistribute | 35 |
| TableRightCell | 33 |
| TableResizeExUp | 22 |
| CharShape | 18 |
| TablePropertyDialog | 18 |
| Select | 18 |
| DeleteBack | 16 |
| CloseEx | 15 |
| PageSetup | 14 |
| TableColBegin | 13 |
| TableInsertLowerRow | 12 |
| TableDeleteRow | 12 |
| Delete | 11 |
| CharShapeSuperscript | 11 |
| ParagraphShape | 10 |
| MoveLeft | 10 |
| CharShapeUnderline | 9 |
| CellBorderFill | 9 |
| TableLowerCell | 9 |
| TableDistributeCellHeight | 9 |
| Cut | 8 |
| CharShapeSpacingIncrease | 8 |

## Matched Symbols

| Kind | Name | Features | File:Line |
| --- | --- | --- | --- |
| function | 값만붙임 | document_blocks | excel_library.py:33 |
| function | 배경색 | font_color, text_background | excel_library.py:41 |
| function | 서식붙임 | document_blocks | excel_library.py:45 |
| function | 취소선 | strike_or_underline | excel_library.py:49 |
| function | 공백정리 | cleanup_whitespace | excel_library.py:111 |
| function | 투명표 | transparent_table | excel_library.py:126 |
| function | 기본테두리 | table_border | excel_library.py:171 |
| function | 진한테두리 | table_border | excel_library.py:182 |
| function | 기본글자 | character_emphasis | excel_library.py:197 |
| function | 랜덤정렬 | paragraph_alignment | excel_library.py:216 |
| function | 병합해제 | table_merge_split | excel_library.py:288 |
| function | 산출근거계산 | numeric_calculation | excel_library.py:296 |
| function | 순환붙임 | document_blocks | excel_library.py:327 |
| function | 제목 | document_blocks | excel_library.py:456 |
| function | 직제순정렬 | paragraph_alignment | excel_library.py:467 |
| function | 가운데정렬 | paragraph_alignment, paragraph_spacing | hancom_library.py:54 |
| function | 고정여백 | cleanup_whitespace, control_characters, table_dimensions | hancom_library.py:58 |
| function | 기본정렬 | paragraph_alignment, paragraph_spacing | hancom_library.py:68 |
| function | 기본글자 | character_emphasis, font_color, font_family | hancom_library.py:72 |
| function | 글자작게 | font_color, font_family, font_size, table_dimensions | hancom_library.py:76 |
| function | 글자크게 | font_color, font_family, font_size, table_dimensions | hancom_library.py:82 |
| function | 다음페이지 | page_break | hancom_library.py:88 |
| function | 도형나가기 | control_characters | hancom_library.py:92 |
| function | 밑줄 | font_color, font_family, strike_or_underline | hancom_library.py:111 |
| function | 배분정렬 | paragraph_alignment, paragraph_spacing | hancom_library.py:115 |
| function | 셀병합 | table_merge_split | hancom_library.py:123 |
| function | 셀선택 | table_background | hancom_library.py:127 |
| function | 셀전체 | table_background | hancom_library.py:132 |
| function | 엔터 | control_characters | hancom_library.py:138 |
| function | 오른쪽정렬 | paragraph_alignment, paragraph_spacing | hancom_library.py:144 |
| function | 윗첨자 | font_color, font_family, superscript_subscript | hancom_library.py:148 |
| function | 진하게 | character_emphasis, font_color, font_family | hancom_library.py:152 |
| function | 표나가기 | control_characters, paragraph_alignment, paragraph_spacing | hancom_library.py:156 |
| function | 표너비줄이기 | table_dimensions | hancom_library.py:162 |
| function | 표오른쪽 | table_rows | hancom_library.py:168 |
| function | 표전체 | table_background | hancom_library.py:200 |
| function | 탭 | control_characters | hancom_library.py:220 |
| function | 고급붙임 | document_blocks | hancom_library.py:224 |
| function | 글자간격 | character_spacing, font_color, font_family | hancom_library.py:247 |
| function | 글자그림자 | character_shadow, font_color, font_family | hancom_library.py:261 |
| function | 글자마이 | font_color, font_family, font_size, table_dimensions | hancom_library.py:271 |
| function | 글자문단모양복사 | paragraph_spacing | hancom_library.py:276 |
| function | 글자색 | font_color, font_family | hancom_library.py:284 |
| function | 글자음영 | font_color, font_family, text_background | hancom_library.py:307 |
| function | 글자장평 | character_width, font_color, font_family | hancom_library.py:315 |
| function | 글자크기 | font_color, font_family, font_size | hancom_library.py:329 |
| function | 글자크기찾기 | font_size | hancom_library.py:337 |
| function | 글자색찾기 | font_color | hancom_library.py:349 |
| function | 글자플이 | font_color, font_family, font_size, table_dimensions | hancom_library.py:362 |
| function | 내어쓰기 | paragraph_spacing | hancom_library.py:367 |
| function | 대각선 | table_border | hancom_library.py:383 |
| function | 문단여백 | paragraph_spacing | hancom_library.py:544 |
| function | 문단여백측정 | page_layout, paragraph_spacing | hancom_library.py:553 |
| function | 문단위 | paragraph_spacing | hancom_library.py:561 |
| function | 문단아래 | paragraph_spacing | hancom_library.py:569 |
| function | 문단음영 | paragraph_spacing, text_background | hancom_library.py:577 |
| function | 문서여백 | page_layout | hancom_library.py:583 |
| function | 문서여백새페이지 | page_layout | hancom_library.py:595 |
| function | 문서용지복사 | page_layout | hancom_library.py:607 |
| function | 문서용지붙임 | document_blocks, page_layout | hancom_library.py:621 |
| function | 문서테두리 | page_border, table_border | hancom_library.py:633 |
| function | 문장 | document_blocks | hancom_library.py:661 |
| function | 밑줄얇굵 | font_color, font_family, strike_or_underline | hancom_library.py:669 |
| function | 블록첫위치 | document_blocks | hancom_library.py:678 |
| function | 블록끝위치 | document_blocks | hancom_library.py:685 |
| function | 블록스캔 | document_blocks | hancom_library.py:692 |
| function | 사진 | table_rows | hancom_library.py:699 |
| function | 사진넣기 | paragraph_alignment, paragraph_spacing | hancom_library.py:715 |
| function | 사진넣기배경 | text_background | hancom_library.py:722 |
| function | 사진넣기절대값 | paragraph_alignment, paragraph_spacing | hancom_library.py:728 |
| function | 상단캡션 | table_dimensions | hancom_library.py:735 |
| function | 셀나누기 | table_merge_split | hancom_library.py:746 |
| function | 셀높이넓이복사 | table_dimensions | hancom_library.py:753 |
| function | 셀높이붙여넣기 | table_dimensions | hancom_library.py:764 |
| function | 셀높이지정 | table_dimensions | hancom_library.py:774 |
| function | 셀넓이붙여넣기 | table_dimensions | hancom_library.py:784 |
| function | 셀여백제로 | table_dimensions | hancom_library.py:794 |
| function | 셀여백지정 | table_dimensions | hancom_library.py:807 |
| function | 셀세로정렬 | paragraph_alignment, table_dimensions | hancom_library.py:820 |
| function | 셀한줄 | table_dimensions | hancom_library.py:831 |
| function | 자간헌터 | paragraph_spacing | hancom_library.py:854 |
| function | 제목셀반복 | document_blocks, table_dimensions | hancom_library.py:894 |
| function | 쪽번호 | page_number | hancom_library.py:912 |
| function | 쪽새번호 | page_number | hancom_library.py:920 |
| function | 쪽번호숨기기 | page_number | hancom_library.py:929 |
| function | 쪽번호보이기 | page_number | hancom_library.py:937 |
| function | 쪽번호초기화 | page_number | hancom_library.py:945 |
| function | 줄간격 | paragraph_spacing | hancom_library.py:956 |
| function | 중고딕 | font_color, font_family | hancom_library.py:973 |
| function | 탭점선설정 | paragraph_spacing | hancom_library.py:1009 |
| function | 탭점선제거 | paragraph_spacing | hancom_library.py:1021 |
| function | 표내부선색 | font_color, table_border | hancom_library.py:1039 |
| function | 표내부선굵기 | table_border | hancom_library.py:1048 |
| function | 표내부선타입 | table_border | hancom_library.py:1057 |
| function | 표단일선 | table_border | hancom_library.py:1066 |
| function | 표배경그라데이션 | table_background, text_background | hancom_library.py:1102 |
| function | 표배경색 | font_color, table_background, text_background | hancom_library.py:1176 |
| function | 표배경제거 | table_background, text_background, transparent_table | hancom_library.py:1186 |
| function | 표밖여백제로 | table_dimensions | hancom_library.py:1195 |
| function | 표문장변환 | document_blocks | hancom_library.py:1206 |
| function | 표테두리굵기 | table_border | hancom_library.py:1215 |
| function | 표테두리단일선 | table_border | hancom_library.py:1226 |
| function | 표테두리단일선색 | font_color, table_border | hancom_library.py:1245 |
| function | 표테두리색 | font_color, table_border | hancom_library.py:1260 |
| function | 표테두리타입 | table_border, transparent_table | hancom_library.py:1271 |
| function | 폰트 | font_color, font_family | hancom_library.py:1288 |
| function | 화면비율 | numeric_calculation | hancom_library.py:1369 |
| function | 휴먼명조 | font_color, font_family | hancom_library.py:1383 |
| function | 증감계산 | numeric_calculation | hancom_library.py:1463 |
| function | 블록한줄개선 | document_blocks | hancom_library.py:1533 |
| function | 문장풀 | character_emphasis, document_blocks, font_color, font_family, paragraph_alignment, paragraph_spacing | hancom_library.py:1546 |
| function | 블록리스트생성 | document_blocks | hancom_library.py:1649 |
| function | 합계수식 | numeric_calculation | hancom_library.py:1658 |
| function | 빼기수식 | numeric_calculation | hancom_library.py:1666 |
| function | 블록텍스트 | document_blocks | hancom_library.py:1674 |
| function | 글자문단모양기본 | character_emphasis, font_color, font_family, paragraph_alignment, paragraph_spacing | hancom_library.py:1683 |
| function | 글자크기좌표리스트 | font_size | hancom_library.py:1730 |
| function | 문장쌈 | document_blocks | hancom_library.py:1882 |
| function | 블록계산 | document_blocks, numeric_calculation | hancom_library.py:1898 |
| function | 블록글머리 | document_blocks | hancom_library.py:1923 |
