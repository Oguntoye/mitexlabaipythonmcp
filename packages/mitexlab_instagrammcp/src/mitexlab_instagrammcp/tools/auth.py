import json
import logging
import time

from ..core.api import  InstagramAPI
from ..core.constants import REDIS_OAUTH_CRED_PREFIX
from ..server import server
from ..core.redis import redis_client
from ..core.helper import getaccesstoken
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


@server.tool()
async def get_login_url(
    session_id: str,
    app_id: str,
    app_secret: str,
    redirect_uri: str
):
    """
    Generate the Instagram login URL for user authentication.
    User must visit this link and grant permissions.
    """
    scopes = [
        "instagram_business_basic",
        # "instagram_business_content_publish",
        "instagram_business_manage_comments",
        "instagram_business_manage_messages"
    ]

    params = {
        "client_id": app_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": ",".join(scopes),
        "state": session_id
    }

    key = session_id
    data = {
        "session_id": session_id,
        "app_id": app_id,
        "app_secret": app_secret,
        "redirect_uri": redirect_uri,
        "whichapp":"instagram"
    }
    await redis_client.set(key, json.dumps(data), ex=600)
    return f"https://api.instagram.com/oauth/authorize?{urlencode(params)}"


@server.tool()
async def exchange_code_for_token(
    code: str, 
    session_id: str,
):
    """
    Exchange the short-lived code for a short-lived access token,
    then upgrade to long-lived token and store it in Redis.
    """
    try:

        statekey = session_id
        statedata = await redis_client.get(statekey)
        if not statedata:
            raise ValueError("Unable to retrieve oauth state from redis")
        
        session_data = json.loads(statedata)
        if not session_data:
            raise ValueError(f"No session data found for state: {session_id}")
        

        session_id = session_data.get("session_id")
        app_id = session_data.get("app_id")
        app_secret = session_data.get("app_secret")
        redirect_uri = session_data.get("redirect_uri")

        async with InstagramAPI( access_token="nill", app_id=app_id, app_secret=app_secret ) as igclientinstance:
            if not igclientinstance:
                raise ValueError("Invalid client instantiated")
        
            short_token_response = await igclientinstance.exchange_code_for_token(code=code, redirect_uri=redirect_uri)
            logger.debug("Instagram short-lived token exchange completed")

            if not short_token_response or "access_token" not in short_token_response:
                return { "success": False,"message": "error occurred! unable to generate slt" }
            
            shorttoken = short_token_response["access_token"]

            long_token_response = await igclientinstance.get_long_lived_token(short_lived_token=shorttoken)

            if not long_token_response or "access_token" not in long_token_response:
                return { "success": False,"message": "error occurred! unable to generate llt" }        
        # in slt=> access_token, user_id
        # in llt=> access_token, token_type, expires_in

    
        # ##get  profile details
        llt = long_token_response["access_token"]
        async with InstagramAPI( access_token=llt, app_id="nill", app_secret="nill") as reqigcl:
            if not reqigcl:
                raise ValueError("Invalid client reqigcl")
            
            profiledetails = await reqigcl.get_user_profile()
            if not profiledetails or "username" not in profiledetails:
                return { "success": False,"message": "error occurred! unable to generate ppdetails" }   

        profileusername = profiledetails["username"]
        profileuserid = profiledetails["user_id"]

        # credentials_dict = {
        #     "access_token":long_token_response["access_token"],
        #     "user_id": profiledetails["user_id"],
        #     "profileid": profiledetails["id"],
        #     "username": profiledetails["username"],
        #     "profile_picture_url": profiledetails["profile_picture_url"],
        #     "name": profiledetails["name"],
        #     # "expires_in": long_token_response["expires_in"],
        #     "expires_in": long_token_response["expires_in"],   # seconds, relative
        #     "expires_at": int(time.time()) + long_token_response["expires_in"],  # absolute timestamp
        #     "profile_picture_url": profiledetails["profile_picture_url"],
        #     "fullprofile": profiledetails,
        #     "app_id": app_id,
        #     "app_secret": app_secret,
        #     "redirect_uri": redirect_uri,
        # }
        credentials_dict = {
            "access_token": long_token_response.get("access_token"),
            "user_id": profiledetails.get("user_id"),
            "profileid": profiledetails.get("id"),
            "username": profiledetails.get("username"),
            "profile_picture_url": profiledetails.get("profile_picture_url"),
            "name": profiledetails.get("name"),
            "expires_in": long_token_response.get("expires_in"),
            "expires_at": int(time.time()) + long_token_response.get("expires_in", 0),
            "fullprofile": profiledetails,
            "app_id": app_id,
            "app_secret": app_secret,
            "redirect_uri": redirect_uri
        }

        key1 = f"{REDIS_OAUTH_CRED_PREFIX}{profileusername}"
        key2 = f"{REDIS_OAUTH_CRED_PREFIX}{profileuserid}"
        await redis_client.set(key1, json.dumps(credentials_dict))
        await redis_client.set(key2, json.dumps(credentials_dict))

        return {
            "success": True,
            "message": "Authentication successful",
            "data": {
                "user_id": profileusername,
                "profileuserid": profileuserid,
                "state": session_id,
            },
        }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"Error processing OAuth callback: {str(e)}",
            "data": {"state": session_id}
        }


@server.tool()
async def test_connection( 
    username: str, 
) -> str:
    """
    Test the validity of a user access token
    """

    try:
        accesstoken = await getaccesstoken(username=username)
        if not accesstoken:
            raise ValueError("Unable to retrive user access token")

        async with InstagramAPI( access_token=accesstoken) as instagram_api:
            if not instagram_api:
                raise ValueError("Invalid client instantiated")

            result = await instagram_api.test_connection()
        if not result:
            raise ValueError(f"Failed to test_connection")
            
        return (
            f"Connection successful!\n"
            f"User ID: {result.get('user_id')}\n"
            f"Username: {result.get('username')}\n"
        )
    except Exception as e:
        raise ValueError(f"error-test_connection: {str(e)}")