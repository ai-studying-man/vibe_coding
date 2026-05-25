# Standard HWPX Template Goal

> AI 에이전트가 공통 HWPX 기능을 JSON 작업 배열로 넘기는 CLI 계약은 [ai_agent_feature_operations.md](ai_agent_feature_operations.md)에 정리했다.

## Objective

기관별로 고정된 버튼/양식에 맞춰 문서를 작성하는 방식에서 벗어나, 사용자가 제공한 HWPX 문서 1개를 표준 양식 프로필로 학습한 뒤 새 텍스트를 같은 구조와 스타일에 맞춰 출력한다.

## Core Principle

LLM은 내용을 정리하고 슬롯을 제안한다. HWPX 생성과 서식 적용은 결정적 XML 엔진이 담당한다. 이 분리를 지켜야 원본 양식의 글자크기, 글씨체, 문단, 표, 여백, 결재란이 안정적으로 유지된다.

## Target Workflow

1. 사용자가 기관 HWPX 양식 1개를 업로드한다.
2. 엔진이 `Contents/header.xml`과 `Contents/section*.xml`을 분석한다.
3. 제목, 본문, 붙임, 표, 결재란, 반복 블록 후보를 슬롯으로 분류한다.
4. 글자 스타일(`hh:charPr`), 문단 스타일(`hh:paraPr`), 표/셀 스타일(`hh:borderFill`, `hp:tbl`, `hp:tc`)을 프로필로 저장한다.
5. 사용자가 텍스트를 입력한다.
6. Ollama LLM이 텍스트를 제목/본문/표 데이터 JSON으로 재가공한다.
7. 결정적 HWPX 엔진이 원본 XML 구조를 복제하고 슬롯 텍스트만 교체한다.
8. 필요 시 표준 기능 레지스트리의 공백정리, 투명표, 표 배경색, 테두리, 글자색 같은 기능을 공통 규칙으로 적용한다.
9. 최종 HWPX를 저장한다.

## Standard Feature Groups

범정부 오피스의 기관별 버튼은 다음 공통 기능군으로 정규화한다.

| Group | Examples | HWPX Strategy |
| --- | --- | --- |
| Text cleanup | 공백정리, 엔터정리, 셀공백제거 | `hp:t` 텍스트 정규화 |
| Character style | 글자크기, 글자색, 글자음영, 취소선, 밑줄 | `hh:charPr` 분석/복제/참조 |
| Paragraph style | 가운데정렬, 배분정렬, 줄간격, 문단여백, 들여쓰기, 문단 앞/뒤 간격, 문단 배경/테두리 | `hh:paraPr` 분석/복제/참조 |
| Table style | 투명표, 표배경색, 표배경제거, 테두리색, 내부선 | `hh:borderFill`과 셀 borderFill 참조 적용 |
| Table structure | 셀병합, 행/열 추가, 셀 크기, 표 정렬 | `hp:tbl`, `hp:tr`, `hp:tc`, `rowSpan`, `colSpan` 변환 |
| Template block | 제목, 소제목, 붙임, 참고, 회색점선박스 | 학습한 `hp:p`/`hp:tbl` 블록 복제 |
| Calculation | 금액, 증감, 퍼센트, 셀합계 | 계산 후 `hp:t`/표 셀에 반영 |

## Current Implementation Status

