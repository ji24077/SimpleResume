"""POST /resume/score, /resume/score-from-text — resume scoring endpoints."""

import logging

from fastapi import APIRouter, File, HTTPException, UploadFile

from resume_service.models.resume_score import ResumeScoreResponse, ResumeScoreTextBody
from resume_service.services.pdf_service import extract_text
from resume_service.services.resume_score_service import score_resume

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/resume/score", response_model=ResumeScoreResponse)
async def score_resume_upload(file: UploadFile = File(...)):
    """Score an uploaded resume (PDF/TXT)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        text = extract_text(file.filename, data)
    except Exception:
        logger.exception("Failed to extract text from %s", file.filename)
        raise HTTPException(status_code=422, detail="Could not extract text from the uploaded file.")

    return score_resume(text)


@router.post("/resume/score-from-text", response_model=ResumeScoreResponse)
def score_resume_text(body: ResumeScoreTextBody):
    """Score resume from pasted text."""
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Resume text is empty.")

    return score_resume(body.text, job_description=body.job_description)
