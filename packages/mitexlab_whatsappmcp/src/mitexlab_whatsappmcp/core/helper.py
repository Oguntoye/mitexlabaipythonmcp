import json
import time
import httpx
from ..core.api import WhatsAppAPI
from ..core.constants import REDIS_OAUTH_CRED_PREFIX, WA_API_VERSION, WA_GRAPH_API_URL
from ..core.redis import redis_client
import time

def normalize_phone(phone: str) -> str:
    """Remove spaces, plus signs, and trim whitespace"""
    return phone.strip().replace("+", "").replace(" ", "")


async def get_access_token(phone_number_id: str):
    try:
        # normalized_number = normalize_phone(fullphonenumber)
        statekey = f"{REDIS_OAUTH_CRED_PREFIX}{phone_number_id}"
        statedata = await redis_client.get(statekey)
        
        if not statedata:
            raise ValueError("Unable to retrieve WhatsApp credentials frmrds")
        
        auth_data = json.loads(statedata)
        if not auth_data or "access_token" not in auth_data:
            raise ValueError(f"No credentials found for number: {phone_number_id}")
        
        # Check if token never expires
        if auth_data.get("token_never_expires", False) or auth_data.get("expires_at", 0) == 0:
            print("Token never expires, no refresh needed")
            return auth_data["access_token"]
        
        # Calculate remaining time
        remaining_seconds = max(0, auth_data["expires_at"] - int(time.time()))
        remaining_days = remaining_seconds // 86400
        accesstoken = auth_data["access_token"]
        print(f"Token expires in {remaining_days} days")
        
        # Refresh if less than 7 days remain
        if remaining_days <= 30:
            async with WhatsAppAPI(
                access_token=accesstoken,
                phone_number_id=auth_data["phone_number_id"],
                business_account_id=auth_data["business_account_id"],
            ) as wa_client:
                result = await wa_client.refresh_long_lived_token(
                    app_id=auth_data["app_id"],
                    app_secret=auth_data["app_secret"]
                )
                
                print(f"Token refresh result: {result}")
                
                if not result or "access_token" not in result:
                    raise ValueError("Token refresh failed")
                
                accesstoken = result["access_token"]
                auth_data["access_token"] = result["access_token"]
                
                # Handle both possible response formats
                if "expires_in" in result:
                    auth_data["expires_in"] = result["expires_in"]
                    auth_data["expires_at"] = int(time.time()) + result["expires_in"]
                elif "data_access_expires_at" in result:
                    # Some tokens return data_access_expires_at instead
                    auth_data["expires_at"] = result["data_access_expires_at"]
                else:
                    # Default to 60 days (5184000 seconds) for long-lived tokens
                    auth_data["expires_in"] = 5184000
                    auth_data["expires_at"] = int(time.time()) + 5184000
                
                # Update redis
                await redis_client.set(statekey, json.dumps(auth_data))
                
                print(f"Token refreshed successfully")
        
        return accesstoken
        
    except Exception as e:
        raise ValueError(f"get_access_token error: {e}")


async def get_whatsapp_authdata(phone_number_id: str):
    try:
        # normalized_number = normalize_phone(fullphonenumber)
        statekey = f"{REDIS_OAUTH_CRED_PREFIX}{phone_number_id}"
        statedata = await redis_client.get(statekey)
        
        if not statedata:
            raise ValueError("Unable to retrieve WhatsApp credentials frmrds")
        
        auth_data = json.loads(statedata)
        if not auth_data or "access_token" not in auth_data:
            raise ValueError(f"No credentials found for number: {phone_number_id}")
        
        return auth_data
        
    except Exception as e:
        raise ValueError(f"get_whatsapp_authdata error: {e}")
    
async def get_business_account_id(phone_number_id: str):
    try:
        # normalized_number = normalize_phone(fullphonenumber)
        statekey = f"{REDIS_OAUTH_CRED_PREFIX}{phone_number_id}"
        statedata = await redis_client.get(statekey)
        
        if not statedata:
            raise ValueError("Unable to retrieve WhatsApp credentials frmrds")
        
        auth_data = json.loads(statedata)
        if not auth_data or "access_token" not in auth_data:
            raise ValueError(f"No credentials found for number: {phone_number_id}")
        
        return auth_data['business_account_id']
        
    except Exception as e:
        raise ValueError(f"get_whatsapp_authdata error: {e}")

