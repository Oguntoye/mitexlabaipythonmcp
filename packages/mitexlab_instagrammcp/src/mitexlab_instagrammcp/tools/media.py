import asyncio
from typing import Any, Dict, List, Optional

from ..core.helper import getaccesstoken, getprofileuserid
from ..core.api import InstagramAPI
from ..server import server


@server.tool()
async def publish_single_photo(
    username: str,
    image_url: str,
    caption: Optional[str] = None
) -> Dict[str, Any]:
    """
    Publish a single photo post to Instagram.
    Args:
        username (str): 
        image_url (str): URL of the image to upload (must be publicly accessible)
        caption (Optional[str]): Caption for the post
    Returns:
        str: Published post information
    """
   
    try:
        accesstoken = await getaccesstoken(username=username)

        async with InstagramAPI( access_token=accesstoken) as instagram_api:
            if not instagram_api:
                raise ValueError("Invalid client instantiated")
            
            # instagram_api = InstagramAPI(access_token= accesstoken)
            container_result = await instagram_api.create_media_container(
                image_url=image_url,
                caption=caption
            )
            print(f"container_result: {container_result}")

            creation_id = container_result.get("id")
            if not creation_id:
                raise ValueError("Failed to create media container")
            
            publish_result = await instagram_api.publish_media(
                creation_id = creation_id
            )
            print(f"publish_result: {publish_result}")
        
        return publish_result
        # return (
        #     f"Photo post published successfully!\n"
        #     f"Post ID: {publish_result.get('id')}\n"
        #     f"Media Type: {publish_result.get('media_type')}\n"
        #     f"Media URL: {publish_result.get('media_url')}\n"
        #     f"Caption: {publish_result.get('caption')}\n"
        #     f"Permalink: {publish_result.get('permalink')}\n"
        #     f"Timestamp: {publish_result.get('timestamp')}"
        # )
    except Exception as e:
        raise ValueError(f"Failed to publish_single_photo: {str(e)}")
        # return f"Failed to publish_single_photo: {str(e)}"


@server.tool()
async def get_user_media(
    username: str,
    limit: int = 25,
    before: str | None = None,
    after: str | None = None,
) -> Dict[str, Any]:
    """
    Get user media.
    """
   
    try:
        accesstoken = await getaccesstoken(username=username)
        
        async with InstagramAPI( access_token=accesstoken) as instagram_api:
            if not instagram_api:
                raise ValueError("Invalid client instantiated")

            result = await instagram_api.get_user_media(
               limit = limit,
               before=before,
               after=after
            )
        if not result:
            raise ValueError(f"Failed to get_user_media")
        
        return result
    
    except Exception as e:
        raise ValueError(f"Failed to get_user_media: {str(e)}")


@server.tool()
async def publish_story(
    username: str,
    image_url: str,
) -> Dict[str, Any]:
    """
    Publish an Instagram Story.

    Args:

        username (str): Instagram professional account ID
        image_url (str): URL of the image for story (must be publicly accessible)

    Returns:
        Published story information
    """
    try:
        accesstoken = await getaccesstoken(username=username)

        async with InstagramAPI( access_token=accesstoken) as instagram_api:
            if not instagram_api:
                raise ValueError("Invalid client instantiated")

            # Create story container
            container_result = await instagram_api.create_story_container(
                image_url=image_url
            )

            creation_id = container_result.get("id")
            if not creation_id:
                raise ValueError("Failed to publish_story")

            publish_result = await instagram_api.publish_media(
                creation_id=creation_id
            )

        return publish_result
    except Exception as e:
        raise ValueError(f"error: publish_story: {str(e)}")


@server.tool()
async def publish_carousel(
    username: str,
    image_urls: List[str],
    caption: Optional[str] = None,
    location_id: Optional[str] = None,
) :
    """
    Publish a carousel post with multiple images to Instagram.
    """
    
    try:
        if len(image_urls) < 2 or len(image_urls) > 10:
            return ("Failed to publish carousel: Carousel must have between 2 and 10 images")

        accesstoken = await getaccesstoken(username=username)

        async with InstagramAPI( access_token=accesstoken) as instagram_api:
            if not instagram_api:
                raise ValueError("Invalid client instantiated")
        

            # Create individual media containers for each image
            children_ids = []
            for image_url in image_urls:
                container_result = await instagram_api.create_media_container(
                    image_url=image_url
                )
                children_ids.append(container_result.get("id"))

            # Create carousel container
            carousel_container = await instagram_api.create_carousel_container(
                children_ids = children_ids,
                caption=caption,
                location_id=location_id 
            )

            creation_id = carousel_container.get("id")
            if not creation_id:
                raise ValueError("Failed to create carousel container")

            # Publish the carousel
            publish_result = await instagram_api.publish_media(
                creation_id=creation_id
            )

            return publish_result
    except Exception as e:
        raise ValueError(f"error: publish_carousel: {str(e)}")


@server.tool()
async def publish_video(
    username: str,
    video_url: str,
    caption: Optional[str] = None,
    location_id: Optional[str] = None,
    thumbnail_url: Optional[str] = None,
) -> str:
    """
    Publish a video post to Instagram.
    """
   
    try:
        accesstoken = await getaccesstoken(username=username)
        if not accesstoken:
            raise ValueError("Unable to retrive user access token")

        async with InstagramAPI( access_token=accesstoken) as instagram_api:
            if not instagram_api:
                raise ValueError("Invalid client instantiated")
        
            container_result = await instagram_api.create_video_container(
                video_url=video_url,
                caption=caption,
                location_id=location_id,
                thumbnail_url=thumbnail_url,
            )

            creation_id = container_result.get("id")
            if not creation_id:
                raise ValueError("Failed to create video container")

            publish_result = await instagram_api.publish_media(
                creation_id=creation_id
            )
        if not publish_result:
            raise ValueError(f"Failed to publish_video")

        return publish_result
    except Exception as e:
        raise ValueError(f"error: publish_video: {str(e)}")


@server.tool()
async def publish_reel(
    username: str,
    video_url: str,
    caption: Optional[str] = None,
    location_id: Optional[str] = None,
    share_to_feed: bool = True,
) -> str:
    """
    Publish a Reel to Instagram.
    """

    try:
        accesstoken = await getaccesstoken(username=username)
        if not accesstoken:
            raise ValueError("Unable to retrive user access token")
        
        async with InstagramAPI( access_token=accesstoken) as instagram_api:
            if not instagram_api:
                raise ValueError("Invalid client instantiated")

            container_result = await instagram_api.create_reels_container(
                video_url=video_url,
                caption=caption,
                location_id=location_id,
                share_to_feed=share_to_feed,
            )

            creation_id = container_result.get("id")
            if not creation_id:
                raise ValueError("Failed to create Reel container")

            publish_result = await instagram_api.publish_media(
                creation_id=creation_id,
            )

        if not publish_result:
            raise ValueError(f"Failed to publish_reel")

        return publish_result
    except Exception as e:
        raise ValueError(f"error: publish_video: {str(e)}")




# async def quickie():
#     reuslt = await publish_carousel(
#         username="rankloid_",
#         # caption="Img 101",
#         image_urls=[
#             "https://res.cloudinary.com/tribapay/image/upload/v1756330478/Screenshot_2025-08-27_at_22.27.39_picvex.png",
#             "https://res.cloudinary.com/tribapay/image/upload/v1756330478/Screenshot_2025-08-27_at_22.27.39_picvex.png"
#         ]
#     )
#     print(f"reusltdd: {reuslt}")

# if __name__ == "__main__":
#     asyncio.run(quickie())