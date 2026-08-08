import asyncio
from typing import Any, Dict, List, Optional
from ..core.api import WhatsAppAPI
from ..core.helper import get_access_token, get_business_account_id
from ..server import server


@server.tool()
async def create_flow(
    phone_number_id: str,
    name: str,
    category: str = "LEAD_GENERATION",
) -> Dict[str, Any]:
    """
    Create a new WhatsApp Flow.

    Args:
        phone_number_id: Your WhatsApp Business phone number ID
        name: Name of the flow
        category: Flow category (LEAD_GENERATION, SIGN_UP, APPOINTMENT_BOOKING,
                  CONTACT_US, CUSTOMER_SUPPORT, SURVEY, OTHER)
    """
    try:
        access_token = await get_access_token(phone_number_id=phone_number_id)
        business_account_id = await get_business_account_id(phone_number_id=phone_number_id)

        async with WhatsAppAPI(
            access_token=access_token,
            phone_number_id=phone_number_id,
            business_account_id=business_account_id,
        ) as wa_client:
            if not wa_client:
                raise ValueError("Invalid client instantiated")

            result = await wa_client.create_flow(
                name=name,
                categories=[category],
            )

        return {
            "success": True,
            "message": "Flow created successfully!",
            "data": result,  # contains { id: flow_id }
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"create_flow error: {str(e)}",
            "data": None,
        }


