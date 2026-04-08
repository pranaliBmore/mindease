from app.services.feedback_service import FeedbackService

feedback_service = FeedbackService()


async def submit_feedback_controller(user: dict, flow_type: str, content_type: str | None, message: str, rating: int) -> dict:
    return await feedback_service.submit(
        user=user, flow_type=flow_type, content_type=content_type, message=message, rating=rating
    )
