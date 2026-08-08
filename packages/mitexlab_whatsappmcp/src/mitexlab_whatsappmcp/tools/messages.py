import asyncio
from typing import Any, List, Literal, Dict, Optional

from ..core.webhookfetcher import query_webhooks
from ..core.api import WhatsAppAPI
from ..core.helper import get_access_token, get_business_account_id
from ..server import server



@server.tool()
async def send_text_message(
    phone_number_id: str, 
    to: str, 
    text: str, 
    preview_url: bool = True,
    context_message_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send a text message to a WhatsApp number.

    Args:
        phone_number_id: Your WhatsApp Business phone number ID
        to: Recipient's phone number (with country code, e.g., +1234567890)
        text: Message text content
        preview_url: Whether to generate URL previews in the message
    """
    try:
        access_token = await get_access_token(phone_number_id=phone_number_id)
        businessaccountid = await get_business_account_id(phone_number_id=phone_number_id)

        async with WhatsAppAPI(
            access_token=access_token, 
            phone_number_id=phone_number_id,
            business_account_id=businessaccountid
        ) as wa_client:

            result = await wa_client.send_text_message(
                to=to, 
                text=text, 
                preview_url=preview_url,
                context_message_id=context_message_id
            )

        return {
            "success": True,
            "message": "Text message sent successfully",
            "data": result,
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"send_text_message error: {str(e)}",
            "data": None,
        }


@server.tool()
async def send_an_interactive_message(
    phone_number_id: str, 
    to: str,
    interactive_type: str,
    body_text: str,
    footer_text: Optional[str] = None,
    header: Optional[Dict[str, Any]] = None,
    action: Optional[Dict[str, Any]] = None,
    context_message_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send an interactive message
    """
    try:
        access_token = await get_access_token(phone_number_id=phone_number_id)
        businessaccountid = await get_business_account_id(phone_number_id=phone_number_id)

        async with WhatsAppAPI(
            access_token=access_token, 
            phone_number_id=phone_number_id,
            business_account_id=businessaccountid
        ) as wa_client:

            result = await wa_client.send_interactive_message(
                to = to,
                interactive_type = interactive_type,
                body_text = body_text,
                footer_text = footer_text,
                header = header,
                action = action,
                context_message_id=context_message_id
            )

        return {
            "success": True,
            "message": "Successfully sent!",
            "data": result,
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"send_an_interactive_message error: {str(e)}",
            "data": None,
        }


@server.tool()
async def send_media_message(
    phone_number_id: str,
    to: str,
    media_type: Literal["image", "document", "audio", "video", "sticker"],
    media_url: str = "",
    caption: Optional[str] = None,
    filename: Optional[str] = None,
    context_message_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send a media message (image, document, audio, video, sticker).

    Args:
        phone_number_id: Your WhatsApp Business phone number ID
        to: Recipient's phone number (with country code)
        media_type: Type of media (image, document, audio, video, sticker)
        media_url: Public URL of the media file
        caption: Caption for the media (for image, video, document)
        filename: Filename for document type
    """
    try:
        
        access_token = await get_access_token(phone_number_id=phone_number_id)
        businessaccountid = await get_business_account_id(phone_number_id=phone_number_id)

        async with WhatsAppAPI(
            access_token=access_token, 
            phone_number_id=phone_number_id,
            business_account_id=businessaccountid
        ) as wa_client:

            result = await wa_client.send_media_message(
                to=to,
                media_type=media_type,
                media_url=media_url,
                caption=caption,
                filename=filename,
                context_message_id=context_message_id
            )

        return {
            "success": True,
            "message": "Successfully sent!",
            "data": result,
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"send_media_message error: {str(e)}",
            "data": None,
        }


@server.tool()
async def mark_message_as_read(
    phone_number_id: str, 
    message_id: str
) -> Dict[str, Any]:
    """
    Mark a message as read.
    """
    try:
        access_token = await get_access_token(phone_number_id=phone_number_id)
        businessaccountid = await get_business_account_id(phone_number_id=phone_number_id)

        async with WhatsAppAPI(
            access_token=access_token, 
            phone_number_id=phone_number_id,
            business_account_id=businessaccountid
        ) as wa_client:

            result = await wa_client.mark_message_as_read(
                message_id=message_id
            )

        return {
            "success": True,
            "message": "action completed",
            "data": result,
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"mark_message_as_read error: {str(e)}",
            "data": None,
        }


@server.tool()
async def fetch_recent_messages_with_jsonoutput(
    phone_number_id: str, 
    systemid: str = "nill",  
    limit: int = 20
):
    try:
        result = await query_webhooks(
            phone_number_id = phone_number_id,
            systemid = systemid,
            limit = limit
        )

        if not result or len(result) == 0:
            return {
                "success": True,
                "message": "No new messages found.",
                "data":[]
            }
        
        return {
            "success": True,
            "message": "Successfully retrieved",
            "data": result
        }
        
    except Exception as e:
        print(f"Error fetching whatsapp messages for phone_number_id {phone_number_id}: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to retrieve recent messages again. {str(e)}"
        }    




# async def quickie():
#     result = await send_text_message(
#         phone_number_id="753830084490207",
#         to="+233548765995",
#         context_message_id="wamid.HBgMMjMzNTQ4NzY1OTk1FQIAEhgUM0FCODMzQ0JERkEzODVDOTZDQzcA",
#         text="Sure! we got it"
#     )
#     print(f"result: {result}")

# if __name__ == "__main__":
#     asyncio.run(quickie())