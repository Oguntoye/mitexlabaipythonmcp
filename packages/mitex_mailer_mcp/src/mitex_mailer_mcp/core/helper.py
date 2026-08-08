import json
from datetime import datetime, timedelta
import re
from html import unescape
from ..core.redis import redis_client
from ..core.constants import REDIS_IMAP_AUTH_CRED_PREFIX, REDIS_SMTP_AUTH_CRED_PREFIX
from ..core.imapclient import IMAPClient
from ..core.smtpclient import SMTPClient
from ..core.schemas import EmailServer, EmailPageResponse


async def getimapcredentials(emailaddress: str):
    try:
        statekey = f"{REDIS_IMAP_AUTH_CRED_PREFIX}{emailaddress}"
        statedata = await redis_client.get(statekey)
        if not statedata:
            raise ValueError("Unable to retrieve imapauth data f. err.frm-rds")
        
        # auth_data = EmailServer(**json.loads(statedata))
        auth_data = EmailServer.model_validate(json.loads(statedata))
        
        return auth_data
    except Exception as e:
        # print(f"getaccesstoken-error: {str(e)}")
        raise ValueError(f"getimapcredentials-error: {e}") 
        return None
    

async def getsmtpcredentials(emailaddress: str):
    try:
        statekey = f"{REDIS_SMTP_AUTH_CRED_PREFIX}{emailaddress}"
        statedata = await redis_client.get(statekey)
        if not statedata:
            raise ValueError("Unable to retrieve smtp data f. err.frm-rds")
        
        # auth_data = EmailServer(**json.loads(statedata))
        auth_data = EmailServer.model_validate(json.loads(statedata))
        
        return auth_data
    except Exception as e:
        # print(f"getaccesstoken-error: {str(e)}")
        raise ValueError(f"getsmtpcredentials-error: {e}") 
        return None
    



def extract_text_from_html(html_content: str) -> str:
    """Extract plain text from HTML content."""
    if not html_content:
        return ""
    
    # Check if content looks like HTML
    if not ('<' in html_content and '>' in html_content):
        return html_content
    
    # Remove script and style elements completely
    html_content = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove HTML comments
    html_content = re.sub(r'<!--.*?-->', '', html_content, flags=re.DOTALL)
    
    # Replace common block elements with newlines
    block_elements = ['div', 'p', 'br', 'h[1-6]', 'li', 'tr', 'td', 'th']
    for element in block_elements:
        html_content = re.sub(f'</?{element}[^>]*>', '\n', html_content, flags=re.IGNORECASE)
    
    # Remove all remaining HTML tags
    html_content = re.sub(r'<[^>]+>', '', html_content)
    
    # Decode HTML entities
    html_content = unescape(html_content)
    
    # Clean up whitespace
    lines = [line.strip() for line in html_content.split('\n')]
    lines = [line for line in lines if line]  # Remove empty lines
    
    return '\n'.join(lines)

def format_email_page_response(response: EmailPageResponse) -> str:
    """Format EmailPageResponse as human-readable text."""
    output = f"Page {response.page}\n"
    output += f"Page Size: {response.page_size}\n"
    output += f"Total Emails: {response.total}\n"
    
    if response.before:
        output += f"Before: {response.before}\n"
    if response.since:
        output += f"Since: {response.since}\n"
    if response.subject:
        output += f"Subject Filter: {response.subject}\n"
    if response.body:
        output += f"Body Filter: {response.body}\n"
    if response.text:
        output += f"Text Filter: {response.text}\n"
    
    output += "\nEmails:\n"
    
    for i, email in enumerate(response.emails, 1):
        output += f"{i}. Subject: {email.subject}\n"
        output += f"   UID: {email.uid}\n"
        output += f"   From: {email.sender}\n"
        output += f"   Date: {email.date}\n"
        
        # Extract plain text from potentially HTML body
        clean_body = extract_text_from_html(email.body)
        
        # Limit body preview to 200 characters
        # body_preview = clean_body[:200] + "..." if len(clean_body) > 200 else clean_body
        # output += f"   Body: {body_preview}\n"

        output += f"   Body: {clean_body}\n"
        
        if email.attachments:
            output += f"   Attachments: {', '.join(email.attachments)}\n"
        output += "\n"
    
    if not response.emails:
        output += "No emails found.\n"
    
    return output



async def get_last_seen_uid(emailaddress: str, systemid: str = None):
    """Retrieve last seen UID from Redis"""
    redis_key = f"{REDIS_IMAP_AUTH_CRED_PREFIX}{emailaddress}"
    
    existing_data = await redis_client.get(redis_key)
    if existing_data:
        # If existing_data is bytes, decode it; if string, use as-is
        data_str = existing_data.decode('utf-8') if isinstance(existing_data, bytes) else existing_data
        cred_data = json.loads(data_str)
        
        if systemid:
            # Get UID for specific system
            return cred_data.get("systems", {}).get(systemid, {}).get("last_seen_uid", 0)
        else:
            # Get global UID (backward compatibility)
            return cred_data.get("last_seen_uid", 0)
    return 0

async def update_last_seen_uid(emailaddress: str, uid: int, systemid: str = None):
    """Update last seen UID in Redis"""
    redis_key = f"{REDIS_IMAP_AUTH_CRED_PREFIX}{emailaddress}"
    
    # Get existing data or create new
    existing_data = await redis_client.get(redis_key)
    if existing_data:
        data_str = existing_data.decode('utf-8') if isinstance(existing_data, bytes) else existing_data
        cred_data = json.loads(data_str)
    else:
        cred_data = {}
    
    if systemid:
        # Store UID for specific system
        if "systems" not in cred_data:
            cred_data["systems"] = {}
        if systemid not in cred_data["systems"]:
            cred_data["systems"][systemid] = {}
        cred_data["systems"][systemid]["last_seen_uid"] = uid
    else:
        # Store global UID (backward compatibility)
        cred_data["last_seen_uid"] = uid
    
    await redis_client.set(redis_key, json.dumps(cred_data))