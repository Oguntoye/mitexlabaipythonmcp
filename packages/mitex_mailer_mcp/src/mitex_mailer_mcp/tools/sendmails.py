import base64
import logging
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
import aiohttp
import base64
import mimetypes
from urllib.parse import urlparse
from pathlib import Path
from jinja2 import Template
import asyncio
import inflection

from ..server import server
from ..core.helper import getimapcredentials, getsmtpcredentials
from ..core.smtpclient import SMTPClient

logger = logging.getLogger(__name__)


async def process_data_uri(attachment_uri: str) -> dict:
    """Process data URI attachment."""
    header, data = attachment_uri.split(",", 1)
    mime_info = header[5:]  # Remove "data:"
    
    if ";filename=" in mime_info:
        mime_type, filename = mime_info.split(";filename=", 1)
    else:
        mime_type = mime_info
        filename = "attachment"
    
    return {
        "filename": filename,
        "content": base64.b64decode(data),
        "mime_type": mime_type,
    }


async def process_url_attachment(attachment_uri: str) -> dict:
    """Download and process URL attachment."""
    timeout = aiohttp.ClientTimeout(total=30, connect=10)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(attachment_uri) as response:
            if response.status != 200:
                raise ValueError(f"HTTP {response.status}")
            
            # Check file size
            content_length = response.headers.get('Content-Length')
            if content_length and int(content_length) > 25 * 1024 * 1024:
                raise ValueError(f"File too large ({content_length} bytes)")
            
            attachment_data = await response.read()
            
            # Extract filename
            content_disposition = response.headers.get('Content-Disposition')
            if content_disposition and 'filename=' in content_disposition:
                filename = content_disposition.split('filename=')[1].strip('"')
            else:
                parsed_url = urlparse(attachment_uri)
                filename = Path(parsed_url.path).name or "downloaded_file"
            
            # Determine mime type
            mime_type = response.headers.get('Content-Type')
            if not mime_type:
                mime_type, _ = mimetypes.guess_type(filename)
                mime_type = mime_type or "application/octet-stream"
            
            return {
                "filename": filename,
                "content": attachment_data,
                "mime_type": mime_type,
            }


async def process_attachment(attachment_uri: str) -> dict | None:
    """Process a single attachment (data URI or URL)."""
    try:
        if attachment_uri.startswith("data:"):
            return await process_data_uri(attachment_uri)
        
        elif attachment_uri.startswith(("http://", "https://")):
            print(f"Processing: {attachment_uri}")
            return await process_url_attachment(attachment_uri)
        
        else:
            logger.error(f"Unsupported attachment format: {attachment_uri}")
            return None
            
    except asyncio.TimeoutError:
        logger.error(f"Download timeout: {attachment_uri}")
        print(f"TIMEOUT: {attachment_uri} took too long")
        return None
    except aiohttp.ClientError as e:
        logger.error(f"Download failed: {attachment_uri} - {e}")
        print(f"DOWNLOAD ERROR: {attachment_uri} - {e}")
        return None
    except Exception as e:
        logger.error(f"Error processing {attachment_uri}: {e}")
        return None




@server.tool()
async def send_email(
    emailaddress: str,
    recipients: List[str],
    subject: str,
    body: str,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    attachments: Optional[List[str]] = None,
    custom_headers: Optional[dict] = None
) -> str:
    """
    Send an email to specified recipients with optional attachments.

    This tool allows sending emails with attachments provided as data URIs or URLs.
    - Data URIs should be in format: "data:mime/type;filename=name;base64,data"
    - URLs will be downloaded and converted automatically

    Args:
        emailaddress (str): Unique identifier for the user's email configuration
        recipients (List[str]): List of email addresses to send to
        subject (str): Email subject line
        body (str): Email body content
        cc (Optional[List[str]]): Optional list of CC recipients
        bcc (Optional[List[str]]): Optional list of BCC recipients
        attachments (Optional[List[str]]): Optional list of data URIs or URLs for attachments

    Returns:
        str: A success message indicating the email was sent
    """
    smtpauthdata = await getsmtpcredentials(emailaddress=emailaddress)
    if not smtpauthdata:
        raise ValueError("Unable to retrieve SMTP auth data")

    try:
        # Process attachments
        processed_attachments = []
        if attachments:
            # Process all attachments concurrently
            attachment_results = await asyncio.gather(
                *[process_attachment(uri) for uri in attachments],
                return_exceptions=True
            )
            
            # Filter successful results
            processed_attachments = [
                result for result in attachment_results 
                if isinstance(result, dict)
            ]

        # Send email
        async with SMTPClient(smtpauthdata, timeout=180) as client:
            await client.send_email(
                recipients, subject, body, cc, bcc, processed_attachments, custom_headers=custom_headers
            )

        attachment_info = (
            f" with {len(processed_attachments)} attachment(s)"
            if processed_attachments else ""
        )
        return f"Email sent successfully to {', '.join(recipients)}{attachment_info}"
        
    except Exception as e:
        logger.error(f"Error sending email for {emailaddress}: {e}")
        return "Failed to send email. Please check your email settings and try again."
    

# if __name__ == "__main__":
#     result = asyncio.run( send_email(
#         emailaddress="user@example.com",
#         recipients=["recipient@example.com"],
#         subject="Testing email",
#         body="<p>Hello</p> <b>World</b>",
#         # attachments=[
#         #     "https://res.cloudinary.com/tribapay/image/upload/v1673269687/xi8pxm0tcrl7wzkanvgt.jpg",
#         #     "https://res.cloudinary.com/tribapay/image/upload/v1756330478/Screenshot_2025-08-27_at_22.27.39_picvex.png"
#         # ]
#         # fullname="Rankloid",
#         # password="xxxxxxxxxxxx",
#         # smtp_host="smtp.gmail.com",
#         # smtp_port=587
#     ))
#     print(f"result:{result}")
