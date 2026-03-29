# 운영 체크리스트 (한 페이지 밀도 / underfull)

**이것만 순서대로 확인하면 됩니다.**

1. **Poppler** — 서버에 `pdftoppm` 이 PATH에 있는가?  
   - macOS: `brew install poppler`  
   - 확인: `which pdftoppm`

2. **Pillow** — API venv에 설치되어 있는가?  
   - `pip install -r requirements.txt` (이미 `Pillow` 포함)

3. **`GET /health`** — `compiler.pdf_density_check_ready` 가 **`true`** 인가?  
   - `false`면 밀도 측정·underfull 판정이 동작하지 않음.

4. **`RESUME_DENSITY_EXPAND_MAX`** — **`1` 이상**인가? (기본 `2`)  
   - `0`이면 “한 페이지 꽉 채우기” 자동 보강 루프 자체가 꺼짐.

5. **원문** — 추가로 넣을 **진짜** 불릿·수치·프로젝트가 있는가?  
   - 없으면 결과는 **짧거나 하단 여백이 남을 수 있음** (허위 성과는 넣지 않음).  
   - 생성 후 `revision_log` / `revision_log_ko` 에도 같은 취지가 붙을 수 있음.

## 골든 PDF 기준 (선택)

Overleaf “꽉 찬 1페이지” PDF로 숫자 고정:

```bash
cd api && source .venv/bin/activate
python scripts/measure_pdf_bottom_mean.py /path/to/golden.pdf
```

출력된 `RESUME_UNDERFULL_GOLDEN_MEAN` 등을 `api/.env`에 넣기.
