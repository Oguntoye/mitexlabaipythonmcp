import asyncio
import json
import time
from typing import Any, Dict
from unittest import result
import cloudinary
import cloudinary.uploader
import cloudinary.api 
from urllib.parse import urlparse
import httpx
from ..core.api import WhatsAppAPI
from ..core.constants import REDIS_OAUTH_CRED_PREFIX, WA_API_VERSION, WA_GRAPH_API_URL
from ..core.helper import get_access_token, get_business_account_id, get_whatsapp_authdata, normalize_phone
from ..core.redis import redis_client
from ..server import server
from ..env import settings


@server.tool()
async def complete_whatsapp_signup(
    code: str,
    cloudinaryurl: str
) -> Dict[str, Any]:
    try:
        APP_ID = settings.WA_APP_ID
        APP_SECRET = settings.WA_APP_SECRET
        base_url = f"{WA_GRAPH_API_URL}/{WA_API_VERSION}"

        # Step 1: Exchange code for access token
        token_url = (
            f"{base_url}/oauth/access_token?"
            f"client_id={APP_ID}&client_secret={APP_SECRET}&code={code}"
        )
        async with httpx.AsyncClient() as client:
            token_response = await client.get(token_url, timeout=30.0)
            token_data = token_response.json()
        print(f"\ntoken_data1: {token_data}")

        if 'error' in token_data:
            return {
                "success": False,
                "message": f"Token exchange failed: {token_data.get('error', {}).get('message', 'Unknown error')}",
                "data": token_data
            }
        
        access_token = token_data.get('access_token')
        if not access_token:
            return {
                "success": False,
                "message": "No access token in response",
                "data": token_data
            }

        # Step 2: Debug token to get WABA ID
        debug_url = (
            f"{base_url}/debug_token?"
            f"input_token={access_token}&access_token={APP_ID}|{APP_SECRET}"
        )
        async with httpx.AsyncClient() as client:
            debug_response = await client.get(debug_url, timeout=30.0)
            debug_data = debug_response.json()
        print(f"\ndebug_data2: {debug_data}")
      

        if 'error' in debug_data:
            return {
                "success": False,
                "message": f"Debug token failed: {debug_data.get('error', {}).get('message', 'Unknown error')}",
                "data": debug_data
            }

        granular_scopes = debug_data.get('data', {}).get('granular_scopes', [])
        if not granular_scopes:
            return {
                "success": False,
                "message": "No granular_scopes found in token debug response",
                "data": debug_data
            }

        # Find the whatsapp_business_management scope with target_ids
        waba_id = None
        for scope in granular_scopes:
            if scope.get('scope') == 'whatsapp_business_management':
                target_ids = scope.get('target_ids', [])
                if target_ids:
                    waba_id = target_ids[0]
                    break

        if not waba_id:
            return {
                "success": False,
                "message": "No WABA ID found in granular_scopes",
                "data": debug_data
            }

        # Step 3: Get phone number
        phone_url = f"{base_url}/{waba_id}/phone_numbers"
        headers = {'Authorization': f'Bearer {access_token}'}
        async with httpx.AsyncClient() as client:
            phone_response = await client.get(phone_url, headers=headers, timeout=30.0)
            phone_data = phone_response.json()
        print(f"\nphone_data3: {phone_data}")
        print(f"\nwaba_id: {waba_id}")

        if 'error' in phone_data:
            return {
                "success": False,
                "message": f"Get phone number failed: {phone_data.get('error', {}).get('message', 'Unknown error')}",
                "data": phone_data
            }
        
        phones = phone_data.get('data', [])
        if not phones:
            return {
                "success": False,
                "message": "No phone numbers found for WABA",
                "data": phone_data
            }
        
        phone_info = phones[0]
        phonenumberid = phone_info.get('id')
        display_phone = phone_info.get('display_phone_number')
        normalized_display_phonenumber = normalize_phone(display_phone)
        verified_name = phone_info.get('verified_name')
        platform_type = phone_info.get('platform_type')

        print(f"\nphone_info: {phone_info}")
        print(f"\nphonenumberid: {phonenumberid}")
        print(f"\ndisplay_phone: {display_phone}")
        print(f"\nnormalized_display_phonenumber: {normalized_display_phonenumber}")
        print(f"\nverified_name: {verified_name}")
        print(f"\nplatform_type: {platform_type}")

        
        
        if not phonenumberid:
            return {
                "success": False,
                "message": "Phone number ID not found in response",
                "data": phone_data
            }
        

        # Step 4: Register phone number (if needed)
        headers = {'Authorization': f'Bearer {access_token}'}
        
        if platform_type != "CLOUD_API":
            try:
                async with httpx.AsyncClient() as client:
                    # Register phone number
                    register_url = f"{base_url}/{phonenumberid}/register"
                    register_payload = {
                        "messaging_product": "whatsapp",
                        "pin": phonenumberid[:6]
                    }
                    register_response = await client.post(
                        register_url, 
                        headers=headers, 
                        json=register_payload,
                        timeout=30.0
                    )
                    registrationdetails = register_response.json()
                    print(f"\nregistrationdetails2: {registrationdetails}")

                    if 'error' in registrationdetails or not registrationdetails.get('success'):
                        return {
                            "success": False,
                            "message": f"Phone number {normalized_display_phonenumber} is verified but not connected yet to Whatsapp cloud API!",
                            "data": {
                                "registrationdetails": registrationdetails
                            },
                        }
            except Exception as e:
                print(f"\nError during phone registration: {str(e)}")
                return {
                    "success": False,
                    "message": f"Phone registration request failed: {str(e)}",
                    "data": {
                        "error": str(e),
                        "phone_number": normalized_display_phonenumber
                    }
                }
        
        # Step 5: subscribe to webhhook and Check token expiry
        try:
            async with httpx.AsyncClient() as client:
                # Step 5.1: Subscribe webhook to WABA
                subscribe_url = f"{base_url}/{waba_id}/subscribed_apps"
                subscribe_response = await client.post(
                    subscribe_url,
                    headers=headers,
                    timeout=30.0
                )
                subscribe_data = subscribe_response.json()
                print(f"\nsubscribe_data: {subscribe_data}")

                if 'error' in subscribe_data:
                    return {
                        "success": False,
                        "message": f"Webhook subscription failed: {subscribe_data.get('error', {}).get('message')}",
                        "data": subscribe_data
                    }

                
                # Step 5.2: Check expirty
                token_debug_url = (
                    f"{base_url}/debug_token?"
                    f"input_token={access_token}&access_token={APP_ID}|{APP_SECRET}"
                )
                token_validity_response = await client.get(token_debug_url, timeout=30.0)
                token_validity_data = token_validity_response.json()
                
                tokenvaliddityresult = {
                    "data": {
                        "expires_at": token_validity_data.get('data', {}).get('expires_at', 0)
                    }
                }
                print(f"tokenvaliddityresult: {tokenvaliddityresult}")
                
                # Prepare token expiry info
                expires_at = tokenvaliddityresult["data"]["expires_at"]
                token_never_expires = expires_at == 0
                if token_never_expires:
                    expires_at_value = 0  # Store 0 to indicate no expiry
                else:
                    expires_at_value = expires_at  # Store the Unix timestamp
        except Exception as e:
            print(f"\nError during token validity check: {str(e)}")
            return {
                "success": False,
                "message": f"Token validity check failed: {str(e)}",
                "data": {
                    "error": str(e)
                }
            }

            
        credentials_dict = {
            "cloudinaryurl": cloudinaryurl,
            "fullphonenumber": normalized_display_phonenumber,
            "phone_number_id": phonenumberid,
            "access_token": access_token,
            "business_account_id": waba_id,
            "app_id": APP_ID,
            "app_secret": APP_SECRET,
            "name": verified_name,
            "expires_at": expires_at_value,  # Unix timestamp or 0 for never expires
            "token_never_expires": token_never_expires,  # Boolean flag
        }

        key = f"{REDIS_OAUTH_CRED_PREFIX}{phonenumberid}"
        await redis_client.set(key, json.dumps(credentials_dict))

        return { 
            "success": True, 
            "message": "Authentication successful",
            "data": {
                "user_id": phonenumberid,
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error setting up WhatsApp credentials: {str(e)}",
            "data": None
        }



@server.tool()
async def setup_whatsapp_credentials(
    fullphonenumber: str,
    access_token: str,
    app_id: str,
    app_secret: str,
    business_account_id: str,
    cloudinaryurl: str
) -> Dict[str, Any]:
    """
    Setup WhatsApp credentials for a phone number.

    Args:
        fullphonenumber (str): Your WhatsApp Business phone number ID
        access_token (str): Your WhatsApp Business access token
        app_id (str): Your Meta App ID
        app_secret (str): Your Meta App Secret
        business_account_id (str): Your WhatsApp Business account ID (optional)
    """
    try:
        parsed = urlparse(cloudinaryurl)
        if  parsed.scheme != 'cloudinary':
            return {
                "success": False,
                "message": f"Invalid Cloudinary URL scheme",
                "data": None,
            }

        parsed = urlparse(cloudinaryurl)
        cloudinary.config(
            cloud_name=parsed.hostname,
            api_key=parsed.username,
            api_secret=parsed.password
        )
        result = cloudinary.api.ping()
        if result.get('status') != 'ok':
            return {
                "success": False,
                "message": f"Invalid cloudinary credential",
                "data": None,
            }

        async with WhatsAppAPI(
            access_token=access_token,
            phone_number_id="nill",
            business_account_id=business_account_id,
        ) as wa_client:
            # if not wa_client:
            #     raise ValueError("Invalid client instantiated")
            
            normalized_phonenumber_passed = normalize_phone(fullphonenumber)

            ##g et list of all phone  number linked to the business accountid
            alllinkedphonenumbers = await wa_client.get_phone_numbers()

            obj_detail_of_number_found = None
            for number_data in alllinkedphonenumbers.get('data', []):
                display_number = number_data.get('display_phone_number', '')
                normalized_phonenumber_inloop = normalize_phone(display_number)
                
                if normalized_phonenumber_inloop == normalized_phonenumber_passed:
                    obj_detail_of_number_found = number_data
                    break
            
            print(f"\n\nobj_detail_of_number_found: {obj_detail_of_number_found}")
            if not obj_detail_of_number_found:
                return {
                    "success": False,
                    "message": f"Phone number {fullphonenumber} not found in linked numbers",
                    "data": None,
                }
            if obj_detail_of_number_found['code_verification_status'] != "VERIFIED":
                return {
                    "success": False,
                    "message": f"Phone number {fullphonenumber} is yet to be verified!",
                    "data": None,
                }
            
            phonenumberid = obj_detail_of_number_found['id']
            if obj_detail_of_number_found['platform_type'] != "CLOUD_API":
                ### Attempt to register the number first
                registrationdetails = await wa_client.register_phone_number(
                    pin=phonenumberid[:6],
                    phone_number_id=phonenumberid
                )
                print(f"\nregistrationdetails2: {registrationdetails}")

                if registrationdetails['success'] != True:
                    return {
                        "success": False,
                        "message": f"Phone number {fullphonenumber} is verified but not connected yet to Whatsapp cloud API!",
                        "data": {
                            "numberdetails":obj_detail_of_number_found,
                            "registrationdetails": registrationdetails
                        },
                    }


            tokenvaliddityresult = await wa_client.check_token_expiry(
                app_id=app_id, 
                app_secret=app_secret
            )
            print(f"tokenvaliddityresult: {tokenvaliddityresult}")
            
            # Prepare token expiry info
            expires_at = tokenvaliddityresult["data"]["expires_at"]
            token_never_expires = expires_at == 0
            if token_never_expires:
                expires_at_value = 0  # Store 0 to indicate no expiry
            else:
                expires_at_value = expires_at  # Store the Unix timestamp

            
            credentials_dict = {
                "cloudinaryurl": cloudinaryurl,
                "fullphonenumber": fullphonenumber,
                "phone_number_id": phonenumberid,
                "access_token": access_token,
                "business_account_id": business_account_id,
                "app_id": app_id,
                "app_secret": app_secret,
                "name": obj_detail_of_number_found['verified_name'],
                "expires_at": expires_at_value,  # Unix timestamp or 0 for never expires
                "token_never_expires": token_never_expires,  # Boolean flag
            }

            key = f"{REDIS_OAUTH_CRED_PREFIX}{phonenumberid}"
            await redis_client.set(key, json.dumps(credentials_dict))

            return { "success": True, "message": "Authentication successful",
                "data": {
                    "user_id": phonenumberid,
                    # "credentials_dict": credentials_dict
                }
            }

    except Exception as e:
        return {
            "success": False,
            "message": f"Error setting up WhatsApp credentials: {str(e)}",
        }



@server.tool()
async def test_whatsapp_connection(
    phone_number_id: str,
) -> dict:
    """
    Test the WhatsApp API connection for a phone number.
    """
    try:
        
        access_token = await get_access_token(phone_number_id=phone_number_id)
        businessaccountid = await get_business_account_id(phone_number_id=phone_number_id)
        
        async with WhatsAppAPI(
            access_token=access_token,
            phone_number_id=phone_number_id,
            business_account_id=businessaccountid,
        ) as wa_client:
            
            ##g et list of all phone  number linked to the business accountid
            alllinkedphonenumbers = await wa_client.get_phone_numbers()
            
            obj_detail_of_number_found = None
            for number_data in alllinkedphonenumbers.get('data', []):
                phone_number_id_inloop = number_data.get('id', '')
                if phone_number_id_inloop == phone_number_id:
                    obj_detail_of_number_found = number_data
                    break
            
            if not obj_detail_of_number_found:
                return {
                    "success": False,
                    "message": f"Phone number not found in linked numbers",
                    "data": None,
                }
            # if obj_detail_of_number_found['code_verification_status'] != "VERIFIED":
            #     return {
            #         "success": False,
            #         "message": f"Phone number is yet to be verified!",
            #         "data": None,
            #     }
            if obj_detail_of_number_found['platform_type'] != "CLOUD_API":
                return {
                    "success": False,
                    # "message": f"Phone number is verified but not connected yet to Whatsapp cloud API!",
                    "message": f"Phone number is not connected yet to Whatsapp cloud API!",
                    "data": None,
                }


            return {
                "success": True,
                "message": "Connection successful!",
                "data": {
                    "phone_number_id": obj_detail_of_number_found['id'],
                    "name": obj_detail_of_number_found['verified_name'],
                    "webhookurl": obj_detail_of_number_found['webhook_configuration'],
                    "fulldetails": obj_detail_of_number_found
                },
            }

    except Exception as e:
        return {
            "success": False,
            "message": f"Connection test error: {str(e)}",
            "data": None,
        }
    



# async def quickie():
#     result = await complete_whatsapp_signup(
#         cloudinaryurl="[REDACTED]",
#         code="AQAQY9XQvCrTbHgOH1AZ8IBY642f1zVtrAY0WuTjIeoGBBXbfRfMkHRyJhsxcM3nLEQtYrc0NJzOLcOhIj9p4Eu96bh7vj8OIpCrM4bHX4Di1XRPQtqvWE4iJJGuVZjnsnvfz7akWkbIlIZuDgnI11hQILfdqUTwOAeOQczwSmVVd0Aedsa5OT6D4GMTPCjxHyZ7Wm7bPMeFFqflycvqHPz4Own3M3_rZ-fangUkkBkm6A98PdMMjVadVw_F61NjOV2Evz1spW9mM_E8Cxh7MYlYpcGRVcrQ-HQKrG0ENjjv7CzwhoV-suYo4MRNe3ENT7ofLNIQ1SciMadOGme93A0PtwrMtDAYU3yMnyEqGq90WjwCHNPKY8HvvV1mP8M09r_qtz9yLzdxQ_Q0mbpC0q88yAoQoDBQGGFe0o4gdKlBAr-Ne7mwYEHg_rWngx1Ljvo"
#     )
#     print(f"result: {result}")
# if __name__ == "__main__":
#     asyncio.run(quickie())