@server.tool()
async def upload_flow_json(
    phone_number_id: str,
    flow_id: str,
    flow_json: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Upload or update the screen JSON for an existing flow.
    Can be called multiple times on the same flow_id while it is in DRAFT state.

    Args:
        phone_number_id: Your WhatsApp Business phone number ID
        flow_id: ID of the flow to upload JSON to
        flow_json: The full flow JSON object (version, screens, etc.)
    """
    try:
        access_token = await get_access_token(phone_number_id=phone_number_id)
        business_account_id = await get_business_account_id(phone_number_id=phone_number_id)

        async with WhatsAppAPI(
            access_token=access_token,
            phone_number_id=phone_number_id,
            business_account_id=business_account_id,
        ) as wa_client:
            if not wa_client:
                raise ValueError("Invalid client instantiated")

            result = await wa_client.upload_flow_json(
                flow_id=flow_id,
                flow_json=flow_json,
            )

        return {
            "success": True,
            "message": "Flow JSON uploaded successfully!",
            "data": result,
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"upload_flow_json error: {str(e)}",
            "data": None,
        }


# @server.tool()
# async def get_flow(
#     phone_number_id: str,
#     flow_id: str,
# ) -> Dict[str, Any]:
#     """
#     Get full details of a single flow including status, validation errors,
#     preview URL, and screen JSON.

#     Args:
#         phone_number_id: Your WhatsApp Business phone number ID
#         flow_id: ID of the flow to retrieve
#     """
#     try:
#         access_token = await get_access_token(phone_number_id=phone_number_id)
#         business_account_id = await get_business_account_id(phone_number_id=phone_number_id)

#         async with WhatsAppAPI(
#             access_token=access_token,
#             phone_number_id=phone_number_id,
#             business_account_id=business_account_id,
#         ) as wa_client:
#             if not wa_client:
#                 raise ValueError("Invalid client instantiated")

#             result = await wa_client.get_flow(
#                 flow_id=flow_id,
#                 fields=[
#                     "id",
#                     "name",
#                     "status",
#                     "categories",
#                     "validation_errors",
#                     "json_version",
#                     "data_api_version",
#                     "endpoint_uri",
#                     "preview",
#                     "whatsapp_business_account",
#                     "asset_links"
#                 ],
#             )

#         return {
#             "success": True,
#             "message": "Flow retrieved successfully!",
#             "data": result,
#         }

#     except Exception as e:
#         return {
#             "success": False,
#             "message": f"get_flow error: {str(e)}",
#             "data": None,
#         }


@server.tool()
async def get_flow(
    phone_number_id: str,
    flow_id: str,
) -> Dict[str, Any]:
    try:
        access_token = await get_access_token(phone_number_id=phone_number_id)
        business_account_id = await get_business_account_id(phone_number_id=phone_number_id)

        async with WhatsAppAPI(
            access_token=access_token,
            phone_number_id=phone_number_id,
            business_account_id=business_account_id,
        ) as wa_client:
            if not wa_client:
                raise ValueError("Invalid client instantiated")

            flow_result, assets_result = await asyncio.gather(
                wa_client.get_flow(
                    flow_id=flow_id,
                    fields=[
                        "id", "name", "status", "categories",
                        "validation_errors", "json_version", "data_api_version",
                        "endpoint_uri", "preview", "whatsapp_business_account",
                    ],
                ),
                wa_client.get_flow_assets(flow_id=flow_id),
                return_exceptions=True,
            )

            # Download actual flow JSON if assets call succeeded
            if not isinstance(assets_result, Exception):
                assets_data = assets_result.get("data", [])
                if assets_data:
                    download_url = assets_data[0].get("download_url")
                    if download_url:
                        try:
                            flow_result["flow_json"] = await wa_client.download_flow_json(download_url)
                        except Exception:
                            flow_result["flow_json"] = None

        return {
            "success": True,
            "message": "Flow retrieved successfully!",
            "data": flow_result,
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"get_flow error: {str(e)}",
            "data": None,
        }


@server.tool()
async def list_flows(
    phone_number_id: str,
) -> Dict[str, Any]:
    """
    List all flows for the WhatsApp Business Account.

    Args:
        phone_number_id: Your WhatsApp Business phone number ID
    """
    try:
        access_token = await get_access_token(phone_number_id=phone_number_id)
        business_account_id = await get_business_account_id(phone_number_id=phone_number_id)

        async with WhatsAppAPI(
            access_token=access_token,
            phone_number_id=phone_number_id,
            business_account_id=business_account_id,
        ) as wa_client:
            if not wa_client:
                raise ValueError("Invalid client instantiated")

            result = await wa_client.list_flows(
                fields=["id", "name", "status", "categories"],
            )

        return {
            "success": True,
            "message": "Flows retrieved successfully!",
            "data": result.get("data", []),
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"list_flows error: {str(e)}",
            "data": None,
        }


@server.tool()
async def submit_flow(
    phone_number_id: str,
    flow_id: str,
) -> Dict[str, Any]:
    """
    Submit a DRAFT flow for Meta review.
    After submission the flow status moves to SUBMITTED.
    Once Meta approves it, call publish_flow to make it live.

    Args:
        phone_number_id: Your WhatsApp Business phone number ID
        flow_id: ID of the flow to submit
    """
    try:
        access_token = await get_access_token(phone_number_id=phone_number_id)
        business_account_id = await get_business_account_id(phone_number_id=phone_number_id)

        async with WhatsAppAPI(
            access_token=access_token,
            phone_number_id=phone_number_id,
            business_account_id=business_account_id,
        ) as wa_client:
            if not wa_client:
                raise ValueError("Invalid client instantiated")

            result = await wa_client.submit_flow(flow_id=flow_id)

        return {
            "success": True,
            # "message": "Flow submitted for review!",
            "message": "Flow published successfully!",
            "data": result,
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"submit_flow error: {str(e)}",
            "data": None,
        }


@server.tool()
async def publish_flow(
    phone_number_id: str,
    flow_id: str,
) -> Dict[str, Any]:
    """
    Publish a SUBMITTED (and approved) flow to make it live.
    Once published the flow cannot be edited — deprecate it first to make changes.

    Args:
        phone_number_id: Your WhatsApp Business phone number ID
        flow_id: ID of the flow to publish
    """
    try:
        access_token = await get_access_token(phone_number_id=phone_number_id)
        business_account_id = await get_business_account_id(phone_number_id=phone_number_id)

        async with WhatsAppAPI(
            access_token=access_token,
            phone_number_id=phone_number_id,
            business_account_id=business_account_id,
        ) as wa_client:
            if not wa_client:
                raise ValueError("Invalid client instantiated")

            result = await wa_client.publish_flow(flow_id=flow_id)

        return {
            "success": True,
            "message": "Flow published successfully!",
            "data": result,
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"publish_flow error: {str(e)}",
            "data": None,
        }


@server.tool()
async def deprecate_flow(
    phone_number_id: str,
    flow_id: str,
) -> Dict[str, Any]:
    """
    Deprecate a PUBLISHED flow.
    Required step before you can delete a published flow or replace it with a new one.
    After deprecation the flow status moves to DEPRECATED.

    Args:
        phone_number_id: Your WhatsApp Business phone number ID
        flow_id: ID of the flow to deprecate
    """
    try:
        access_token = await get_access_token(phone_number_id=phone_number_id)
        business_account_id = await get_business_account_id(phone_number_id=phone_number_id)

        async with WhatsAppAPI(
            access_token=access_token,
            phone_number_id=phone_number_id,
            business_account_id=business_account_id,
        ) as wa_client:
            if not wa_client:
                raise ValueError("Invalid client instantiated")

            result = await wa_client.deprecate_flow(flow_id=flow_id)

        return {
            "success": True,
            "message": "Flow deprecated successfully!",
            "data": result,
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"deprecate_flow error: {str(e)}",
            "data": None,
        }


@server.tool()
async def delete_flow(
    phone_number_id: str,
    flow_id: str,
) -> Dict[str, Any]:
    """
    Delete a flow. Flow must be in DRAFT or DEPRECATED state.
    To delete a PUBLISHED flow: call deprecate_flow first, then delete_flow.

    Args:
        phone_number_id: Your WhatsApp Business phone number ID
        flow_id: ID of the flow to delete
    """
    try:
        access_token = await get_access_token(phone_number_id=phone_number_id)
        business_account_id = await get_business_account_id(phone_number_id=phone_number_id)

        async with WhatsAppAPI(
            access_token=access_token,
            phone_number_id=phone_number_id,
            business_account_id=business_account_id,
        ) as wa_client:
            if not wa_client:
                raise ValueError("Invalid client instantiated")

            # Guard: check status before attempting delete
            flow_details = await wa_client.get_flow(
                flow_id=flow_id,
                fields=["id", "status"],
            )
            flow_status = flow_details.get("status", "")

            if flow_status == "PUBLISHED":
                return {
                    "success": False,
                    "message": "Cannot delete a PUBLISHED flow. Call deprecate_flow first, then delete.",
                    "data": None,
                }

            result = await wa_client.delete_flow(flow_id=flow_id)

        return {
            "success": True,
            "message": "Flow deleted successfully!",
            "data": result,
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"delete_flow error: {str(e)}",
            "data": None,
        }
    


@server.tool()
async def deprecate_and_delete_flow(
    phone_number_id: str,
    flow_id: str,
) -> Dict[str, Any]:
    """
    Deprecate and delete a flow in one operation.
    Works on any flow status — DRAFT flows are deleted directly,
    PUBLISHED flows are deprecated first then deleted.

    Args:
        phone_number_id: Your WhatsApp Business phone number ID
        flow_id: ID of the flow to deprecate and delete
    """
    try:
        access_token = await get_access_token(phone_number_id=phone_number_id)
        business_account_id = await get_business_account_id(phone_number_id=phone_number_id)

        async with WhatsAppAPI(
            access_token=access_token,
            phone_number_id=phone_number_id,
            business_account_id=business_account_id,
        ) as wa_client:
            if not wa_client:
                raise ValueError("Invalid client instantiated")

            # Check current status
            flow_details = await wa_client.get_flow(
                flow_id=flow_id,
                fields=["id", "status"],
            )
            flow_status = flow_details.get("status", "")

            # Deprecate first if published
            if flow_status == "PUBLISHED":
                await wa_client.deprecate_flow(flow_id=flow_id)

            # Now delete
            await wa_client.delete_flow(flow_id=flow_id)

        return {
            "success": True,
            "message": f"Flow {'deprecated and ' if flow_status == 'PUBLISHED' else ''}deleted successfully!",
            "data": {"flow_id": flow_id, "previous_status": flow_status},
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"deprecate_and_delete_flow error: {str(e)}",
            "data": None,
        }