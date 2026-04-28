"""SimpleResume API — FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from resume_service.config import settings
from resume_service.routers import (
    health,
    compile,
    resume,
    coaching,
    resume_score,
    resume_review,
    bullet_chat,
)

app = FastAPI(title="SimpleResume API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(compile.router)
app.include_router(resume.router)
app.include_router(coaching.router)
app.include_router(resume_score.router)
app.include_router(resume_review.router)
if settings.feature_bullet_chat:
    app.include_router(bullet_chat.router)
