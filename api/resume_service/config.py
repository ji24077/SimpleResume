"""Settings, env loading, and startup diagnostics for SimpleResume API."""

import logging
import os
import shutil
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from compile_pdf import compiler_available

# api/ directory (one level up from resume_service/)
API_DIR = Path(__file__).resolve().parent.parent
load_dotenv(API_DIR / ".env")
if not (os.environ.get("OPENAI_API_KEY") or "").strip():
    load_dotenv(API_DIR.parent / ".env", override=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    latex_docker_image: str = Field(default="simpleresume-texlive:full")
    latex_docker_network: str = "none"
    latex_portable_preamble: bool = Field(default=False)

    resume_one_page_max_revisions: int = Field(default=3, ge=0, le=8)

    resume_density_expand_max: int = Field(default=2, ge=0, le=6)
    resume_underfull_bottom_frac: float = Field(default=0.15, ge=0.08, le=0.45)
    resume_underfull_mean_threshold: float = Field(default=233.0, ge=210.0, le=252.0)
    resume_underfull_dpi: int = Field(default=100, ge=72, le=150)
    resume_underfull_golden_mean: float | None = Field(default=None)
    resume_underfull_golden_margin: float = Field(default=12.0, ge=0.5, le=80.0)

    resume_ats_fix_max: int = Field(default=2, ge=0, le=4)
    resume_quality_checker: bool = Field(default=False)

    resume_structured_latex: bool = Field(default=False)
    resume_schema_heal_max: int = Field(default=2, ge=0, le=8)

    feature_pdf_annotations: bool = Field(default=False)
    feature_advanced_diagnostics: bool = Field(default=False)
    feature_parse_review: bool = Field(default=True)

    model_config = SettingsConfigDict(extra="ignore")

    @field_validator("openai_api_key", mode="before")
    @classmethod
    def strip_api_key(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("latex_docker_image", mode="before")
    @classmethod
    def strip_docker_image(cls, v: Any) -> Any:
        if v is None:
            return ""
        if isinstance(v, str):
            return v.strip()
        return v


settings = Settings()

if settings.latex_docker_image.strip():
    os.environ["LATEX_DOCKER_IMAGE"] = settings.latex_docker_image.strip()
else:
    os.environ.pop("LATEX_DOCKER_IMAGE", None)
if settings.latex_docker_network.strip():
    os.environ["LATEX_DOCKER_NETWORK"] = settings.latex_docker_network.strip()
os.environ.pop("LATEX_DOCKER_ONLY", None)
os.environ.pop("LATEX_DOCKER_ALLOW_FALLBACK", None)
if settings.latex_portable_preamble:
    os.environ["LATEX_PORTABLE_PREAMBLE"] = "1"
else:
    os.environ.pop("LATEX_PORTABLE_PREAMBLE", None)

if not settings.openai_api_key:
    logger.warning(
        "OPENAI_API_KEY is empty. Add it to %s or %s then restart the API.",
        API_DIR / ".env",
        API_DIR.parent / ".env",
    )
else:
    logger.info("OpenAI API key loaded (%d chars). Model: %s", len(settings.openai_api_key), settings.openai_model)

if settings.resume_structured_latex:
    logger.info(
        "RESUME_STRUCTURED_LATEX: model outputs resume_data only; LaTeX is server-rendered "
        "(schema self-heal max=%s).",
        settings.resume_schema_heal_max,
    )

_has_docker_cli = bool(shutil.which("docker"))
logger.info(
    "PDF compile: Docker-only | LATEX_DOCKER_IMAGE=%r | docker CLI=%s | LATEX_DOCKER_NETWORK=%r",
    settings.latex_docker_image or None,
    "yes" if _has_docker_cli else "NO (PDF will fail until Docker is available)",
    settings.latex_docker_network,
)
if settings.latex_docker_image.strip() and not _has_docker_cli:
    logger.warning(
        "LATEX_DOCKER_IMAGE is set but `docker` is not in PATH — PDF compile will fail. "
        "Start Docker Desktop and ensure `docker` is on PATH."
    )

_comp = compiler_available()
if settings.latex_docker_image.strip() and not _comp.get("latex_docker_ready"):
    logger.warning(
        "PDF requires Docker for %s. From repo root: docker compose build texlive — "
        "then start Docker Desktop and restart the API.",
        settings.latex_docker_image,
    )
