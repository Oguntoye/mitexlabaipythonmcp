
import json
# from ..tools.auth import REDIS_OAUTH_CRED_PREFIX, redis_client
from ..core.redis import redis_client
from ..core.constants import REDIS_OAUTH_CRED_PREFIX
from ..core.api import InstagramAPI
import time


async def getaccesstoken(username: str):
    try:
        statekey = f"{REDIS_OAUTH_CRED_PREFIX}{username}"
        statedata = await redis_client.get(statekey)
        if not statedata:
            raise ValueError("Unable to retrieve auth data from redis")
        
        auth_data = json.loads(statedata)
        if not auth_data or "access_token" not in auth_data:
            raise ValueError(f"No session data found for username: {username}")
        
        # remaining_seconds = auth_data["expires_at"] - int(time.time())
        # remaining_days = remaining_seconds // 86400

        remaining_seconds = max(0, auth_data["expires_at"] - int(time.time()))
        remaining_days = remaining_seconds // 86400
        accesstoken: str = auth_data["access_token"]
        print(f"remaining_days: {remaining_days}")

        if remaining_days <= 30:
            async with InstagramAPI( access_token=accesstoken) as instagram_api:
                result = await instagram_api.refresh_token()
                if not result or "access_token" not in result:
                    raise ValueError("Token refresh failed")
                
                accesstoken = result["access_token"]
                auth_data["access_token"] = result["access_token"]
                auth_data["expires_in"] = result["expires_in"]
                auth_data["expires_at"] =  int(time.time()) + result["expires_in"]

                key1 = f"{REDIS_OAUTH_CRED_PREFIX}{auth_data['username']}"
                key2 = f"{REDIS_OAUTH_CRED_PREFIX}{auth_data['user_id']}"

                # await redis_client.set(key1, json.dumps(auth_data))
                # await redis_client.set(key2, json.dumps(auth_data))

                pipe = redis_client.pipeline()
                pipe.set(key1, json.dumps(auth_data))
                pipe.set(key2, json.dumps(auth_data))
                await pipe.execute()

                print(f"result: {result}")

        return accesstoken
    except Exception as e:
        # print(f"getaccesstoken-error: {str(e)}")
        raise ValueError(f"getaccesstoken-error: {e}") 
        return ""
    

async def getprofileuserid(username: str):
    try:
        statekey = f"{REDIS_OAUTH_CRED_PREFIX}{username}"
        statedata = await redis_client.get(statekey)
        if not statedata:
            raise ValueError("Unable to retrieve auth data from redis")
        
        auth_data = json.loads(statedata)
        if not auth_data or "user_id" not in auth_data:
            raise ValueError(f"No session data found for username: {username}")
        user_id: str = auth_data["user_id"]
        return user_id
    except Exception as e:
        print(f"getprofileuserid-error: {str(e)}")
        return ""
