"""POST /resume/review, /resume/review-from-text — document-annotation review endpoints."""

import logging

from fastapi import APIRouter, File, HTTPException, UploadFile

from resume_service.models.resume_review import ReviewResponse
from resume_service.models.resume_score import ResumeScoreTextBody
from resume_service.services.pdf_service import extract_text
from resume_service.services.resume_score_service import score_resume
from resume_service.services.resume_score_parser import parse_resume
from resume_service.services.resume_review_service import build_review

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/resume/review", response_model=ReviewResponse)
async def review_resume_upload(file: UploadFile = File(...)):
    """Score and build review for an uploaded resume (PDF/TXT)."""
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

    parsed = parse_resume(text)
    score_result = score_resume(text)
    return build_review(score_result, parsed=parsed)


@router.post("/resume/review-from-text", response_model=ReviewResponse)
def review_resume_text(body: ResumeScoreTextBody):
    """Score and build review from pasted text."""
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Resume text is empty.")

    parsed = parse_resume(body.text)
    score_result = score_resume(body.text, job_description=body.job_description)
    return build_review(score_result, parsed=parsed)
