from app.schemas.solo_schema import SoloAnalyzeRequest
from app.services.solo_service import solo_service


async def solo_analyze_controller(user: dict, payload: SoloAnalyzeRequest) -> dict:
    return await solo_service.analyze(user=user, text=payload.text, session_id=payload.session_id)

