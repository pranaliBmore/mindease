from fastapi import APIRouter, Depends

from app.controllers.feedback_controller import submit_feedback_controller
from app.middleware.auth_middleware import get_current_user
from app.schemas.feedback_schema import FeedbackRequest, FeedbackResponse

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


@router.post("/submit", response_model=FeedbackResponse)
async def submit_feedback(payload: FeedbackRequest, current_user: dict = Depends(get_current_user)):
    return await submit_feedback_controller(
        current_user,
        flow_type=payload.flow_type,
        content_type=payload.content_type,
        message=payload.message,
        rating=payload.rating,
    )
