import asyncio
from typing import Any, List, Literal, Dict, Optional
from ..core.api import WhatsAppAPI
from ..core.helper import get_access_token, get_business_account_id
from ..server import server


@server.tool()
async def create_message_template(
    phone_number_id: str,
    template_name: str,
    category: str,
    components: List[Dict[str, Any]],
    allow_category_change: bool = True,
    language: str = "en_US",
) -> Dict[str, Any]:
    """
    Create a new text-based message template.

    Args:
        phone_number_id: Your WhatsApp Business phone number ID
        template_name: Unique name for the template (lowercase, underscores only)
        category: Template category (MARKETING, UTILITY)
        components: List of components to be included in template
        allow_category_change: Allow WhatsApp to change category if needed
        language: Language code (e.g., en_US, es_ES)
    """
    try:
        
        access_token = await get_access_token(phone_number_id=phone_number_id)
        businessaccountid = await get_business_account_id(phone_number_id=phone_number_id)

        async with WhatsAppAPI(
            access_token=access_token, 
            phone_number_id=phone_number_id,
            business_account_id=businessaccountid
        ) as wa_client:
            if not wa_client:
                raise ValueError("Invalid client instantiated")
            
            ###quickly check if that name aleady exists!
            searchtemplateresult = await wa_client.get_filtered_message_templates(
                templatename=template_name
            )

            searchtemplateresultdata = searchtemplateresult.get('data', [])
            
            obj_template_found = None
            for each_template in searchtemplateresultdata:
                template_name_in_loop = each_template.get('name', '')
                if template_name_in_loop == template_name:
                    obj_template_found = each_template
                    break
            
            # print(f"obj_template_found: {obj_template_found}")
            if obj_template_found:
                return {
                    "success": False,
                    "message": "Template name already exists! Please use a different name",
                    "data": None,
                }

            result = await wa_client.create_message_template(
                name=template_name,
                language=language,
                category=category,
                components=components,
                allow_category_change=allow_category_change,
            )

        return {
            "success": True,
            "message": "Template created successfully!",
            "data": result
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Unable to create template: {str(e)}",
            "data": None,
        }


@server.tool()
async def get_message_template(
    phone_number_id: str,
    template_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new text-based message template.

    Args:
        phone_number_id: Your WhatsApp Business phone number ID
        template_name: Unique name for the template (lowercase, underscores only)
    """
    try:
        
        access_token = await get_access_token(phone_number_id=phone_number_id)
        businessaccountid = await get_business_account_id(phone_number_id=phone_number_id)

        async with WhatsAppAPI(
            access_token=access_token, 
            phone_number_id=phone_number_id,
            business_account_id=businessaccountid
        ) as wa_client:
            if not wa_client:
                raise ValueError("Invalid client instantiated")
            
            searchtemplateresult = await wa_client.get_filtered_message_templates(
                templatename=template_name
            )
            searchtemplateresultdata = searchtemplateresult.get('data', [])

        return {
            "success": True,
            "message": "Successfully retrieved!",
            "data": searchtemplateresultdata
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Unable to get_message_template: {str(e)}",
            "data": None,
        }


@server.tool()
async def send_a_template_message(
    phone_number_id: str, 
    to: str,
    template_name: str,
    components: List[Dict[str, Any]],
    language_code: str = "en_US",
    context_message_id: Optional[str] = None,
    biz_opaque_callback_data: Optional[str] = None,  
) -> Dict[str, Any]:
    """
    Send a template message to a WhatsApp number.
    """
    try:
        access_token = await get_access_token(phone_number_id=phone_number_id)
        businessaccountid = await get_business_account_id(phone_number_id=phone_number_id)

        async with WhatsAppAPI(
            access_token=access_token, 
            phone_number_id=phone_number_id,
            business_account_id=businessaccountid
        ) as wa_client:

            result = await wa_client.send_template_message(
                to=to, 
                template_name=template_name, 
                components=components,
                language_code=language_code,
                context_message_id=context_message_id,
                biz_opaque_callback_data=biz_opaque_callback_data, 
            )

        return {
            "success": True,
            "message": "Successfully sent!",
            "data": result,
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"send_a_template_message error: {str(e)}",
            "data": None,
        }


@server.tool()
async def delete_template(
    phone_number_id: str, 
    template_name: str, 
    hsm_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Delete a message template.

    Args:
        phone_number_id: Your WhatsApp Business phone number ID
        template_name: Name of the template to delete
        hsm_id: HSM ID of the template (optional, for specific template versions)
    """
    try:
        access_token = await get_access_token(phone_number_id=phone_number_id)
        businessaccountid = await get_business_account_id(phone_number_id=phone_number_id)

        async with WhatsAppAPI(
            access_token=access_token, 
            phone_number_id=phone_number_id,
            business_account_id=businessaccountid
        ) as wa_client:
            

            result = await wa_client.delete_message_template(
                template_name=template_name, hsm_id=hsm_id
            )

        return {
            "success": True,
            "message": "Successfully deleted!",
            "data": result,
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"delete_template error: {str(e)}",
            "data": None,
        }