- `office_bumpis/template_engine.py`: HWPX 업로드 양식 분석, 텍스트 노드/스타일 참조/표 개수 추출, 원본 양식 복제 후 텍스트 치환. `hh:fontface`를 해석해 글꼴 ID를 실제 글꼴명으로 풀고, `hh:paraPr`의 정렬/여백/들여쓰기/앞뒤 간격/문단 borderFill 참조와 `hh:borderFill` 세부 속성을 스타일 프로필에 저장한다. Ollama 프롬프트와 기본 파서는 학습된 슬롯/표 프로필을 참고해 제목, 본문, 표 데이터로 원문을 재구성한다.
- `office_bumpis/standard_features.py`: 범정부 오피스 버튼 기능을 공통 기능군으로 정규화한 레지스트리.
- `office_bumpis/hwpx_features.py`: 공통 기능 일부를 실제 HWPX XML 변환으로 적용한다. 현재 적용 가능 기능은 공백정리, 빈 줄 정리, 글자색, 글자크기, 글자음영, 밑줄/취소선, 문단 정렬, 문단 여백/간격, 표 배경색/배경제거, 투명표, 표 테두리/내부선, 표 크기/여백, 셀 병합/분할, 표 행 정렬, 금액/증감/비율 계산이다.
- `office_bumpis/structure_guard.py`: 생성 HWPX가 템플릿 대비 섹션, 스타일 수, 표 수, 슬롯별 글자/문단 스타일 참조를 보존했는지 검증한다. CLI에서는 `guard-output`으로 실행한다.
- `office_bumpis/cli.py`: `generate-from-template` 명령으로 HWPX 양식 1개와 텍스트 파일만 받아 프로필 학습, 초안 생성, HWPX 채우기, 구조 가드, 선택적 공통 기능 적용을 한 번에 실행한다.
- `office_bumpis/feature_coverage.py`: 복원된 EXE 소스의 함수, 버튼, HAction 호출을 스캔해 표준 기능 레지스트리와 매칭하는 커버리지 리포트를 만든다. CLI에서는 `feature-coverage`로 JSON/Markdown 리포트를 생성한다.
- `office_bumpis/template_profile.py`: HWPX 양식에서 제목/본문/붙임/표 슬롯과 데이터 표 프로토타입을 학습한다. 각 슬롯에는 `charPrIDRef`/`paraPrIDRef`뿐 아니라 해석된 글꼴명, 글자 높이, 문단 정렬/줄간격/여백/들여쓰기/문단 borderFill 참조를 함께 저장한다. 표 프로토타입에는 셀 텍스트뿐 아니라 행 속성, 셀 span/size/margin 속성도 함께 저장한다.
- `office_bumpis/profile_filler.py`: 학습한 슬롯 프로필을 기준으로 제목, 본문, 붙임, 표 데이터 행을 같은 양식에 채운다. 복수 표 입력 시 학습된 표의 열 수와 헤더 유사도를 비교해 가장 가까운 표 슬롯에 자동 매핑하고, Markdown 표의 헤더 행은 데이터 행으로 반복 삽입하지 않는다.
- `office_bumpis/webapp.py`: 문서 양식 업로드, 텍스트 입력, 생성하기, 저장하기 로컬 웹 UI.
- `office_bumpis/webapp.py`: 구현된 표준 기능 전체를 웹 체크박스로 노출하고, 웹 생성 경로에서도 CLI와 같은 `apply_standard_features` 변환을 사용한다. 생성 단계에서는 구조 가드를 실행해 슬롯/표 구조 보존 여부를 응답과 화면 상태 메시지에 표시한다. 양식 분석 후에는 학습 프로필 JSON, Markdown 요약, 분석 JSON, 원본 `header.xml`/`section*.xml`이 들어간 XML ZIP 번들을 `/profile/...` 경로로 내려받을 수 있다.
- `office_bumpis/llm_adapter.py`: Ollama/OpenAI-compatible LLM 연결 기반.

## Next Implementation Milestones

1. 슬롯 매핑 강화: 제목/본문/붙임/표/결재란을 텍스트 길이뿐 아니라 스타일, 위치, 표 내부 여부로 분류한다.
2. 스타일 프로필 저장: `charPrIDRef`, `paraPrIDRef`, `borderFillIDRef`를 사람이 읽을 수 있는 JSON 프로필로 내보낸다.
3. 표준 기능 적용기 확대: 반복 표 블록 생성, 복수 표 매핑, 표 헤더/본문 행 판별 정확도, 병합 셀 포함 표 데이터 입력을 강화한다.
4. 양식 블록 복제: 한 문단만 바꾸는 수준을 넘어 제목 블록, 본문 블록, 표 블록을 반복 생성한다.
5. LLM JSON 스키마 고정: Ollama 출력이 항상 `{title, sections, tables, attachments}` 형태가 되도록 검증한다.
