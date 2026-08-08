from datetime import datetime, timedelta
import logging
from typing import Any, Dict, Literal, Optional
from ..server import server
from ..core.schemas import EmailPageResponse, EmailData
from ..core.helper import getimapcredentials, format_email_page_response, extract_text_from_html, get_last_seen_uid, update_last_seen_uid
from ..core.imapclient import IMAPClient
from ..server import server
import asyncio
logger = logging.getLogger(__name__)


async def get_emailsfnx(
    emailaddress: str,
    page: int = 1,
    page_size: int = 10,
    before: datetime | None = None,
    since: datetime | None = None,
    subject: str | None = None,
    body: str | None = None,
    text: str | None = None,
    from_address: str | None = None,
    to_address: str | None = None,
    order: str = "desc",
    unread: bool = False,
    uid_start: int | None = None,  # Add this parameter
) -> EmailPageResponse:

    imapauthdata = await getimapcredentials(emailaddress=emailaddress)
    if not imapauthdata:
        raise ValueError("Unable to retrieve imap auth data")

    # Use context manager for automatic connection management
    async with IMAPClient(imapauthdata) as client:
        emails = []
        async for email_data in client.get_emails_stream(
            page,
            page_size,
            before,
            since,
            subject,
            body,
            text,
            from_address,
            to_address,
            order,
            unread,
            uid_start,  # Pass it down
        ):
            emails.append(EmailData.from_email(email_data))
        
        total = await client.get_email_count(
            before, since, subject, body, text, from_address, to_address, unread
        )
    
    # Connection automatically closed here
    return EmailPageResponse(
        page=page,
        page_size=page_size,
        before=before,
        since=since,
        subject=subject,
        body=body,
        text=text,
        emails=emails,
        total=total,
    )


@server.tool()
async def get_emails_with_textoutput(
    emailaddress: str,
    page: int = 1,
    page_size: int = 10,
    before: datetime | None = None,
    since: datetime | None = None,
    subject: str | None = None,
    body: str | None = None,
    text: str | None = None,
    from_address: str | None = None,
    to_address: str | None = None,
    order: str = "desc",
    unread: bool = False,
) -> str:
    """
    Get the count of emails matching the specified criteria.

    Args:
        emailaddress: Unique identifier for the user's email configuration
        before (Optional[datetime]): Only emails before this date
        since (Optional[datetime]): Only emails after this date
        subject (Optional[str]): Filter by subject containing this text
        body (Optional[str]): Filter by body containing this text
        text (Optional[str]): Filter by any field containing this text
        from_address (Optional[str]): Filter by sender email
        to_address (Optional[str]): Filter by recipient email
        unread (bool): If True, only count unread emails

    Returns:
        dict: Count of matching emails and sample emails
    """
    try:
        # Use get_emails to do the heavy lifting
        result = await get_emailsfnx(
            emailaddress=emailaddress,
            page=page,
            page_size=page_size, 
            before=before,
            since=since,
            subject=subject,
            body=body,
            text=text,
            from_address=from_address,
            to_address=to_address,
            order=order,
            unread=unread,
        )
        
        if result.total == 0:
            return "Found 0 emails matching the criteria."
        
        formatted_emails = format_email_page_response(result)
        return f"Found {result.total} emails matching the criteria.\n\n{formatted_emails}"
       
    except ValueError as e:
        logger.error(f"Auth error for user {emailaddress}: {str(e)}")
        return "Unable to retrieve email credentials. Please check your email settings."
    except Exception as e:
        logger.error(f"Error counting emails for user {emailaddress}: {str(e)}")
        return "Failed to count emails. Please check your email settings and try again."



