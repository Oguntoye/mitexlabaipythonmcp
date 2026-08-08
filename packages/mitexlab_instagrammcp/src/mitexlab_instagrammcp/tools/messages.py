import asyncio
from typing import Literal, Optional

from ..core.helper import getaccesstoken, getprofileuserid
from ..core.api import InstagramAPI
from ..server import server
from ..core.webhookfetcher import query_webhooks

# User have dm business before
@server.tool()
async def send_text_directmessage(
    username: str,
    recipient_id: str,
    text: str,
) -> str:
    """Send text as a direct message to a user via their IGSID."""
    try:
        accesstoken = await getaccesstoken(username=username)
        if not accesstoken:
            raise ValueError("Unable to retrieve user access token")
        async with InstagramAPI(access_token=accesstoken) as instagram_api:
            result = await instagram_api.send_text_directmessage(recipient_id=recipient_id, text=text)
        return (
            f"message successfully sent!\n"
            f"Recipient ID: {result.get('recipient_id')}\n"
            f"Message ID: {result.get('message_id')}\n"
        )
    except Exception as e:
        raise ValueError(f"error-send_text_directmessage: {str(e)}")

@server.tool()
async def send_media_directmessage(
    username: str,
    recipient_id: str,
    media_type: Literal['image', 'audio', 'video'],
    url: str,
) -> str:
    """Send media file (image, audio, video) as a direct message to a user."""
    try:
        accesstoken = await getaccesstoken(username=username)
        if not accesstoken:
            raise ValueError("Unable to retrieve user access token")
        async with InstagramAPI(access_token=accesstoken) as instagram_api:
            result = await instagram_api.send_media_directmessage(
                recipient_id=recipient_id,
                media_type=media_type,
                url=url,
            )
        return (
            f"message successfully sent!\n"
            f"Recipient ID: {result.get('recipient_id')}\n"
            f"Message ID: {result.get('message_id')}\n"
        )
    except Exception as e:
        raise ValueError(f"error-send_media_directmessage: {str(e)}")


@server.tool()
async def send_button_template(
    username: str,
    recipient_id: str,
    text: str,
    buttons: list[dict],
) -> str:
    """
    Send a button template DM to a commenter using their IGSID (fromuserid from webhook).
    A comment on your post opens the 24hr window — use this immediately after a comment webhook.
    Max 3 buttons.
    Example buttons: [{"type": "postback", "title": "Send me the link 🔗", "payload": "OPEN_DM"}]
    """
    try:
        accesstoken = await getaccesstoken(username=username)
        if not accesstoken:
            raise ValueError("Unable to retrieve user access token")
        async with InstagramAPI(access_token=accesstoken) as instagram_api:
            result = await instagram_api.send_button_template(
                recipient_id=recipient_id,
                text=text,
                buttons=buttons,
            )
        return (
            f"Button DM sent!\n"
            f"Recipient ID: {result.get('recipient_id')}\n"
            f"Message ID: {result.get('message_id')}\n"
        )
    except Exception as e:
        raise ValueError(f"error-send_button_template: {str(e)}")


# ##from comment >>  user may have never dm business before
@server.tool()
async def send_private_reply(
    username: str,
    comment_id: str,
    text: str,
) -> str:
    """
    Send a plain text private reply to a commenter via comment_id.
    Only one private reply allowed per comment.
    """
    try:
        accesstoken = await getaccesstoken(username=username)
        if not accesstoken:
            raise ValueError("Unable to retrieve user access token")
        async with InstagramAPI(access_token=accesstoken) as instagram_api:
            result = await instagram_api.send_private_reply(comment_id=comment_id, text=text)
        return (
            f"message successfully sent!\n"
            f"Recipient ID: {result.get('recipient_id')}\n"
            f"Message ID: {result.get('message_id')}\n"
        )
    except Exception as e:
        raise ValueError(f"error-send_private_reply: {str(e)}")


@server.tool()
async def send_private_reply_with_buttons(
    username: str,
    comment_id: str,
    text: str,
    buttons: list[dict],
) -> str:
    """
    Send a button template as a private reply to a commenter via comment_id.
    Only one private reply allowed per comment. Max 3 buttons.
    When user taps a button, the 24hr messaging window opens — you can then send follow-up DMs.
    Example buttons:
      [{"type": "postback", "title": "Send me the link 🔗", "payload": "SEND_LINK"}]
      [{"type": "web_url", "title": "Open Website", "url": "https://yoursite.com"}]
    """
    try:
        accesstoken = await getaccesstoken(username=username)
        if not accesstoken:
            raise ValueError("Unable to retrieve user access token")
        async with InstagramAPI(access_token=accesstoken) as instagram_api:
            result = await instagram_api.send_private_reply_with_buttons(
                comment_id=comment_id,
                text=text,
                buttons=buttons,
            )
        return (
            f"Private reply with buttons sent!\n"
            f"Recipient ID: {result.get('recipient_id')}\n"
            f"Message ID: {result.get('message_id')}\n"
        )
    except Exception as e:
        raise ValueError(f"error-send_private_reply_with_buttons: {str(e)}")


# @server.tool()
# async def fetch_recent_messages_and_comments_jsonoutput(
#     username: str,
#     systemid: str = "nill",
#     type_filter: Optional[Literal['dm', 'comment', '']] = None,
#     mediaids: Optional[list[str]] = None,
#     limit: int = 20,
# ):
#     try:
#         result = await query_webhooks(
#             username=username,
#             systemid=systemid,
#             type_filter=type_filter if type_filter else None,
#             mediaids=mediaids,
#             limit=limit,
#         )
#         if not result or len(result) == 0:
#             return {"success": True, "message": "No new messages or comments found.", "data": []}
#         return {"success": True, "message": "Successfully retrieved", "data": result}
#     except Exception as e:
#         print(f"Error fetching ig messages/comment for user {username}: {str(e)}")
#         return {"success": False, "message": f"Failed to retrieve recent messages/comments. {str(e)}"}