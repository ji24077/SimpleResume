"""POST /coaching/analyze — coaching endpoint (placeholder)."""

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.post("/coaching/analyze")
def coaching_analyze():
    """Placeholder for standalone coaching analysis endpoint."""
    raise HTTPException(status_code=501, detail="Not implemented yet")
