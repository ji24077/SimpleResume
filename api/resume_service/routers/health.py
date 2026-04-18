"""GET /health — system readiness check."""

from fastapi import APIRouter

from compile_pdf import compiler_available
from resume_service.config import API_DIR, settings

router = APIRouter()


@router.get("/health")
def health():
    comp = compiler_available()
    return {
        "ok": True,
        "openai_configured": bool(settings.openai_api_key),
        "model": settings.openai_model if settings.openai_api_key else None,
        "resume_structured_latex": settings.resume_structured_latex,
        "resume_schema_heal_max": settings.resume_schema_heal_max,
        "env_hint": str(API_DIR / ".env"),
        "pdf_compile": comp.get("pdf_compile", comp.get("pdflatex") or comp.get("tectonic")),
        "compiler": comp,
    }


@router.get("/health/detailed")
def health_detailed():
    """Placeholder for detailed health check."""
    return {"status": "not_implemented"}
