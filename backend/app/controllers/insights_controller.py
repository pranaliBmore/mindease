from app.services.insights_service import insights_service


async def insights_summary_controller(user: dict, range_: str) -> dict:
    return await insights_service.summary(user, range_)
