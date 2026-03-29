# 구현 메모 · 엣지케이스 · 건드리면 안 되는 것

이 문서는 **지금까지 넣은 동작**과 **깨지기 쉬한 가정**을 한곳에 모아 둔 것입니다.  
레거시 규칙: `.cursor/rules/do-not-touch-pdf-and-env.mdc` — PDF 파이프라인·`.env` 임의 변경 금지는 그대로 따릅니다.

---

## 1. 생성 플로우

| 항목 | 위치 | 요약 |
|------|------|------|
| 동기 생성 | `POST /generate`, `/generate-json` | 폼/JSON → `_run_generate` |
| 스트림 생성 | `POST /generate-stream`, `/generate-json-stream` | NDJSON: `progress` → `result` / `error` |
| 웹 프록시 | `web/src/app/api/generate-stream/route.ts` | multipart → 백엔드 `generate-stream`, JSON → `generate-json-stream` |
| UI | `web/src/app/page.tsx` | 붙여넣기/파일, `page_policy`, 스트림 파싱, 연락처 필드 |

**엣지케이스**

- 스트림이 끊기면 `result` 없이 끝날 수 있음 → 클라이언트는 `type === "result"` 필수 확인.
- `OPENAI_API_KEY` 없으면 스트림 시작 전 JSON 에러(비스트림 경로와 동일).

---

## 2. 페이지 정책 (`strict_one_page` vs `allow_multi`)

| 정책 | 동작 |
|------|------|
| `strict_one_page` | 컴파일 → 페이지 수 루프 → 2p+면 “완만한 트림” 재요청(경력·원문 사실 유지 지시). |
| `allow_multi` | 1페이지 강제 루프 생략, 한 번 컴파일해 `pdf_page_count`만 붙임. |

**엣지케이스**

- `RESUME_ONE_PAGE_MAX_REVISIONS=0` 이면 strict여도 페이지 루프 비활성.
- 모델이 지시를 어기면 여전히 2페이지 또는 정보 누락 가능 → 프롬프트·`max_revisions`로만 완화.

---

## 3. “꽉 찬 1페이지” 밀도 (underfull)

| 항목 | 위치 |
|------|------|
| 하단 밝기 측정 | `compile_pdf.pdf_bottom_strip_mean_luminance` (`pdftoppm` + Pillow) |
| underfull 판정 | `main.py` — 골든: `mean > GOLDEN_MEAN + MARGIN`, 절대: `mean >= THRESHOLD` |
| 확장 LLM | `_revision_user_expand_density` |
| 운영 체크 | `api/OPS_CHECKLIST.md`, `/health` → `pdf_density_check_ready` |

**엣지케이스**

- `pdftoppm`/Pillow 없으면 측정 `None` → underfull 루프 의사결정 없이 통과.
- 원문이 짧으면 짧게 끝나는 것이 정상 → `revision_log_ko`에 안내 문구(`_append_one_page_done_notes`).
- 골든과 절대 임계 동시 설정 시 **골든이 우선**(코드상 `golden_mean is not None`이면 절대 임계 무시).

---

## 4. LaTeX 정리 · 컴파일 안정성 (`compile_pdf.py`)

다음은 **컴파일/미리보기 직전**에 적용됨 (`sanitize_latex_for_overleaf`, `sanitize_unicode_for_latex`, `normalize_to_dhruv_template`).

| 수정 | 이유 |
|------|------|
| `\\%` → `\%` | 이중 백슬래시 + `%` 가 줄바꿈·주석으로 레이아웃 깨짐. |
| `\\&` → `\&` | tabular 안 `&` 오염. |
| 빈 `\href{}{}` 제거 | hyperref 오류. |
| `extbf{` → `\textbf{` | 백슬래시 누락 오타. |
| `\begin{center}` 미종료 + 첫 `\section` | `\end{center}` 자동 삽입(Dhruv 헤더 깨짐 방지). |
| 유니코드 치환 + 탭→공백 | pdflatex “invalid character”. |
| `LATEX_PORTABLE_PREAMBLE=1` | 프리앰블에서 `fullpage` / `glyphtounicode` 줄 완화(TinyTeX·웹 경로). |

**건드리면 안 되는 것(주의)**

- `normalize_to_dhruv_template` / `dhruv_preamble.tex` — 템플릿·매크로와 프롬프트 `LATEX_FORMAT_LOCK`이 **한 세트**. 한쪽만 바꾸면 모델 출력과 불일치.
- `compile_latex_to_pdf` 내부 **variant 순서**(`portable_first`) — Docker vs 호스트 TeX 실패 시 재시도 순서.

---

## 5. 연락처 (이메일 / LinkedIn)

| 항목 | 동작 |
|------|------|
| 웹 | 붙여넣기만 할 때: 원문에 이메일·`linkedin.com` 패턴 없으면 **필드 입력 강제**. |
| 파일 업로드 | 클라이언트에서 텍스트 검사 안 함 → 같은 폼 필드로 선택 입력 가능. |
| API | `_append_contact_hints`로 user 메시지에 `USER-SUPPLIED CONTACT` 블록 추가. |

**엣지케이스**

- 이메일이 비표준 형태로만 있으면 휴리스틱이 놓칠 수 있음 → 사용자가 필드에 직접 입력.

---

## 6. PDF 페이지 수

순서: `pdfinfo` → `qpdf` → `pypdf`.  
`/health`에 `pdf_page_counter`, `pdfinfo`, `qpdf` 표시.

---

## 7. 타입 · 응답 필드 (`GenerateResponse`)

프론트 `web/src/lib/types.ts`와 맞출 것:

- `page_policy_applied`, `revision_log`, `revision_log_ko`
- `pdf_layout_underfull`, `density_expand_rounds`

---

## 8. 관련 파일 빠른 색인

```
api/main.py          — 라우트, iterate_generate_progress, 연락처, 설정 동기화
api/prompts.py       — 시스템 프롬프트·템플릿 락
api/compile_pdf.py   — 컴파일, sanitize, 측정, portable preamble
api/OPS_CHECKLIST.md — 운영 체크리스트
api/scripts/measure_pdf_bottom_mean.py — 골든 PDF 밝기 측정
web/src/app/page.tsx
web/src/app/api/generate-stream/route.ts
```

---

## 9. 변경 시 회귀 체크(권장)

1. `GET /health` — `pdf_compile`, `pdf_density_check_ready`, `latex_portable_preamble`  
2. 붙여넣기 생성 → 스트림 `progress` 한글 메시지  
3. strict 1p → 2p 초과 시 트림 로그  
4. 임의 `.tex`에 `\begin{center}`만 있고 `\end{center}` 없을 때 compile-pdf 성공 여부  
5. `npm run build` (web), API는 `uvicorn` 기동 후 스모크

이 문서를 **기능 추가·리팩터 전에** 한 번 읽고, 새 엣지케이스가 생기면 **같은 파일에 짧은 bullet로 추가**하면 됩니다.
