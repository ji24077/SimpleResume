# 기능별 `feature/*` 브랜치 가이드

코드 동작은 바꾸지 않고, **어떤 종류의 작업을 할 때 어떤 브랜치를 쓰면 되는지**만 정리합니다.  
실제 저장소에는 아래 이름으로 **로컬 브랜치가 이미 생성**되어 있으며, 모두 같은 시점의 `main` 커밋을 가리킵니다. 작업을 시작할 때 해당 브랜치로 체크아웃한 뒤 커밋하면 됩니다.

```bash
git fetch origin main
git checkout feature/<이름>
# 또는 최신 main 위에서: git checkout -b feature/<이름> origin/main
```

원격에 올릴 때:

```bash
git push -u origin feature/<이름>
```

---

## 브랜치 목록 (역할)

| 브랜치 | 담당 영역 (한 줄) | 작업 예시 |
|--------|-------------------|-----------|
| `feature/pdf-rendering` | **PDF로 굽기** — Docker/latexmk, 산출 PDF, 1페이지 여부 측정에 가까운 쪽 | 주로 `api/features/pdf_rendering/` |
| `feature/resume-generation` | **첫 생성(1차)** — LLM으로 이력서 본문·구조를 만드는 흐름 | 주로 `api/features/generation/prompts.py`, `structured_resume.py` |
| `feature/resume-generation-editorial` | **에디토리얼·부가 출력** — 코칭, 프리뷰 섹션, 톤/피드백 | `coaching`, `preview_sections`, 사용자에게 보여줄 설명 문구 |
| `feature/generation-revision-second-pass` | **두 번째 이후 생성(재시도·압축)** — 1페이지 맞추기, 밀도 확장 등 **서버가 모델을 다시 부르는 루프** | `resume_one_page_max_revisions`, density expand, “다시 써줘”에 해당하는 서버 측 재프롬프트 |
| `feature/error-recovery-compile` | **오류 시(컴파일)** — LaTeX 실패 시 복구 | 컴파일 에러 파싱, Fixer/heal, `rendered_latex` 기반 수정 루프 |
| `feature/error-recovery-json-schema` | **오류 시(JSON/스키마)** — `resume_data` 형식 깨짐 복구 | SCHEMA_ERROR, `resume_schema_heal_max`, structured 모드 스키마 힐 |
| `feature/error-recovery-ats-quality` | **오류·품질(ATS/체커)** — 텍스트 추출 스모크 이후 자동 수정·진단 | `api/features/resume_pipeline/` + `main.py`의 ATS/체커 루프 |
| `feature/api-extensions-flags` | **API·플래그·확장만** — 계약 유지한 채 필드/플래그 추가 | `FEATURE_*`, `extensions/`, 응답에 optional 필드만 추가 |

---

## 폴더 구조 (`api/features/`)

Git 브랜치 이름과 맞추기 쉽도록 **구현도 기능 폴더**로 나눠 두었습니다. (`api/` 루트의 `compile_pdf.py` / `prompts.py` / `structured_resume.py` 는 **기존 import 경로 유지용 shim**입니다.)

| 디렉터리 | 내용 |
|----------|------|
| `api/features/pdf_rendering/` | `compile_pdf.py`, `dhruv_preamble.tex`, `tex_assets/` |
| `api/features/generation/` | `prompts.py`, `structured_resume.py` |
| `api/features/resume_pipeline/` | lint → compile → 페이지 → ATS 등 게이트 |
| `api/features/paths.py` | preamble 등 공통 경로 |

**`extensions/`** 는 거버넌스상 “코어가 import 하지 않는” **옵션 확장**용이고, **`features/`** 는 제품 핵심 파이프라인 코드가 들어가는 곳입니다.

---

## 겹칠 때 규칙

1. **한 PR = 한 브랜치 = 한 주제**가 이상적입니다.  
2. **PDF 파이프**와 **프롬프트/생성**이 한 번에 바뀌어야 하면, **하나의 브랜치**에서 하되 PR 본문에  
   “PDF 쪽 변경 / 생성 쪽 변경”을 **문단으로 나눠** 적습니다. (거버넌스 문서와 동일)  
3. **보호된 코어 파일**(`/.github/core-protected-paths.txt`)을 건드리면 CI가 막습니다. 해당 수정이 필요하면 라벨 `allow-core-change` 또는 별도 승인 절차를 탑니다.  
4. 애매하면 **사용자에게 보이는 결과 기준**으로 가깝게 고릅니다. (예: “컴파일 에러 나면 고치는 로직” → `feature/error-recovery-compile`)

---

## 현재 로컬 브랜치 확인

```bash
git branch --list 'feature/*'
```

---

더 자세한 거버넌스는 [`AI_GOVERNANCE.md`](./AI_GOVERNANCE.md)를 참고하세요.
