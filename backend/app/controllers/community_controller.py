from app.services.community_service import CommunityService

community_service = CommunityService()


async def join_community_controller(user: dict, community_name: str) -> dict:
    return await community_service.join(user=user, community_name=community_name)

async def get_community_controller(community_name: str) -> dict:
    return await community_service.get_details(community_name=community_name)