@server.tool()
async def get_emails_with_jsonoutput(
    emailaddress: str,
    page: int = 1,
    page_size: int = 10,
    before: datetime | None = None,
    since: datetime | None = None,
    subject: str | None = None,
    body: str | None = None,
    text: str | None = None,
    from_address: str | None = None,
    to_address: str | None = None,
    order: str = "desc",
    unread: bool = False,
) -> dict[str, Any]:
    """
    Get the count of emails matching the specified criteria.

    Args:
        emailaddress: Unique identifier for the user's email configuration
        before (Optional[datetime]): Only emails before this date
        since (Optional[datetime]): Only emails after this date
        subject (Optional[str]): Filter by subject containing this text
        body (Optional[str]): Filter by body containing this text
        text (Optional[str]): Filter by any field containing this text
        from_address (Optional[str]): Filter by sender email
        to_address (Optional[str]): Filter by recipient email
        unread (bool): If True, only count unread emails
    """
    try:
        # Use get_emails to do the heavy lifting
        result = await get_emailsfnx(
            emailaddress=emailaddress,
            page=page,
            page_size=page_size, 
            before=before,
            since=since,
            subject=subject,
            body=body,
            text=text,
            from_address=from_address,
            to_address=to_address,
            order=order,
            unread=unread,
        )
        
        if result.total == 0:
            return {
                "success": False,
                "message":"Found 0 emails matching the criteria."
            }
        
        # return {
        #     "success": True,
        #     "message":"Successfully retrieved",
        #     "data": result
        # }

        # Clean HTML from email bodies
        cleaned_emails = []
        for email in result.emails:
            # Create a copy of the email with cleaned body
            cleaned_email = EmailData(
                subject=email.subject,
                sender=email.sender,
                body=extract_text_from_html(email.body),  # Clean the HTML here
                date=email.date,
                attachments=email.attachments,
                uid=email.uid
            )
            cleaned_emails.append(cleaned_email)
        
        # Create new result with cleaned emails
        cleaned_result = EmailPageResponse(
            page=result.page,
            page_size=result.page_size,
            before=result.before,
            since=result.since,
            subject=result.subject,
            body=result.body,
            text=result.text,
            emails=cleaned_emails,  # Use cleaned emails
            total=result.total,
        )
        
        return {
            "success": True,
            "message": "Successfully retrieved",
            "data": cleaned_result
        }

  
    except ValueError as e:
        logger.error(f"Auth error for user {emailaddress}: {str(e)}")
        return {
            "success": False,
            "message":"Unable to retrieve email credentials. Please check your email settings."
        } 
    except Exception as e:
        logger.error(f"Error counting emails for user {emailaddress}: {str(e)}")
        return {
            "success": False,
            "message":"Failed to count emails. Please check your email settings and try again."
        } 



@server.tool()
async def mark_emails_as_read(emailaddress: str, message_ids: list[str]) -> str:
    """
    Mark specified emails as read.
    
    Args:
        emailaddress (str): Unique identifier for the user's email configuration
        message_ids (list[str]): List of message UIDs to mark as read
    
    Returns:
        str: Success or error message
    """
    if not message_ids:
        return "No message IDs provided. Please specify which emails to mark as read."
    
    try:
        imapauthdata = await getimapcredentials(emailaddress=emailaddress)
        if not imapauthdata:
            return "Unable to retrieve email credentials. Please check your email settings."
        
        # Use context manager for automatic connection management
        async with IMAPClient(imapauthdata) as client:
            await client.mark_emails_as_read(message_ids)
            return f"Successfully marked {len(message_ids)} emails as read."
            
    except ValueError as e:
        logger.error(f"Auth error for user {emailaddress}: {str(e)}")
        return "Unable to retrieve email credentials. Please check your email settings."
    except Exception as e:
        logger.error(f"Error marking emails as read for user {emailaddress}: {str(e)}")
        return "Failed to mark emails as read. Please check your email settings and try again."
    


@server.tool()
async def mark_emails_as_unread(emailaddress: str, message_ids: list[str]) -> str:
    """
    Mark specified emails as unread.
    
    Args:
        emailaddress (str): Unique identifier for the user's email configuration
        message_ids (list[str]): List of message UIDs to mark as unread
    
    Returns:
        str: Success or error message
    """
    if not message_ids:
        return "No message IDs provided. Please specify which emails to mark as unread."
    
    try:
        imapauthdata = await getimapcredentials(emailaddress=emailaddress)
        if not imapauthdata:
            return "Unable to retrieve email credentials. Please check your email settings."
        
        # Use context manager for automatic connection management
        async with IMAPClient(imapauthdata) as client:
            await client.mark_emails_as_unread(message_ids)
            return f"Successfully marked {len(message_ids)} emails as unread."
            
    except ValueError as e:
        logger.error(f"Auth error for user {emailaddress}: {str(e)}")
        return "Unable to retrieve email credentials. Please check your email settings."
    except Exception as e:
        logger.error(f"Error marking emails as unread for user {emailaddress}: {str(e)}")
        return "Failed to mark emails as unread. Please check your email settings and try again."


