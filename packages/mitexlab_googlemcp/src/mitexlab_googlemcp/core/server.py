import json
from typing import Any, Dict, List, Literal, Optional, TypedDict
# from mcp.server.fastmcp import FastMCP
from fastmcp import FastMCP
from starlette.requests import Request
from fastapi import Header
from fastapi.responses import HTMLResponse
from ..env import settings
from ..auth.oauth_responses import create_error_response, create_success_response, create_server_error_response
from ..auth.google_auth import handle_auth_callback, start_auth_flow
import importlib



server = FastMCP("google_workspace")


@server.custom_route("/oauth2callback", methods=["GET"])
async def oauth2_callback(request: Request) -> HTMLResponse:
    """
    Handle OAuth2 callback from Google via a custom route.
    This endpoint exchanges the authorization code for credentials and saves them.
    It then displays a success or error page to the user.
    """
    state = request.query_params.get("state")
    code = request.query_params.get("code")
    error = request.query_params.get("error")

    print(f"\n\nstate: {state}\n")
    print(f"\n\ncode: {code}\n")
    print(f"\n\nerror: {error}\n")

    if error:
        error_message = f"Authentication failed: Google returned an error: {error}. State: {state}."
        print(error_message)
        return create_error_response(error_message)

    if not code:
        error_message = "Authentication failed: No authorization code received from Google."
        print(error_message)
        return create_error_response(error_message)

    try:
        print(f"OAuth callback: Received code (state: {state}). Attempting to exchange for tokens.")
        
        # Exchange code for credentials. handle_auth_callback will save them.
        # The user_id returned here is the Google-verified email.
        verified_user_id, credentials = handle_auth_callback(
            authorization_response=str(request.url)
        )

        print(f"OAuth callback: Successfully authenticated user: {verified_user_id} - state: {state}")

        # Return success page using shared template
        return create_success_response(verified_user_id)

    except Exception as e:
        print(f"\n\n: errorlogging at server.py")
        error_message_detail = f"Error processing OAuth callback (state: {state}): {str(e)}"
        print(error_message_detail)
        # Generic error page for any other issues during token exchange or credential saving
        return create_server_error_response(str(e))



class OAuth2Response(TypedDict):
    success: bool
    message: str
    data: Optional[dict[str, Any]]


@server.tool()
async def oauth2_fnx_callback(
    state: str,
    url: str,
    code: str,
) -> OAuth2Response:
    
    if not code:
        return OAuth2Response( 
            success=False, 
            message="Authentication failed: No authorization code received from Google.", 
            data=None
        )
    
    try:
        verified_user_id, credentials, credentials_dict = handle_auth_callback(authorization_response=str(url))
        
        return OAuth2Response(
            success=True,
            message="Authentication successful",
            data={
                "user_id": verified_user_id, #emailaddress that is verified
                "credentials_dict": credentials_dict, #{}
                "state": state #
            }
        )
    except Exception as e:
        return OAuth2Response(
            success=False,
            message=f"Error processing OAuth callback: {str(e)}",
            data={"state": state}
        )

@server.tool()
async def start_google_auth(
    session_id: str,
    user_google_email: str,
    service_name: str,  # e.g., "Google Calendar", "Gmail" for user messages
    redirect_uri: str,  # Added redirect_uri as a required parameter
    scopes: List[str],
    client_id: str, # Made mandatory
    client_secret: str, # Made mandatory
    mode: Literal['forlogin', 'permissionrequest']
) -> str:
    """
    Initiates the Google OAuth 2.0 authentication flow for the specified user email and service.
    This is the primary method to establish credentials when no valid session exists or when targeting a specific account for a particular service.
    It generates an authorization URL that the LLM must present to the user.
    The authentication attempt is linked to the current MCP session via `session_id`.

    LLM Guidance:
    - Use this tool when you need to authenticate a user for a specific Google service (e.g., "Google Calendar", "Google Docs", "Gmail", "Google Drive")
      and don't have existing valid credentials for the session or specified email.
    - You MUST provide the `user_google_email` and the `service_name`. If you don't know the email, ask the user first.
    - Valid `service_name` values typically include "Google Calendar", "Google Docs", "Gmail", "Google Drive".
    - After calling this tool, present the returned authorization URL clearly to the user and instruct them to:
        1. Click the link and complete the sign-in/consent process in their browser.
        2. Note the authenticated email displayed on the success page.
        3. Provide that email back to you (the LLM).
        4. Retry their original request, including the confirmed `user_google_email`.

    Args:
        user_google_email (str): The user's full Google email address (e.g., 'example@gmail.com'). This is REQUIRED.
        service_name (str): The name of the Google service for which authentication is being requested (e.g., "Google Calendar", "Google Docs"). This is REQUIRED.
        session_id (Optional[str]): The active MCP session ID (automatically injected by FastMCP from the Mcp-Session-Id header). Links the OAuth flow state to the session.

    Returns:
        str: A detailed message for the LLM with the authorization URL and instructions to guide the user through the authentication process.
    """
    if not user_google_email or not isinstance(user_google_email, str) or '@' not in user_google_email:
        error_msg = "Invalid or missing 'user_google_email'. This parameter is required and must be a valid email address. LLM, please ask the user for their Google email address."
        print(f"email in google auth_error: {error_msg}")
        raise Exception(error_msg)

    if not service_name or not isinstance(service_name, str):
        error_msg = "Invalid or missing 'service_name'. This parameter is required (e.g., 'Google Calendar', 'Google Docs'). LLM, please specify the service name."
        print(f"[start_google_auth] {error_msg}")
        raise Exception(error_msg)

    print(f"Tool 'start_google_auth' invoked for user_google_email: '{user_google_email}', service: '{service_name}', session: '{session_id}'.")

    # Ensure OAuth callback is available for current transport mode
    # redirect_uri = get_oauth_redirect_uri_for_current_mode()
    # if not ensure_oauth_callback_available(_current_transport_mode, WORKSPACE_MCP_PORT, WORKSPACE_MCP_BASE_URI):
    #     raise Exception("Failed to start OAuth callback server. Please try again.")

    auth_result = await start_auth_flow(
        session_id=session_id,
        user_google_email=user_google_email,
        service_name=service_name,
        redirect_uri=redirect_uri,
        scopes=scopes,
        client_id=client_id,
        client_secret=client_secret,
        mode = mode
    )

    return auth_result


def google_mcp_main_server():
    """
    Main entry point for the Google Workspace MCP server.
    Uses FastMCP's native streamable-http transport.
    """

    # Import tool modules to register them with the MCP server via decorators
    tool_imports = {
        'gmail': lambda: importlib.import_module('...gmail.gmail_tools', package=__name__),
        'drive': lambda: importlib.import_module('...gdrive.drive_tools', package=__name__),
        'calendar': lambda: importlib.import_module('...gcalendar.calendar_tools', package=__name__),
        'docs': lambda: importlib.import_module('...gdocs.docs_tools', package=__name__),
        'sheets': lambda: importlib.import_module('...gsheets.sheets_tools', package=__name__),
        'chat': lambda: importlib.import_module('...gchat.chat_tools', package=__name__),
        'forms': lambda: importlib.import_module('...gforms.forms_tools', package=__name__),
        'slides': lambda: importlib.import_module('...gslides.slides_tools', package=__name__),
    }
    tools_to_import = tool_imports.keys()

    for tool in tools_to_import:
        tool_imports[tool]()
        print(f"{tool.title()} - Google {tool.title()} API integration")
   

    return server