# AI-Safe Development Governance (SimpleResume)

AI/인간 공통으로 **기존 동작을 깨지 않고** 기능을 추가하기 위한 규칙입니다.

## 브랜치

| 브랜치 | 용도 |
|--------|------|
| `main` | 프로덕션 안정 |
| `dev` | (선택) 통합 브랜치 |
| `feature/*` | 새 기능 전용 — **기능당 브랜치 1개, PR 1개 권장** |

팀 표준 브랜치 이름·역할(PDF / 1·2차 생성 / 오류 복구 등): **[`docs/FEATURE_BRANCHES.md`](./FEATURE_BRANCHES.md)**.

### PDF 렌더링 + LaTeX 생성기 (현실적인 정리)

Docker TeX 컴파일과 LLM LaTeX 생성은 **구현상 같은 경로(`api/features/pdf_rendering/`, `api/features/generation/`)를 많이 공유**합니다. **완전히 다른 브랜치로만** 쪼개기 어려울 수 있으므로:

- **같은 브랜치/PR에 묶일 수 있음**을 허용하되,
- PR/커밋 설명에서 **“PDF 파이프” vs “프롬프트/생성 로직”** 을 구분해 적고,
- 가능하면 **기능 플래그**로 켜고 끌 수 있게 설계합니다.

## 보호된 경로 (Core)

아래 파일은 **의도적인 유지보수**가 아닌 한 변경을 최소화합니다.  
PR이 이 목록을 건드리면 [Core protection](../.github/workflows/core-protection.yml) 워크플로가 실패합니다.  
**예외:** PR에 라벨 `allow-core-change` 가 있으면 해당 검사를 건너뜁니다 (메인테이너 전용).

목록 원본: [`.github/core-protected-paths.txt`](../.github/core-protected-paths.txt)

현재 포함 예시:

- `api/features/pdf_rendering/compile_pdf.py` — Docker/latexmk·sanitize·컴파일 루프
- `api/features/pdf_rendering/dhruv_preamble.tex` — Dhruv 템플릿 본문

팀 합의로 `.github/core-protected-paths.txt` 에 줄을 **추가**해 범위를 넓힐 수 있습니다. (삭제는 신중히.)

## 확장 아키텍처

새 기능은 가급적 **`extensions/`** 아래에 격리합니다.

- **Core / 보호 경로**는 `extensions` 에 **의존하지 않음**.
- **Extensions** 는 기존 API·compile·유틸을 **import 해서** 동작.
- 의존 방향: `extensions → (기존 모듈)` 만 허용. 역방향 금지.

자세한 안내: [`extensions/README.md`](../extensions/README.md).

## 기능 플래그

새 기능은 **기본값 `false`** 인 환경 변수 플래그 뒤에 둡니다. 예:

- `FEATURE_PDF_ANNOTATIONS=false`
- `FEATURE_ADVANCED_DIAGNOSTICS=false`

`api/.env` / `api/.env.example` 참고. 플래그만 끄면 롤백 가능해야 합니다.

## API 계약

기존 JSON 응답의 **필드 이름·타입 변경·삭제**는 피하고, **선택(optional) 필드 추가**만 허용합니다.  
참고 스키마 초안: [`schemas/generate_response_v1.json`](../schemas/generate_response_v1.json) (확장 시 버전 전략 합의).

## AI 요청 시 권장 프롬프트 헤더

```
------------------------------------------------------------
DO NOT MODIFY existing core logic (see .github/core-protected-paths.txt).
DO NOT refactor unrelated files.
DO NOT change public API contracts except additive optional fields.
Only ADD new files or optional fields. Preserve backward compatibility.
------------------------------------------------------------
```

Core 변경이 필요하면 **코드를 바로 고치지 말고** 설계/이슈로 제안합니다.

## Golden / 회귀

`tests/golden/` 에 샘플 입력을 두고, 허용된 범위 안에서 점수·스냅샷을 고정하는 방식을 권장합니다.  
현재는 [README](../tests/golden/README.md) 만 두고, 데이터는 팀이 단계적으로 채웁니다.

## PR

- 가능하면 **500줄 미만** diff.
- 체크리스트: [`.github/pull_request_template.md`](../.github/pull_request_template.md)

## 모니터링

플래그를 켠 사용자/트래픽에 대해 실패율·지연 증가를 보며, 이상 시 **플래그 off** 로 즉시 롤백합니다.

---

**원칙:** Core는 불가피할 때만 바꾸고, 새 기능은 **additive + 플래그 + extensions** 로 격리한다.
