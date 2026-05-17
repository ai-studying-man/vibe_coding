# 범정부오피스 분석 요약

## 입력 자료

- `범정부오피스20250819.zip`: ZIP 안에는 소스 트리가 아니라 단일 Windows 실행 파일 `범정부오피스20250819.exe`만 들어 있다.
- `범정부오피스(행안부)가이드북.pdf`: 78쪽 PDF다. `_analysis/converted/guidebook.md`로 변환했으며 76쪽에서 텍스트가 추출되었다. 워크플로 요약은 `docs/guidebook_workflows.md`에 정리했다.

혁신24 공개 게시글에 따르면 범정부오피스는 행정안전부가 배포한 공무원 보고서 편집 자동화 프로그램이며, 주요 기능은 글머리/폰트/내어쓰기 지정, 특수문자 삽입, 제목/소제목/참고/글상자/행정안전부 로고 표서식, 금액 한글화, 만나이 계산, 셀 역방향 합계, 어절 보호 글자간격 조절, 표 서식 변환, 조직도/회의명판/엑셀취합 자동화 등이다.

## 실행 파일 구조

실행 파일은 PyInstaller 패키지다.

- Python 런타임: `python311.dll`
- GUI: `tkinter`
- Windows/Hangul 연동: `pywin32`, `pythoncom`, `win32ui`
- 내부 앱 모듈:
  - `메인.py`: Tkinter UI와 버튼 라우팅
  - `인터페이스/인터페이스.py`: 버튼, 프레임, 이미지 UI helper
  - `한컴오피스/한컴라이브러리.py`: 한컴오피스 COM 자동화 핵심
  - `엑셀/엑셀라이브러리.py`: Excel 자동화 helper

Python 3.11 bytecode라 일반 `decompyle3`로는 완전 소스 복원이 되지 않는다. 대신 PyInstaller CArchive/PYZ를 추출하고 code object의 함수명, 문자열, import/name 테이블을 요약했다. 결과물은 `_analysis/code_summary.md`와 `_analysis/code_summary.json`에 있다.

이후 최신 prebuilt Decompyle++/`pycdc`를 적용해 앱 bytecode 4개를 `.py` 형태로 복원했다.

- `recovered_source/main.py`
- `recovered_source/hancom_library.py`
- `recovered_source/excel_library.py`
- `recovered_source/interface.py`

복원본은 모두 Python AST 파싱이 가능하지만, Python 3.11 opcode 일부는 `pycdc`가 완전 복원하지 못해 `# WARNING: Decompyle incomplete`가 남아 있다. 복원 현황과 불완전 영역은 `docs/decompile_report.md`, 함수/클래스 인덱스는 `docs/recovered_source_index.md`에 정리했다.

## 포함 자산

추출 결과:

- PNG 아이콘 약 2,092개
- HWP 템플릿 22개
- HWPX 템플릿 5개

HWPX 템플릿은 표준 `application/hwp+zip` 패키지이며 `Contents/header.xml`, `Contents/section0.xml`, `Contents/content.hpf` 구조를 가진다.

## 기능 구조 해석

원본 앱은 “문서 생성 엔진”이라기보다 “한글 편집 명령 버튼 모음”에 가깝다.

- 사용자가 한글 문서를 열어둔다.
- Tkinter 버튼을 누르면 `한컴라이브러리` 함수가 HwpObject Action/ParameterSet/Run 명령을 호출한다.
- 표준 문단, 제목, 소제목, 표 스타일, 붙임, 로고, 결재서식, 기관별 보고서식을 즉시 삽입하거나 현재 블록/표에 적용한다.

이 구조는 빠르지만 Windows + 한컴오피스 설치 + COM 자동화에 강하게 묶인다.

## 재구성 방향

본 프로젝트는 다음 구조로 재구성했다.

1. AI Agent 또는 사용자가 `OfficialDocument` JSON을 만든다.
2. `office_bumpis.renderer`가 공문 Markdown으로 정규화한다.
3. `office_bumpis.hwpx`가 `kordoc`의 `markdownToHwpx`로 HWPX 파일을 생성한다.
4. `office_bumpis.llm_adapter`는 Ollama/vLLM/LM Studio 같은 OpenAI-compatible 로컬 LLM에서 JSON 초안을 받는다.
5. `office_bumpis.profiles`는 추출된 HWPX 템플릿 profile을 공문 JSON skeleton으로 바꾼다.

이 방식은 원본의 반복 편집 자동화 철학은 유지하되, COM 버튼 호출 대신 “데이터 -> 문서” 파이프라인으로 바꾼다.

## Profile mapping

추출된 5개 HWPX 템플릿은 다음 생성 profile로 연결했다.

- `approval_sheet`: 생산등록번호, 등록일, 결재일, 공개 구분, 협조, 제목, 개요, 주요 내용, 향후 계획, 붙임
- `plan_report`: 등록번호, 결재선, 추진 배경, 목적 및 추진 방향, 추진 계획, 향후 일정, 행정 사항
- `work_reference`: 업무참고용, 목적, 주요 내용, 향후 계획, 보고자
- `meeting_brief`: 열린 정책간담회 형식, 실시사항, 예정사항, 목적, 일시, 참석 대상, 주요 내용
- `comprehensive_plan`: 종합 추진계획 형식, 목차 성격의 장 구성, 추진배경, 추진방향, 중점과제, 행정사항, 붙임

LLM 연동 시에는 profile을 지정해 모델이 자유 형식 문서를 직접 만들지 않게 하고, 모델 출력은 seed JSON으로 제한한 뒤 deterministic preset으로 공문 구조를 확장한다. 이렇게 하면 로컬 오픈소스 LLM의 문체 생성 능력은 쓰되, 결재/붙임/행정사항 같은 공문 골격은 코드에서 일관되게 유지할 수 있다.
