# office_bumpis

`office_bumpis`는 범정부오피스 실행 파일과 가이드북을 분석한 결과를 바탕으로 만든 공문 자동화 뼈대입니다.

기존 범정부오피스는 PyInstaller로 패키징된 Tkinter + 한컴 COM 자동화 도구입니다. 이 프로젝트는 그 구조를 그대로 복제하지 않고, AI Agent가 만든 표준 JSON을 Markdown과 HWPX로 변환하는 독립 파이프라인을 제공합니다.

## 빠른 실행

```powershell
python -m office_bumpis generate examples\purchase_request.json -o outputs\purchase_request.hwpx --markdown outputs\purchase_request.md
```

HWPX 생성은 Node.js와 `kordoc`를 사용합니다. 실행 시 `npx --yes --package kordoc --package pdfjs-dist ...`가 호출됩니다.

## 템플릿 분석

추출된 HWPX 템플릿의 결재선, 목차, placeholder, 문서 profile을 인벤토리로 만들 수 있습니다.

```powershell
python -m office_bumpis inspect-templates _analysis\pyi_extract -o docs\template_inventory.json --markdown docs\template_inventory.md
```

## LLM 연동

Ollama, vLLM, LM Studio처럼 OpenAI-compatible `/v1/chat/completions` API를 제공하는 서버를 사용할 수 있습니다.

```powershell
$env:OPENAI_COMPATIBLE_BASE_URL="http://localhost:11434/v1"
$env:OPENAI_COMPATIBLE_MODEL="hf.co/unsloth/Qwen3-4B-Instruct-2507-GGUF:Q4_K_M"
python -m office_bumpis draft prompt.txt -o outputs\draft.hwpx --json outputs\draft.json
```

Profile을 지정하면 LLM은 seed JSON만 만들고, 결정적인 profile preset이 공문 구조를 확장합니다.

```powershell
python -m office_bumpis draft prompt.txt --profile plan_report -o outputs\draft_plan.hwpx --json outputs\draft_plan.json --markdown outputs\draft_plan.md
```

## 표준 JSON

핵심 필드는 다음과 같습니다.

- `title`: 공문 제목
- `sender`: 발신 기관
- `recipients`: 수신 기관 목록
- `registration_number`: 문서번호
- `date`: 작성일
- `body`: 문단, 목록, 표 블록
- `attachments`: 붙임 문서
- `approval`: 결재선

자세한 분석 내용은 [docs/source_analysis.md](docs/source_analysis.md)를 보십시오.

## Profile preset

추출된 HWPX 흐름을 기반으로 다음 profile preset을 제공합니다.

- `approval_sheet`
- `plan_report`
- `work_reference`
- `meeting_brief`
- `comprehensive_plan`

Seed JSON에서 title, sender, recipients, section 내용을 받아 표준 공문 JSON을 만들 수 있습니다.

```powershell
python -m office_bumpis preset plan_report --seed examples\plan_report_seed.json -o outputs\plan_report.json
python -m office_bumpis generate outputs\plan_report.json -o outputs\plan_report.hwpx --markdown outputs\plan_report.md
```
