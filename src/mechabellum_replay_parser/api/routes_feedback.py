import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

_log = logging.getLogger(__name__)
router = APIRouter(prefix="/feedback")

_VALID_LABELS = frozenset({
    "good", "bad_illegal", "bad_strategy", "bad_positioning",
    "bad_counter", "too_expensive", "unclear",
})


class FeedbackBody(BaseModel):
    recommendation_id: str
    rating: int | None = None
    label: str | None = None
    comment: str | None = None
    followed_plan: bool | None = None


@router.post("", status_code=204)
async def submit_feedback(body: FeedbackBody, request: Request) -> None:
    _log.info(
        "stage=feedback_received rec_id=%s rating=%s label=%s",
        body.recommendation_id, body.rating, body.label,
    )
    if body.label is not None and body.label not in _VALID_LABELS:
        raise HTTPException(status_code=422, detail=f"Unknown label: {body.label!r}")
    if body.rating is not None and not (1 <= body.rating <= 5):
        raise HTTPException(status_code=422, detail="Rating must be 1–5")

    persistence = getattr(request.app.state, "persistence", None)
    if persistence is not None:
        try:
            await persistence.save_feedback(
                recommendation_id=body.recommendation_id,
                rating=body.rating,
                label=body.label,
                comment=body.comment,
                followed_plan=body.followed_plan,
            )
        except Exception as exc:
            _log.warning("Persistence error saving feedback (non-fatal): %s", exc)
