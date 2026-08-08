import asyncio
from typing import Any, Dict, Optional
from ..core.api import WhatsAppAPI
from ..core.helper import get_access_token, get_business_account_id
from ..server import server


@server.tool()
async def get_business_profile_details(
    phone_number_id: str
) -> Dict[str, Any]:
    """
    Get detailed business profile information.
    """
    try:
        
        access_token = await get_access_token(phone_number_id=phone_number_id)
        businessaccountid = await get_business_account_id(phone_number_id=phone_number_id)

        async with WhatsAppAPI(
            access_token=access_token, 
            phone_number_id=phone_number_id,
            business_account_id=businessaccountid
        ) as wa_client:
            result = await wa_client.get_business_profile(
                phone_number_id=phone_number_id
            )

        return {
            "success": True,
            "message": "Successfully retrieved!",
            "data": result,
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"get_business_profile_detailed error: {str(e)}",
            "data": None,
        }


@server.tool()
async def update_business_profile_details(
    phone_number_id: str,
    about: Optional[str] = None,
    address:Optional[str] = None,
    description: Optional[str] = None,
    email: Optional[str] = None,
    websites: Optional[str] = None,
    vertical: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Update business profile with detailed information.

    Args:
        phone_number_id: Your WhatsApp Business phone number ID
        about: Short description about the business
        address: Business address
        description: Detailed business description
        email: Business email address
        websites: Comma-separated list of website URLs
        vertical: Business category/vertical
    """
    try:
        access_token = await get_access_token(phone_number_id=phone_number_id)
        businessaccountid = await get_business_account_id(phone_number_id=phone_number_id)

        # Parse websites
        websites_list = (
            [w.strip() for w in websites.split(",") if w.strip()] if websites else []
        )
        
        async with WhatsAppAPI(
            access_token=access_token, 
            phone_number_id=phone_number_id,
            business_account_id=businessaccountid
        ) as wa_client:

            result = await wa_client.update_business_profile(
                about=about,
                address=address,
                description=description,
                email=email,
                websites=websites_list,
                vertical=vertical,
            )

        return {
            "success": True,
            "message": "Successfully updated!",
            "data": result,
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"update_business_profile_detailed error: {str(e)}",
            "data": None,
        }
    

# async def quickie():
#     result = await get_business_profile_details(
#         phone_number_id="753830084490207",
#     )
#     print(f"result: {result}")
#     # result = await update_business_profile_details(
#     #     phone_number_id="753830084490207",
#     #     description='We provide great excellent customer service 24/7'
#     # )
#     # print(f"result: {result}")
# if __name__ == "__main__":
#     asyncio.run(quickie())