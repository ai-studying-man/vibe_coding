# AI Agent Feature Operations

## 목적

Ollama 또는 다른 오픈소스 LLM 에이전트가 공문서 내용을 정리한 뒤, HWPX 표준 기능을 코드 수정 없이 조합해서 적용할 수 있도록 공통 JSON 명령 형식을 사용한다.

## 기본 흐름

1. HWPX 양식 1개를 `generate-from-template`에 전달한다.
2. 텍스트 파일을 함께 전달한다.
3. 에이전트가 필요한 공통 기능을 JSON 배열로 만든다.
4. CLI가 양식 학습, 텍스트 초안화, HWPX 채우기, 구조 검증, 기능 적용을 순서대로 실행한다.

```powershell
python -m office_bumpis generate-from-template `
  outputs/plan_report.hwpx `
  outputs/one_step_text.txt `
  -o outputs/agent_generated.hwpx `
  --features-json outputs/agent_feature_ops.json
```

`--features-json`은 JSON 문자열, JSON 파일 경로, `@파일경로`를 모두 받을 수 있다. 여러 번 지정하면 앞에서부터 이어 붙인다.

## JSON 형식

```json
[
  {"key": "font_color", "params": {"color": "#005BAC"}},
  {"key": "paragraph_alignment", "params": {"horizontal": "CENTER"}},
  {"key": "table_dimensions", "params": {"margin": "0", "cell_spacing": "0"}},
  {"key": "document_blocks", "params": {"paragraphs": ["추가 검토사항"]}}
]
```

각 항목은 `key`와 `params`를 가진다. `key`는 `python -m office_bumpis features`에서 확인할 수 있는 표준 기능명이다.

## 단일 문서에 기능만 적용

생성된 HWPX 또는 기존 HWPX에 기능만 다시 적용할 때는 `apply-feature`를 사용한다.

```powershell
python -m office_bumpis apply-feature `
  outputs/agent_generated.hwpx `
  -o outputs/agent_generated_styled.hwpx `
  --features-json '[{"key":"transparent_table","params":{}}]'
```

기존 간편 옵션도 유지된다.

```powershell
python -m office_bumpis apply-feature `
  outputs/agent_generated.hwpx `
  -o outputs/agent_generated_blue.hwpx `
  --feature font_color `
  --color "#005BAC"
```

## 현재 구현된 공통 기능

- `normalize_whitespace`: 공백 정리
- `remove_empty_lines`: 빈 줄 정리
- `font_color`: 글자색
- `font_size`: 글자 크기
- `font_family`: 글씨체. `params.face`로 한글/한자/일본어/기타/사용자 글꼴을, `params.latin_face`로 영문 글꼴을 지정한다.
- `character_width`: 장평. `params.ratio`로 한글/영문/한자/기타 글자 폭 비율을 지정한다.
- `text_background`: 글자 배경색
- `strike_or_underline`: 취소선/밑줄
- `paragraph_alignment`: 문단 정렬
- `paragraph_spacing`: 문단 간격
- `page_layout`: 문서 여백/용지. `params.left/right/top/bottom/header/footer`는 mm 기준이며 `params.orientation`은 `portrait` 또는 `landscape`를 받는다.
- `page_border`: 문서 테두리. `params.type`, `params.width`, `params.color`, `params.offset`으로 페이지 경계선과 오프셋을 적용하고 `params.remove`로 제거한다.
- `page_number`: 쪽번호 표시/숨김/새 번호. `params.mode`는 `show`, `hide`, `reset`, `params.start`는 시작 쪽번호다.
- `table_background`: 표 배경색
- `table_border`: 표 테두리
- `transparent_table`: 투명표
- `remove_table_background`: 표 배경 제거
- `table_dimensions`: 표 크기/셀 여백
- `table_merge_split`: 표 병합/분할
- `table_rows`: 표 행 추가/삭제. `params.mode`는 `append` 또는 `delete`, `params.count`는 행 수, `params.values`는 추가 행 셀 값 배열이다.
- `table_columns`: 표 열 추가/삭제. `params.mode`는 `append` 또는 `delete`, `params.position`은 `left` 또는 `right`, `params.values`는 추가 열의 행별 셀 값 배열이다.
- `table_sort`: 표 정렬
- `numeric_calculation`: 숫자 계산
- `document_blocks`: 문서 블록 추가

구조 검증은 기능 적용 전의 템플릿 채우기 결과에 대해 실행된다. 기능 적용은 `header.xml`과 `section*.xml`을 대상으로 XML-first 방식으로 처리한다.
