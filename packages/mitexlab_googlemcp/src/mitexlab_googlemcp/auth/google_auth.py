import asyncio
from typing import Any, Dict, List, Literal, Optional, Tuple
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
import json

from httpx import Request
from ..core.redis import redis_client
from ..auth.scopes import REDIS_OAUTH_CRED_PREFIX
from googleapiclient.errors import HttpError


def create_oauth_flow(
    scopes: List[str],
    redirect_uri: str,
    client_id: str,
    client_secret: str,
) -> Flow:
    flow = Flow.from_client_config(
        client_config={
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=scopes
    )
    flow.redirect_uri = redirect_uri
    return flow


async def start_auth_flow(
    session_id: str,
    user_google_email: str,
    service_name: str,
    redirect_uri: str,
    scopes: List[str],
    client_id: str,
    client_secret: str,
    mode: Literal['forlogin', 'permissionrequest']
) -> str:
    initial_email_provided = bool(
        user_google_email
        and user_google_email.strip()
        and user_google_email.lower() != "default"
    )

    user_display_name = (
        f"{service_name} for '{user_google_email}'"
        if initial_email_provided
        else service_name
    )

    try:
        # Create flow first to get code_verifier if PKCE is used
        flow = create_oauth_flow(
            scopes=scopes,
            redirect_uri=redirect_uri,
            client_id=client_id,
            client_secret=client_secret
        )
        auth_url, _ = flow.authorization_url(
            state=session_id,
            access_type='offline',
            prompt='consent',
        )

        # Store code_verifier alongside state data in Redis
        key = session_id
        data = {
            "session_id": session_id,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "scopes": scopes,
            "mode": mode,
            "whichapp": "google",
            "code_verifier": flow.code_verifier if hasattr(flow, 'code_verifier') else None,
        }
        redis_client.set(key, json.dumps(data), ex=600)

        message_lines = [
            f"""**ACTION REQUIRED: Google Authentication Needed for {user_display_name}**""",
            f"To proceed, the user must authorize this application for {service_name} access using all required permissions.",
            "**LLM, please present this exact authorization URL to the user as a clickable hyperlink:**",
            f"Authorization URL: {auth_url}",
            f"Markdown for hyperlink: [Click here to authorize {service_name} access]({auth_url})\n",
            "**LLM, after presenting the link, instruct the user as follows:**",
            "1. Click the link and complete the authorization in their browser.",
            f"The application will use the new credentials. If '{user_google_email}' was provided, it must match the authenticated account.",
        ]
        return "\n".join(message_lines)
    except Exception as e:
        error_text = f"Could not initiate authentication for {user_display_name} due to an unexpected error: {str(e)}"
        print(f"Failed to start the OAuth flow for {user_display_name}: {e}")
        raise Exception(error_text)


def handle_auth_callback(
    authorization_response: str,
) -> Tuple[str, Credentials, dict[str, Any]]:
    try:
        from urllib.parse import urlparse, parse_qs, unquote

        parsed_url = urlparse(authorization_response)
        query_params = parse_qs(parsed_url.query)
        state = query_params.get("state", [None])[0]

        print(f"authorization_response: {authorization_response}")
        print(f"parsed_url: {parsed_url}")
        print(f"query_params: {query_params}")
        print(f"state: {state}")

        if not state:
            raise ValueError("OAuth state not found in authorization response.")

        statekey = state
        statedata = redis_client.get(statekey)
        if not statedata:
            raise ValueError("Unable to retrieve oauth state from redis")

        session_data = json.loads(statedata)
        if not session_data:
            raise ValueError(f"No session data found for state: {state}")

        session_id = session_data.get("session_id")
        client_id = session_data.get("client_id")
        client_secret = session_data.get("client_secret")
        redirect_uri = session_data.get("redirect_uri")
        mode = session_data.get("mode")
        code_verifier = session_data.get("code_verifier")  # retrieve stored verifier

        # Use scopes from session data (source of truth)
        scopes = session_data.get("scopes", [])

        print(f"session_id: {session_id}")
        print(f"client_id: {client_id}")
        print(f"client_secret: {'*' * len(client_secret) if client_secret else None}")
        print(f"redirect_uri: {redirect_uri}")
        print(f"scopes: {scopes}")
        print(f"code_verifier present: {bool(code_verifier)}")

        if not all([client_id, client_secret, redirect_uri]):
            raise ValueError("Client ID, Client Secret, or Redirect URI are missing in session data.")

        flow = create_oauth_flow(
            scopes=scopes,
            redirect_uri=redirect_uri,
            client_id=client_id,
            client_secret=client_secret,
        )

        # Pass code_verifier if it exists
        fetch_kwargs = {"authorization_response": authorization_response}
        if code_verifier:
            fetch_kwargs["code_verifier"] = code_verifier

        flow.fetch_token(**fetch_kwargs)
        credentials = flow.credentials
        print("Successfully exchanged authorization code for tokens.")

        if not credentials.client_id and client_id:
            credentials.client_id = client_id
        if not credentials.client_secret and client_secret:
            credentials.client_secret = client_secret

        user_info = get_user_info(credentials)
        if not user_info or "email" not in user_info:
            raise ValueError("Failed to get user email for identification.")

        user_google_email = user_info["email"]
        print(f"Identified user_google_email: {user_google_email}\n\n")

        credentials_dict = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': list(credentials.scopes) if credentials.scopes else scopes,
            'expiry': credentials.expiry.isoformat() if credentials.expiry else None,
            'mode': mode
        }
        key = f"{REDIS_OAUTH_CRED_PREFIX}{user_google_email}"
        redis_client.set(key, json.dumps(credentials_dict))
        redis_client.delete(statekey)

        return user_google_email, credentials, credentials_dict

    except Exception as e:
        print(f"Error handling auth callback: {e}")
        raise


