import json
import asyncio
from typing import Optional
from ..core.imapclient import IMAPClient
from ..core.smtpclient import SMTPClient
from ..core.schemas import EmailServer

from ..core.constants import REDIS_IMAP_AUTH_CRED_PREFIX, REDIS_SMTP_AUTH_CRED_PREFIX
from ..server import server
from ..core.redis import redis_client
from ..core.helper import getimapcredentials, getsmtpcredentials

def format_forwarder_email(email: str, domain: str = "mail.mitexlab.com") -> str:
    email = email.lower()
    local, provider = email.split("@")
    clean_provider = provider.replace(".", "")  # gmail.com → gmailcom
    return f"{local}_{clean_provider}_forwarder@{domain}"

@server.tool()
async def hidefnx_configure_incoming_server(
    emailaddress: str,
    password: str,
    imap_host: str,
    imap_port: int,
    use_ssl: bool = True
):
    """
    Configure imap incoming server
    """
    
    email_server = EmailServer(
        user_name=emailaddress,
        password=password,
        host=imap_host,
        port=imap_port,
        use_ssl=use_ssl,
        fullname=""
    )
    
    try:
        print("Testing connection...")  
        async with IMAPClient(email_server) as client:
            key = f"{REDIS_IMAP_AUTH_CRED_PREFIX}{emailaddress}"
            await redis_client.set(key, email_server.model_dump_json())
            print("Configuration saved successfully")
      
        return {"success": True, "message": "Successfully configured!", "data": {"user_id": emailaddress}}
    except Exception as e:
        errormsg = f"error-configure_incoming_server: {e}"
        print(errormsg)
        return {"success": False, "message": "Connection failed. Check connection details!"}
    

@server.tool()
async def test_incoming_server(
    emailaddress: str
):
    """
    Test imap incoming server
    """

    imapauthdata = await getimapcredentials(emailaddress=emailaddress)
    if not imapauthdata:
        raise ValueError("Unable to retrieve imap auth data")
    
    try:
        print("Testing connection...")
        async with IMAPClient(imapauthdata) as client: 
            print("Connection successful!")
        return {"success": True, "message": "Connection successful!", "data": {"user_id": emailaddress}}
        
    except Exception as e:
        print(f"error-test_incoming_server: {e}")
        return {"success": False, "message": "Connection failed. Check connection details!"}
    

@server.tool()
async def hidefnx_configure_outgoing_server(
    emailaddress: str,
    password: str,
    fullname: str,
    smtp_host: str,
    smtp_port: int,
    start_ssl: bool = True,
    use_ssl: bool = False
):
    """
    Configure smtp outgoing server
    """
    
    email_server = EmailServer(
        user_name=emailaddress,
        password=password,
        fullname=fullname,
        host=smtp_host,
        port=smtp_port,
        start_ssl=start_ssl,
        use_ssl=use_ssl
    )
    
    try:
        print("Testing connection...")
        async with SMTPClient(email_server, "nill") as client:

            key = f"{REDIS_SMTP_AUTH_CRED_PREFIX}{emailaddress}"
            forwarder_key = f"{REDIS_SMTP_AUTH_CRED_PREFIX}{format_forwarder_email(emailaddress)}"

            await redis_client.set(key, email_server.model_dump_json())
            await redis_client.set(forwarder_key, email_server.model_dump_json())
            print("Configuration saved successfully")
      
        return {"success": True, "message": "Successfully configured!", "data": {"user_id": emailaddress}}

    except Exception as e:
        errormsg = f"error-configure_outgoing_server: {e}"
        print(errormsg)
        return {"success": False, "message": "Connection failed. Check connection details!"}
    

@server.tool()
async def test_outgoing_server(
    emailaddress: str
):
    """
    Test smtp outgoing server
    """

    smtpauthdata = await getsmtpcredentials(emailaddress=emailaddress)
    if not smtpauthdata:
        raise ValueError("Unable to retrieve smtp auth data")
    
    try:
        print("Testing connection...")
        async with SMTPClient(smtpauthdata, "nill") as client:
            print("Connection successful!")
        return {"success": True, "message": "Connection successful!", "data": {"user_id": emailaddress}}
        
    except Exception as e:
        print(f"error-test_outgoing_server: {e}")
        return {"success": False, "message": "Connection failed. Check connection details!"}
    

# if __name__ == "__main__":
#     result = asyncio.run( test_outgoing_server(
#         emailaddress="user@example.com",
#         # fullname="Rankloid",
#         # password="xxxxxxxxxxxx",
#         # smtp_host="smtp.gmail.com",
#         # smtp_port=587
#     ))
#     print(f"result:{result}")