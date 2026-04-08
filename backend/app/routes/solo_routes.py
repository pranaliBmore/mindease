from fastapi import APIRouter, Depends

from app.controllers.solo_controller import solo_analyze_controller
from app.middleware.auth_middleware import get_current_user
from app.schemas.solo_schema import SoloAnalyzeRequest, SoloAnalyzeResponse

router = APIRouter(prefix="/api/solo", tags=["solo"])


@router.post("/analyze", response_model=SoloAnalyzeResponse)
async def analyze_solo(payload: SoloAnalyzeRequest, current_user: dict = Depends(get_current_user)):
    return await solo_analyze_controller(current_user, payload)

