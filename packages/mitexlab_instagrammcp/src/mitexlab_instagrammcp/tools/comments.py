
import asyncio
from ..core.helper import getaccesstoken, getprofileuserid
from ..core.api import InstagramAPI
from ..server import server


@server.tool()
async def get_media_comments(
    username: str,
    media_id: str,
    fields: str = "id,text,timestamp,username,like_count,replies",
    limit: int = 25,
) -> str:
    """
    Get comments on a specific Instagram media item.
    """
  
    try:
        accesstoken = await getaccesstoken(username=username)
        if not accesstoken:
            raise ValueError("Unable to retrive user access token")

        async with InstagramAPI( access_token=accesstoken) as instagram_api:
            if not instagram_api:
                raise ValueError("Invalid client instantiated")

            result = await instagram_api.get_media_comments(
                media_id=media_id, 
                fields=fields, 
                limit=limit
            )

            if not result or "data" not in result:
                return "No comments found for the media."

            return f"Media Comments ({len(result.get('data', []))} total):\n" + "\n".join(
                [
                    f"Comment ID: {item.get('id')}, Text: {item.get('text')}, "
                    f"Username: {item.get('username')}, Timestamp: {item.get('timestamp')}, "
                    f"Like Count: {item.get('like_count', 0)}, Replies: {item.get('replies', {}).get('data', [])}"
                    for item in result.get("data", [])
                ]
            )
    except Exception as e:
        raise ValueError(f"error: get_media_comments: {str(e)}")



@server.tool()
async def create_comment(
    username: str, 
    media_id: str, 
    message: str
) -> str:
    """
    Comment on an Instagram media item.
    """

    try:
        if len(message) > 2200:
            return "Failed to create comment: Comment message cannot exceed 2200 characters"

        accesstoken = await getaccesstoken(username=username)
        if not accesstoken:
            raise ValueError("Unable to retrive user access token")
        
        async with InstagramAPI( access_token=accesstoken) as instagram_api:
            if not instagram_api:
                raise ValueError("Invalid client instantiated")

            result = await instagram_api.create_comment(media_id, message)

            return (
                f"Comment created successfully!\n"
                f"Comment ID: {result.get('id')}\n"
                f"Message: {message}\n"
                f"Media ID: {media_id}"
            )
    except Exception as e:
        raise ValueError(f"error: create_comment: {str(e)}")



@server.tool()
async def reply_to_comment(
    username: str, 
    comment_id: str, 
    message: str
) -> str:
    """
    Reply to a comment on Instagram.
    """
    
    try:
        if len(message) > 2200:
            return "Failed to reply to comment: Reply message cannot exceed 2200 characters"

        accesstoken = await getaccesstoken(username=username)
        if not accesstoken:
            raise ValueError("Unable to retrive user access token")
        
        async with InstagramAPI( access_token=accesstoken) as instagram_api:
            if not instagram_api:
                raise ValueError("Invalid client instantiated")

            result = await instagram_api.reply_to_comment(comment_id, message)
        
        if not result:
            raise ValueError(f"Failed to reply_to_comment")

        return (
            f"Reply created successfully!\n"
            f"Reply ID: {result.get('id')}\n"
            f"Message: {message}\n"
            f"Original Comment ID: {comment_id}"
        )
    except Exception as e:
        raise ValueError(f"error: reply_to_comment: {str(e)}")
    



# @server.tool()
# async def fetch_all_comments(
#     username: str, 
# ) -> str:
#     """
#     Reply to a comment on Instagram.
#     """
    
#     try:
#         # if len(message) > 2200:
#         #     return "Failed to reply to comment: Reply message cannot exceed 2200 characters"

#         accesstoken = await getaccesstoken(username=username)
#         if not accesstoken:
#             raise ValueError("Unable to retrive user access token")
        
#         async with InstagramAPI( access_token=accesstoken) as instagram_api:
#             if not instagram_api:
#                 raise ValueError("Invalid client instantiated")

#             result = await instagram_api.get_all_user_comments()
        
#         if not result:
#             raise ValueError(f"Failed to reply_to_comment")
        
#         print(f"resultinside:{result}")

#         # return (
#         #     f"Reply created successfully!\n"
#         #     f"Reply ID: {result.get('id')}\n"
#         #     f"Message: {message}\n"
#         #     f"Original Comment ID: {comment_id}"
#         # )
#     except Exception as e:
#         raise ValueError(f"error: reply_to_comment: {str(e)}")
    


# async def quickie():
#     reuslt = await reply_to_comment(
#         username="rankloid_",
#         comment_id="18074014970143080",
#         message="Nice having you"
#         # caption="Img 101",
#         # image_urls=[
#         #     "https://res.cloudinary.com/tribapay/image/upload/v1756330478/Screenshot_2025-08-27_at_22.27.39_picvex.png",
#         #     "https://res.cloudinary.com/tribapay/image/upload/v1756330478/Screenshot_2025-08-27_at_22.27.39_picvex.png"
#         # ]
#     )
#     print(f"reuslt: {reuslt}")

# if __name__ == "__main__":
#     asyncio.run(quickie())


# async def quickie():
#     reuslt = await fetch_all_comments(
#         username="rankloid_",
#         # caption="Img 101",
#         # image_urls=[
#         #     "https://res.cloudinary.com/tribapay/image/upload/v1756330478/Screenshot_2025-08-27_at_22.27.39_picvex.png",
#         #     "https://res.cloudinary.com/tribapay/image/upload/v1756330478/Screenshot_2025-08-27_at_22.27.39_picvex.png"
#         # ]
#     )
#     # print(f"reuslt: {reuslt}")

# if __name__ == "__main__":
#     asyncio.run(quickie())