@server.tool()
async def fetch_recent_emails(emailaddress: str, systemid: str = None,  page_size: int = 10):
    try:
        # Get last seen UID
        last_seen_uid = await get_last_seen_uid(emailaddress, systemid)
        print(f"last_seen_uid:{last_seen_uid}")
        
        # Fetch emails using UID
        result = await get_emailsfnx(
            emailaddress=emailaddress,
            uid_start=last_seen_uid,
            order="desc",
            page_size=page_size
        )
        
        if not result or len(result.emails) == 0:
            return "No new emails found."
        
        # Remove the last seen email if it exists in results
        filtered_emails = [email for email in result.emails if int(email.uid) != last_seen_uid]
        
        if not filtered_emails:
            return "No new emails found."
        
        # Update last seen UID with highest UID from filtered emails
        current_highest_uid = max(int(email.uid) for email in filtered_emails)
        await update_last_seen_uid(emailaddress, current_highest_uid, systemid)
        
        # Update result object with filtered emails
        result.emails = filtered_emails
        result.total = len(filtered_emails)
        
        formatted_emails = format_email_page_response(result)
        return f"Found {result.total} emails matching the criteria.\n\n{formatted_emails}"
        
    except Exception as e:
        logger.error(f"Error fetching emails for user {emailaddress}: {str(e)}")
        return "Error retrieving emails."
    

@server.tool()
async def fetch_recent_emails_with_jsonoutput(emailaddress: str, systemid: str = None,  page_size: int = 10):
    try:
        # Get last seen UID
        last_seen_uid = await get_last_seen_uid(emailaddress, systemid)
        print(f"last_seen_uid:{last_seen_uid}")
        
        # Fetch emails using UID
        result = await get_emailsfnx(
            emailaddress=emailaddress,
            uid_start=last_seen_uid,
            order="desc",
            page_size=page_size
        )
        
        if not result or len(result.emails) == 0:
            # return "No new emails found."
            return {
                "success": False,
                "message":"No new emails found."
            }
        
        # Remove the last seen email if it exists in results
        filtered_emails = [email for email in result.emails if int(email.uid) != last_seen_uid]
        
        if not filtered_emails:
            # return "No new emails found."
            return {
                "success": False,
                "message":"No new emails found."
            }
        
        # Update last seen UID with highest UID from filtered emails
        current_highest_uid = max(int(email.uid) for email in filtered_emails)
        await update_last_seen_uid(emailaddress, current_highest_uid, systemid)
        
        # Update result object with filtered emails
        result.emails = filtered_emails
        result.total = len(filtered_emails)

        # Clean HTML from email bodies
        cleaned_emails = []
        for email in result.emails:
            # Create a copy of the email with cleaned body
            cleaned_email = EmailData(
                subject=email.subject,
                sender=email.sender,
                body=extract_text_from_html(email.body),  # Clean the HTML here
                date=email.date,
                attachments=email.attachments,
                uid=email.uid
            )
            cleaned_emails.append(cleaned_email)


        cleaned_result = EmailPageResponse(
            page=result.page,
            page_size=result.page_size,
            before=result.before,
            since=result.since,
            subject=result.subject,
            body=result.body,
            text=result.text,
            emails=cleaned_emails,  # Use cleaned emails
            total=result.total,
        )
        
        return {
            "success": True,
            "message": "Successfully retrieved",
            "data": cleaned_result
        }


        # formatted_emails = format_email_page_response(result)
        # return f"Found {result.total} emails matching the criteria.\n\n{formatted_emails}"
        
    except Exception as e:
        logger.error(f"Error fetching emails for user {emailaddress}: {str(e)}")
        # return "Error retrieving emails."
        return {
            "success": False,
            "message":"Failed to count emails. Please check your email settings and try again."
        } 
    


# if __name__ == "__main__":
#     result = asyncio.run( fetch_recent_emails_with_jsonoutput(
#         emailaddress="user@example.com",
#         systemid="sys2"
#         # text="tribapay",
#         # page=1,
#         # page_size=5
#         # fullname="Rankloid",
#         # password="xxxxxxxxxxxx",
#         # smtp_host="smtp.gmail.com",
#         # smtp_port=587
#     ))
#     print(f"result:{result}")

