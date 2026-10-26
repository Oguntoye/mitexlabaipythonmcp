import asyncio

from ..core.helper import getaccesstoken
from ..core.api import InstagramAPI
from ..server import server


@server.tool()
async def get_user_profile( username: str) -> str:
    """
    Get Instagram user profile information.
    Args:
        username (str)
    Returns:
        str: User profile information including account type and stats
    """

    try:
        accesstoken = await getaccesstoken(username=username)
        if not accesstoken:
            raise ValueError("Unable to retrive user access token")

        async with InstagramAPI( access_token=accesstoken) as instagram_api:
            if not instagram_api:
                raise ValueError("Invalid client instantiated")

            # instagram_api = InstagramAPI(access_token= accesstoken)
            result = await instagram_api.get_user_profile()
        
        if not result or not result.get('username'):
            raise ValueError(f"Failed to get result in user profile")
            
        return (
            f"User Profile:\n"
            f"ID: {result.get('id')}\n"
            f"Username: {result.get('username')}\n"
            f"Name: {result.get('name')}\n"
            f"Account Type: {result.get('account_type')}\n"
            f"Followers: {result.get('followers_count')}\n"
            f"Following: {result.get('follows_count')}\n"
            f"Media Count: {result.get('media_count')}\n"
            f"Profile Picture URL: {result.get('profile_picture_url')}"
        )
    except Exception as e:
        raise ValueError(f"Failed to retrieve user profile: {str(e)}")
        # return f"Failed to retrieve user profile: {str(e)}"



# async def quickie():
#     reuslt = await get_user_profile("example_user")
#     print(f"reuslt: {reuslt}")

# if __name__ == "__main__":
#     asyncio.run(quickie())