def get_credentials(
    required_scopes: List[str],
    user_google_email: str,
) -> Optional[Credentials]:

    key = f"{REDIS_OAUTH_CRED_PREFIX}{user_google_email}"
    print(f"key-hhupt: {key}")

    statedata = redis_client.get(key)
    print(f"statedata: {statedata}")
    if not statedata:
        return None

    credentials_dict = json.loads(statedata)
    print(f"credentials_dict: {credentials_dict}")

    credentials = Credentials(
        token=credentials_dict.get('token'),
        refresh_token=credentials_dict.get('refresh_token'),
        token_uri=credentials_dict.get('token_uri'),
        client_id=credentials_dict.get('client_id'),
        client_secret=credentials_dict.get('client_secret'),
        scopes=credentials_dict.get('scopes')
    )

    print(f"credentials-hh: {credentials}")

    if not credentials:
        return None

    if not all(scope in (credentials.scopes or []) for scope in required_scopes):
        print(f"Credentials lack required scopes. Need: {required_scopes}, Have: {credentials.scopes}. User: {user_google_email}")
        return None

    if credentials.valid:
        print(f"\n\nCredentials are valid. User: '{user_google_email}\n\n")
        return credentials

    elif credentials.expired and credentials.refresh_token:
        print(f"Credentials expired. Attempting refresh. User: '{user_google_email}")
        try:
            credentials.refresh(Request())
            print(f"Credentials refreshed successfully. User: {user_google_email}")

            credentials_dict = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': list(credentials.scopes) if credentials.scopes else [],
                'expiry': credentials.expiry.isoformat() if credentials.expiry else None
            }
            redis_client.set(key, json.dumps(credentials_dict))
            return credentials
        except RefreshError as e:
            print(f"RefreshError - token expired/revoked: {e}. User: '{user_google_email}")
            return None
        except Exception as e:
            print(f"Error refreshing credentials: {e}. User: {user_google_email}")
            return None
    else:
        print(f"Credentials invalid/cannot refresh. Valid: {credentials.valid}, Refresh Token: {credentials.refresh_token is not None}. User: '{user_google_email}")
        return None


def get_user_info(credentials: Credentials) -> Optional[Dict[str, Any]]:
    print(f"\n\ncredentials: {credentials}")
    print(f"Token: {credentials.token}")
    print(f"Refresh token: {credentials.refresh_token}")
    print(f"Client ID: {credentials.client_id}")
    print(f"Expiry: {credentials.expiry}")
    print(f"Scopes: {credentials.scopes}")

    if not credentials or not credentials.valid:
        print("Cannot get user info: Invalid or missing credentials.")
        return None
    try:
        service = build("oauth2", "v2", credentials=credentials)
        user_info = service.userinfo().get().execute()
        print(f"Successfully fetched user info: {user_info.get('email')}")
        return user_info
    except HttpError as e:
        print(f"HttpError fetching user info: {e.status_code} {e.reason}")
        return None
    except Exception as e:
        print(f"Unexpected error fetching user info: {e}")
        return None


class GoogleAuthenticationError(Exception):
    def __init__(self, message: str, auth_url: Optional[str] = None):
        super().__init__(message)
        self.auth_url = auth_url


async def get_authenticated_google_service(
    required_scopes: List[str],
    service_name: str,
    version: str,
    tool_name: str,
    user_google_email: str
) -> Optional[tuple[Any, str]]:

    if not user_google_email or "@" not in user_google_email:
        error_msg = f"Authentication required for {tool_name} service: {service_name}. No valid 'user_google_email' provided."
        print(f"get_authenticated_google_service-err: {error_msg}")
        raise GoogleAuthenticationError(error_msg)

    credentials = await asyncio.to_thread(
        get_credentials,
        required_scopes=required_scopes,
        user_google_email=user_google_email
    )

    if not credentials or not credentials.valid:
        return None

    try:
        service = build(service_name, version, credentials=credentials)
        print(f"[{tool_name}] Successfully authenticated {service_name} service for user: {user_google_email}")
        return service, user_google_email
    except Exception as e:
        error_msg = f"[{tool_name}] Failed to build {service_name} service: {str(e)}"
        print(f"get_authenticated_google_service_error: {error_msg}")
        raise GoogleAuthenticationError(error_msg)