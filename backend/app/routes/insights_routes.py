from fastapi import APIRouter, Depends, Query

from app.controllers.insights_controller import insights_summary_controller
from app.middleware.auth_middleware import get_current_user
from app.schemas.insights_schema import InsightsResponse

router = APIRouter(prefix="/api/insights", tags=["insights"])


@router.get("/summary", response_model=InsightsResponse)
async def insights_summary(
    range: str = Query("month", pattern="^(week|month)$"),
    current_user: dict = Depends(get_current_user),
):
    return await insights_summary_controller(current_user, range)
