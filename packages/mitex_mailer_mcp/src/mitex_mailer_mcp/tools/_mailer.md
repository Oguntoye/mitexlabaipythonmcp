import base64
import logging
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

import inflection
from jinja2 import Template

from ..core.helper import (
    check_credentials_exist,
    format_email_page_response,
    get_user_auto_reply_rules, 
    store_user_auto_reply_rules,
    get_user_email_template,
    get_user_email_templates,
    init_email_handler,
    store_email_settings,
    store_user_email_templates,
)
from ..core.schemas import AutoReplyRule, EmailSettings
from ..server import server

logger = logging.getLogger(__name__)


@server.tool()
async def send_email(
    user_mailer_key: str,
    recipients: List[str],
    subject: str,
    body: str,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    attachments: Optional[List[str]] = None,
) -> str:
    """
    Send an email to specified recipients with optional attachments.

    This tool allows sending emails with attachments provided as data URIs.
    Attachments should be in the format: "data:mime/type;filename=name;base64,data"

    Args:
        user_mailer_key (str): Unique identifier for the user's email configuration
        recipients (List[str]): List of email addresses to send to
        subject (str): Email subject line
        body (str): Email body content
        cc (Optional[List[str]]): Optional list of CC recipients
        bcc (Optional[List[str]]): Optional list of BCC recipients
        attachments (Optional[List[str]]): Optional list of data URIs for attachments

    Returns:
        str: A success message indicating the email was sent
    """
    if not await check_credentials_exist(user_mailer_key):
        logger.info(f"No credentials for user {user_mailer_key}")
        return "Error: No email credentials found for user. Please configure email settings first."

    handler = await init_email_handler(user_mailer_key)
    if not handler:
        return "Error: Failed to initialize email handler."

    try:
        processed_attachments = []
        if attachments:
            for attachment_uri in attachments:
                try:
                    if not attachment_uri.startswith("data:"):
                        continue

                    # Extract mime type, filename, and base64 data
                    header, data = attachment_uri.split(",", 1)
                    mime_info = header[5:]  # Remove "data:"

                    if ";filename=" in mime_info:
                        mime_type, filename_part = mime_info.split(";filename=")
                        filename = filename_part
                    else:
                        mime_type = mime_info
                        filename = "attachment"

                    # Decode base64 data
                    attachment_data = base64.b64decode(data)

                    processed_attachments.append(
                        {
                            "filename": filename,
                            "content": attachment_data,
                            "mime_type": mime_type,
                        }
                    )

                except Exception as attach_error:
                    logger.error(
                        f"src.mitex_mailer_mcp.tools.mailer.send_email:: Error processing attachment: {str(attach_error)}"
                    )
                    continue

        await handler.send_email(
            recipients, subject, body, cc, bcc, processed_attachments
        )
        attachment_info = (
            f" with {len(processed_attachments)} attachment(s)"
            if processed_attachments
            else ""
        )
        return f"Email sent successfully to {', '.join(recipients)}{attachment_info}"
    except Exception as e:
        logger.error(
            f"src.mitex_mailer_mcp.tools.mailer.send_email:: Error sending email for user {user_mailer_key}: {str(e)}"
        )
        return "Failed to send email. Please check your email settings and try again."


@server.tool()
async def send_template_email(
    user_mailer_key: str,
    template_name: str,
    recipients: List[str],
    variables: Optional[Dict[str, str]] = None,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    attachments: Optional[List[str]] = None,
) -> str:
    """
    Send an email using a predefined template with optional attachments.

    This tool allows sending templated emails with attachments provided as data URIs.
    Attachments should be in the format: "data:mime/type;filename=name;base64,data"

    Args:
        user_mailer_key (str): Unique identifier for the user's email configuration
        template_name (str): Name of the email template to use. e.g Welcome Email
        recipients (List[str]): List of email addresses to send to
        variables (Optional[Dict[str, str]]): Dictionary of variables to substitute in the template
        cc (Optional[List[str]]): Optional list of CC recipients
        bcc (Optional[List[str]]): Optional list of BCC recipients
        attachments (Optional[List[str]]): Optional list of data URIs for attachments

    Returns:
        str: A success message indicating the email was sent based off the template
    """
    if not await check_credentials_exist(user_mailer_key):
        logger.info(f"No credentials for user {user_mailer_key}")
        return "Error: No email credentials found for user. Please configure email settings first."

    handler = await init_email_handler(user_mailer_key)
    if not handler:
        return "Error: Failed to initialize email handler."

    try:

        template_key = inflection.underscore(template_name)
        template_data = await get_user_email_template(user_mailer_key, template_key)

        if not template_data:
            return f"Error: Template '{template_name}' not found."

        variables = variables or {}
        subject_template = Template(template_data["subject"])
        body_template = Template(template_data["body"])

        rendered_subject = subject_template.render(**variables)
        rendered_body = body_template.render(**variables)

        processed_attachments = []
        if attachments:
            for attachment_uri in attachments:
                try:
                    if not attachment_uri.startswith("data:"):
                        continue

                    header, data = attachment_uri.split(",", 1)
                    mime_info = header[5:]  # Remove "data:"

                    if ";filename=" in mime_info:
                        mime_type, filename_part = mime_info.split(";filename=")
                        filename = filename_part
                    else:
                        mime_type = mime_info
                        filename = "attachment"

                    attachment_data = base64.b64decode(data)

                    processed_attachments.append(
                        {
                            "filename": filename,
                            "content": attachment_data,
                            "mime_type": mime_type,
                        }
                    )

                except Exception as attach_error:
                    logger.error(
                        f"src.mitex_mailer_mcp.tools.mailer.send_template_email:: Error processing attachment: {str(attach_error)}"
                    )
                    continue

        await handler.send_email(
            recipients, rendered_subject, rendered_body, cc, bcc, processed_attachments
        )
        attachment_info = (
            f" with {len(processed_attachments)} attachment(s)"
            if processed_attachments
            else ""
        )
        return f"Template email sent successfully to {', '.join(recipients)}{attachment_info}"
    except Exception as e:
        logger.error(
            f"src.mitex_mailer_mcp.tools.mailer.send_template_email:: Error sending template email for user {user_mailer_key}: {str(e)}"
        )
        return "Failed to send template email. Please check your template and settings."


@server.tool()
async def create_email_template(
    user_mailer_key: str,
    name: str,
    subject: str,
    body: str,
    variables: Optional[List[str]] = None,
) -> str:
    """
    Create a new email template.

    Args:
        user_mailer_key (str): Unique identifier for the user's email configuration
        name (str): Template name e.g. "Welcome Email"
        subject (str): Template subject with optional variables
        body (str): Template body that is either plain text or HTML with optional variables in this format: {{variable_name}}
        variables (Optional[List[str]]): List of variable names used in the template

    Returns:
        str: A success message that confirms the creation of the template
    """
    try:
        variables = variables or []
        template_data = {
            "name": name,
            "subject": subject,
            "body": body,
            "variables": variables,
        }
        template_key = inflection.underscore(name)

        templates_dict = {}

        templates_dict[template_key] = template_data

        user_templates = await get_user_email_templates(user_mailer_key)

        if user_templates is not None:
            templates_dict.update(user_templates)

        await store_user_email_templates(user_mailer_key, templates_dict)

        return f"Template '{name}' created successfully with variables: {', '.join(variables)}"
    except Exception as e:
        logger.error(
            f"src.mitex_mailer_mcp.tools.mailer.create_email_template:: Error creating template for user {user_mailer_key}: {str(e)}"
        )
        return "Failed to create email template. Please try again."


@server.tool()
async def update_email_template(
    user_mailer_key: str,
    name: str,
    subject: Optional[str] = None,
    body: Optional[str] = None,
    variables: Optional[List[str]] = None,
) -> str:
    """
    Update an existing email template.

    Args:
        user_mailer_key (str): Unique identifier for the user's email configuration
        name (str): Template name to update e.g. "Welcome Email"
        subject (Optional[str]): New template subject with optional variables
        body (Optional[str]): New template body that is either plain text or HTML with optional variables in this format: {{variable_name}}. e.g. "Hello {{name}}, welcome!"
        variables (Optional[List[str]]): New list of variable names used in the template

    Returns:
        str: A success message that confirms the update of the template
    """
    try:
        template_key = inflection.underscore(name)
        user_templates = await get_user_email_templates(user_mailer_key)

        if not user_templates or template_key not in user_templates:
            return f"Error: Template '{name}' not found."

        if subject is not None:
            user_templates[template_key]["subject"] = subject
        if body is not None:
            user_templates[template_key]["body"] = body
        if variables is not None:
            user_templates[template_key]["variables"] = variables

        await store_user_email_templates(user_mailer_key, user_templates)

        return f"Template '{name}' updated successfully."
    except Exception as e:
        logger.error(
            f"src.mitex_mailer_mcp.tools.mailer.update_email_template:: Error updating template for user {user_mailer_key}: {str(e)}"
        )
        return "Failed to update email template. Please try again."


@server.tool()
async def delete_email_template(
    user_mailer_key: str,
    name: str,
) -> str:
    """
    Delete an existing email template.

    Args:
        user_mailer_key (str): Unique identifier for the user's email configuration
        name (str): Template name to delete e.g. "Welcome Email"

    Returns:
        str: A success message that confirms the deletion of the template
    """
    try:
        template_key = inflection.underscore(name)
        user_templates = await get_user_email_templates(user_mailer_key)

        if not user_templates or template_key not in user_templates:
            return f"Error: Template '{name}' not found."

        del user_templates[template_key]

        await store_user_email_templates(user_mailer_key, user_templates)

        return f"Template '{name}' deleted successfully."
    except Exception as e:
        logger.error(
            f"src.mitex_mailer_mcp.tools.mailer.delete_email_template:: Error deleting template for user {user_mailer_key}: {str(e)}"
        )
        return "Failed to delete email template. Please try again."


@server.tool()
async def list_email_templates(user_mailer_key: str) -> str:
    """
    List all email templates for the user.

    Args:
        user_mailer_key (str): Unique identifier for the user's email configuration

    Returns:
        str: A list of all email templates
    """
    try:
        user_templates = await get_user_email_templates(user_mailer_key)

        if not user_templates:
            return "No email templates found."

        output = "Email Templates:\n"
        for _, template_data in user_templates.items():
            output += f"- {template_data['name']}\n"
            output += f"  Variables: {', '.join(template_data['variables']) if template_data['variables'] else 'None'}\n"
            output += f"  Subject Preview: {template_data['subject'][:50]}...\n\n"
            output += f"  Body Preview: {template_data['body'][:100]}...\n\n"

        return output
    except Exception as e:
        logger.error(
            f"src.mitex_mailer_mcp.tools.mailer.list_email_templates:: Error listing templates for user {user_mailer_key}: {str(e)}"
        )
        return "Failed to list email templates. Please try again."


@server.tool()
async def configure_email_settings(
    user_mailer_key: str,
    account_name: str,
    email_address: str,
    imap_host: str,
    imap_user: str,
    imap_password: str,
    smtp_host: str,
    smtp_user: str,
    smtp_password: str,
    full_name: str = "Mitex Mailer",
    imap_port: int = 993,
    imap_ssl: bool = True,
    smtp_port: int = 465,
    smtp_ssl: bool = True,
    smtp_start_ssl: bool = False,
) -> str:
    """
    Configure email settings for SMTP and IMAP operations.

    Args:
        user_mailer_key (str): Unique identifier for the user's email configuration
        account_name (str): Name for this email account
        email_address (str): Your email address
        imap_host (str): IMAP server hostname
        imap_user (str): IMAP username
        imap_password (str): IMAP password
        smtp_host (str): SMTP server hostname
        smtp_user (str): SMTP username
        smtp_password (str): SMTP password
        full_name (str): Your full name for email signatures. Defaults to "Mitex Mailer".
        imap_port (int): IMAP server port. Defaults to 993.
        imap_ssl (bool): Whether to use SSL for IMAP. Defaults to True.
        smtp_port (int): SMTP server port. Defaults to 465.
        smtp_ssl (bool): Whether to use SSL for SMTP. Defaults to True.
        smtp_start_ssl (bool): Whether to use STARTTLS for SMTP. Defaults to False.

    Returns:
        str: A success message that confirms the email settings were configured
    """
    try:
        email_settings = EmailSettings.from_params(
            account_name=account_name,
            full_name=full_name,
            email_address=email_address,
            user_name=imap_user,
            password=imap_password,
            imap_host=imap_host,
            smtp_host=smtp_host,
            imap_port=imap_port,
            imap_ssl=imap_ssl,
            smtp_port=smtp_port,
            smtp_ssl=smtp_ssl,
            smtp_start_ssl=smtp_start_ssl,
            smtp_password=smtp_password,
            smtp_user_name=smtp_user,
        )

        success = await store_email_settings(user_mailer_key, email_settings)
        if not success:
            return "Error: Failed to store email settings."

        await init_email_handler(user_mailer_key)
        return f"Email settings configured successfully for user '{user_mailer_key}'. You can now use email tools."
    except Exception as e:
        logger.error(
            f"src.mitex_mailer_mcp.tools.mailer.configure_email_settings:: Error configuring email settings for user {user_mailer_key}: {str(e)}"
        )
        return "Failed to configure email settings. Please check your configuration and try again."


@server.tool()
async def get_mailer_status(user_mailer_key: str) -> str:
    """
    Check if email handler is properly configured and ready to use.

    Args:
        user_mailer_key (str): Unique identifier for the user's email configuration

    Returns:
        str: A status message
    """
    if not await check_credentials_exist(user_mailer_key):
        logger.info(f"No credentials for user {user_mailer_key}")
        return f"No email credentials configured for user. Please use configure_email_settings first."

    handler = await init_email_handler(user_mailer_key)
    if not handler:
        return "Failed to initialize email handler."

    return f"Email handler is ready for user '{user_mailer_key}'. You can send and receive emails."


@server.tool()
async def test_email_connection(user_mailer_key: str) -> str:
    """
    Test the email connection by attempting to connect to both IMAP and SMTP servers.

    Args:
        user_mailer_key (str): Unique identifier for the user's email configuration

    Returns:
        str: Connection test results
    """
    if not await check_credentials_exist(user_mailer_key):
        logger.info(f"No email credentials configured for user {user_mailer_key}.")
        return f"No email credentials configured for user. Please use configure_email_settings first."

    handler = await init_email_handler(user_mailer_key)
    if not handler:
        return "Failed to initialize email handler."

    try:
        imap_count = await handler.incoming_client.get_email_count()
        return f"Email connection successful for user. Found {imap_count} emails in inbox."
    except Exception as e:
        logger.error(
            f"src.mitex_mailer_mcp.tools.mailer.test_email_connection:: Error testing email connection for user {user_mailer_key}: {str(e)}"
        )
        return "Email connection test failed. Please check your email settings."


@server.tool()
async def get_emails(
    user_mailer_key: str,
    page: int = 1,
    page_size: int = 10,
    before: Optional[datetime] = None,
    since: Optional[datetime] = None,
    subject: Optional[str] = None,
    body: Optional[str] = None,
    text: Optional[str] = None,
    from_address: Optional[str] = None,
    to_address: Optional[str] = None,
    order: Literal["asc", "desc"] = "desc",
    unread: bool = False,
) -> str:
    """
    Retrieve emails from the inbox with optional filtering.

    Args:
        user_mailer_key: Unique identifier for the user's email configuration
        page (int): Page number for pagination (1-based). Defaults to 1.
        page_size (int): Number of emails per page. Defaults to 10.
        before (Optional[datetime]): Only emails before this date
        since (Optional[datetime]): Only emails after this date
        subject (Optional[str]): Filter by subject containing this text
        body (Optional[str]): Filter by body containing this text
        text (Optional[str]): Filter by any field containing this text
        from_address (Optional[str]): Filter by sender email
        to_address (Optional[str]): Filter by recipient email
        order (str): Sort order ('asc' or 'desc')
        unread (bool): If True, only return unread emails

    Returns:
        str: Formatted email data
    """
    if not await check_credentials_exist(user_mailer_key):
        logger.info(f"No credentials for user {user_mailer_key}")
        return f"No email credentials configured for user. Please configure email settings first."

    handler = await init_email_handler(user_mailer_key)
    if not handler:
        return "Failed to initialize email handler."

    try:
        result = await handler.get_emails(
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
        return format_email_page_response(result)
    except Exception as e:
        logger.error(f"src.mitex_mailer_mcp.tools.mailer.get_emails:: Error retrieving emails for user {user_mailer_key}: {str(e)}")
        return (
            "Failed to retrieve emails. Please check your email settings and try again."
        )


@server.tool()
async def get_email_count(
    user_mailer_key: str,
    before: Optional[datetime] = None,
    since: Optional[datetime] = None,
    subject: Optional[str] = None,
    body: Optional[str] = None,
    text: Optional[str] = None,
    from_address: Optional[str] = None,
    to_address: Optional[str] = None,
    unread: bool = False,
) -> str:
    """
    Get the count of emails matching the specified criteria.

    Args:
        user_mailer_key: Unique identifier for the user's email configuration
        before (Optional[datetime]): Only emails before this date
        since (Optional[datetime]): Only emails after this date
        subject (Optional[str]): Filter by subject containing this text
        body (Optional[str]): Filter by body containing this text
        text (Optional[str]): Filter by any field containing this text
        from_address (Optional[str]): Filter by sender email
        to_address (Optional[str]): Filter by recipient email
        unread (bool): If True, only count unread emails

    Returns:
        str: Count of matching emails and sample emails
    """
    if not await check_credentials_exist(user_mailer_key):
        logger.info(f"No credentials for user {user_mailer_key}")
        return "No email credentials configured for user. Please configure email settings first."

    handler = await init_email_handler(user_mailer_key)
    if not handler:
        return "Failed to initialize email handler."

    try:
        count = await handler.incoming_client.get_email_count(
            before=before,
            since=since,
            subject=subject,
            body=body,
            text=text,
            from_address=from_address,
            to_address=to_address,
            unread=unread,
        )
        if count == 0:
            return "Found 0 emails matching the criteria."

        display_count = min(10, count)
        result = await handler.get_emails(
            page=1,
            page_size=display_count,
            before=before,
            since=since,
            subject=subject,
            body=body,
            text=text,
            from_address=from_address,
            to_address=to_address,
            order="desc",
            unread=unread,
        )
        formatted_emails = format_email_page_response(result)
        return f"Found {count} emails matching the criteria.\n\n{formatted_emails}"
    except Exception as e:
        logger.error(f"src.mitex_mailer_mcp.tools.mailer.get_email_count:: Error counting emails for user {user_mailer_key}: {str(e)}")
        return "Failed to count emails. Please check your email settings and try again."


@server.tool()
async def search_emails(
    user_mailer_key: str,
    query: str,
    page: int = 1,
    page_size: int = 10,
    order: Literal["asc", "desc"] = "desc",
) -> str:
    """
    Search emails by text content.

    Args:
        user_mailer_key: Unique identifier for the user's email configuration
        query (str): Search query to match against email content
        page (int): Page number for pagination (1-based)
        page_size (int): Number of emails per page
        order (Literal["asc", "desc"]): Sort order ('asc' or 'desc')

    Returns:
        str: A message containing matching emails
    """
    if not await check_credentials_exist(user_mailer_key):
        logger.info(f"No credentials for user {user_mailer_key}")
        return "No email credentials configured for user. Please configure email settings first."

    handler = await init_email_handler(user_mailer_key)
    if not handler:
        return "Failed to initialize email handler."

    try:
        result = await handler.get_emails(
            page=page, page_size=page_size, text=query, order=order
        )
        return format_email_page_response(result)
    except Exception as e:
        logger.error(f"src.mitex_mailer_mcp.tools.mailer.search_emails:: Error searching emails for user {user_mailer_key}: {str(e)}")
        return (
            "Failed to search emails. Please check your email settings and try again."
        )





@server.tool()
async def get_recent_emails(
    user_mailer_key: str, count: int = 10, since: Optional[datetime] = None
) -> str:
    """
    Get the most recent emails from the inbox.

    Args:
        user_mailer_key: Unique identifier for the user's email configuration
        count (int): Number of recent emails to retrieve. Defaults to 10.
        since (Optional[datetime]): Only emails after this date

    Returns:
        str: A message containing recent emails
    """
    if not await check_credentials_exist(user_mailer_key):
        logger.info(f"No credentials for user {user_mailer_key}")
        return "No email credentials configured for user. Please configure email settings first."

    handler = await init_email_handler(user_mailer_key)
    if not handler:
        return "Failed to initialize email handler."

    try:
        result = await handler.get_emails(
            page=1, page_size=count, since=since, order="desc"
        )
        return format_email_page_response(result)
    except Exception as e:
        logger.error(
            f"src.mitex_mailer_mcp.tools.mailer.get_recent_emails:: Error retrieving recent emails for user {user_mailer_key}: {str(e)}"
        )
        return "Failed to retrieve recent emails. Please check your email settings and try again."


@server.tool()
async def get_unread_emails(
    user_mailer_key: str, page: int = 1, page_size: int = 10
) -> str:
    """
    Get unread emails from the inbox.

    Args:
        user_mailer_key (str): Unique identifier for the user's email configuration
        page (int): Page number for pagination (1-based). Defaults to 1.
        page_size (int): Number of emails per page. Defaults to 10.

    Returns:
        str: Formatted unread emails
    """
    if not await check_credentials_exist(user_mailer_key):
        logger.info(f"No credentials for user {user_mailer_key}")
        return "No email credentials configured for user. Please configure email settings first."

    handler = await init_email_handler(user_mailer_key)
    if not handler:
        return "Failed to initialize email handler."

    try:
        result = await handler.get_emails(
            page=page, page_size=page_size, order="desc", unread=True
        )
        return format_email_page_response(result)
    except Exception as e:
        logger.error(
            f"src.mitex_mailer_mcp.tools.mailer.get_unread_emails:: Error retrieving unread emails for user {user_mailer_key}: {str(e)}"
        )
        return "Failed to retrieve unread emails. Please check your email settings and try again."


@server.tool()
async def mark_emails_as_read(user_mailer_key: str, message_ids: list[str]) -> str:
    """
    Mark specified emails as read.

    Args:
        user_mailer_key (str): Unique identifier for the user's email configuration
        message_ids (list[str]): List of message UIDs to mark as read

    Returns:
        str: Success message
    """
    if not await check_credentials_exist(user_mailer_key):
        logger.error(
            f"src.mitex_mailer_mcp.tools.mailer.mark_emails_as_read:: No email credentials configured for user_mailer_key '{user_mailer_key}'."
        )
        return f"No email credentials configured for user. Please configure email settings first."

    handler = await init_email_handler(user_mailer_key)
    if not handler:
        return "Failed to initialize email handler."

    try:
        await handler.mark_emails_as_read(message_ids)
        return f"Marked {len(message_ids)} emails as read."
    except Exception as e:
        logger.error(
            f"src.mitex_mailer_mcp.tools.mailer.mark_emails_as_read:: Error marking emails as read for user {user_mailer_key}: {str(e)}"
        )
        return "Failed to mark emails as read. Please check your email settings and try again."


@server.tool()
async def mark_emails_as_unread(user_mailer_key: str, message_ids: list[str]) -> str:
    """
    Mark specified emails as unread.

    Args:
        user_mailer_key (str): Unique identifier for the user's email configuration
        message_ids (list[str]): List of message UIDs to mark as unread

    Returns:
        str: Success message
    """
    if not await check_credentials_exist(user_mailer_key):
        logger.error(
            f"src.mitex_mailer_mcp.tools.mailer.mark_emails_as_unread:: No email credentials configured for user_mailer_key '{user_mailer_key}'."
        )
        return f"No email credentials configured for user_mailer_key. Please configure email settings first."

    handler = await init_email_handler(user_mailer_key)
    if not handler:
        return "Failed to initialize email handler."

    try:
        await handler.mark_emails_as_unread(message_ids)
        return f"Marked {len(message_ids)} emails as unread."
    except Exception as e:
        logger.error(
            f"Error marking emails as unread for user {user_mailer_key}: {str(e)}"
        )
        return "Failed to mark emails as unread. Please check your email settings and try again."








@server.tool()
async def create_auto_reply_rule(
    user_mailer_key: str,
    name: str,
    conditions: Dict[str, Any],
    reply_subject: str,
    reply_body: str,
    mark_as_read: bool = True,
    template_name: Optional[str] = None,
    variables: Optional[Dict[str, str]] = None,
) -> str:
    """
    Create an auto-reply rule that responds to incoming emails matching specific conditions.

    Args:
        user_mailer_key (str): Unique identifier for the user's email configuration
        name (str): Name for this auto-reply rule
        conditions (Dict[str, Any]): Conditions to match emails. Supported keys:
            - from_address: Exact email address match
            - subject_contains: Text that must be in subject
            - body_contains: Text that must be in body
            - subject_regex: Regex pattern for subject
            - body_regex: Regex pattern for body
        reply_subject (str): Subject line for the auto-reply
        reply_body (str): Body content for the auto-reply
        mark_as_read (bool): Whether to mark the original email as read after replying. Defaults to True.
        template_name (Optional[str]): Name of email template to use instead of reply_subject/reply_body
        variables (Optional[Dict[str, str]]): Variables for template rendering

    Returns:
        str: Success message
    """
    try:
        rule = AutoReplyRule(
            name=name,
            conditions=conditions,
            reply_subject=reply_subject,
            reply_body=reply_body,
            mark_as_read=mark_as_read,
            template_name=template_name,
            variables=variables or {},
        )

        rule_key = inflection.underscore(name)
        rules = await get_user_auto_reply_rules(user_mailer_key) or {}
        rules[rule_key] = rule

        success = await store_user_auto_reply_rules(user_mailer_key, rules)
        if not success:
            return "Error: Failed to store auto-reply rule."

        return f"Auto-reply rule '{name}' created successfully."
    except Exception as e:
        logger.error(
            f"Error creating auto-reply rule for user {user_mailer_key}: {str(e)}"
        )
        return "Failed to create auto-reply rule. Please try again."


@server.tool()
async def update_auto_reply_rule(
    user_mailer_key: str,
    name: str,
    conditions: Optional[Dict[str, Any]] = None,
    reply_subject: Optional[str] = None,
    reply_body: Optional[str] = None,
    enabled: Optional[bool] = None,
    mark_as_read: Optional[bool] = None,
    template_name: Optional[str] = None,
    variables: Optional[Dict[str, str]] = None,
) -> str:
    """
    Update an existing auto-reply rule.

    Args:
        user_mailer_key (str): Unique identifier for the user's email configuration
        name (str): Name of the auto-reply rule to update
        conditions (Optional[Dict[str, Any]]): New conditions to match emails
        reply_subject (Optional[str]): New subject line for the auto-reply
        reply_body (Optional[str]): New body content for the auto-reply
        enabled (Optional[bool]): Whether the rule is enabled
        mark_as_read (Optional[bool]): Whether to mark emails as read after replying
        template_name (Optional[str]): Name of email template to use
        variables (Optional[Dict[str, str]]): Variables for template rendering

    Returns:
        str: Success message
    """
    try:
        rules = await get_user_auto_reply_rules(user_mailer_key)
        if not rules:
            return "No auto-reply rules found."

        rule_key = name.lower().replace(" ", "_")
        if rule_key not in rules:
            return f"Auto-reply rule '{name}' not found."

        rule = rules[rule_key]

        if conditions is not None:
            rule.conditions = conditions
        if reply_subject is not None:
            rule.reply_subject = reply_subject
        if reply_body is not None:
            rule.reply_body = reply_body
        if enabled is not None:
            rule.enabled = enabled
        if mark_as_read is not None:
            rule.mark_as_read = mark_as_read
        if template_name is not None:
            rule.template_name = template_name
        if variables is not None:
            rule.variables = variables

        success = await store_user_auto_reply_rules(user_mailer_key, rules)
        if not success:
            return "Error: Failed to update auto-reply rule."

        return f"Auto-reply rule '{name}' updated successfully."
    except Exception as e:
        logger.error(
            f"Error updating auto-reply rule for user {user_mailer_key}: {str(e)}"
        )
        return "Failed to update auto-reply rule. Please try again."


@server.tool()
async def delete_auto_reply_rule(user_mailer_key: str, name: str) -> str:
    """
    Delete an auto-reply rule.

    Args:
        user_mailer_key (str): Unique identifier for the user's email configuration
        name (str): Name of the auto-reply rule to delete

    Returns:
        str: Success message
    """
    try:
        rules = await get_user_auto_reply_rules(user_mailer_key)
        if not rules:
            return "No auto-reply rules found."

        rule_key = name.lower().replace(" ", "_")
        if rule_key not in rules:
            return f"Auto-reply rule '{name}' not found."

        del rules[rule_key]

        success = await store_user_auto_reply_rules(user_mailer_key, rules)
        if not success:
            return "Error: Failed to delete auto-reply rule."

        return f"Auto-reply rule '{name}' deleted successfully."
    except Exception as e:
        logger.error(
            f"Error deleting auto-reply rule for user {user_mailer_key}: {str(e)}"
        )
        return "Failed to delete auto-reply rule. Please try again."


@server.tool()
async def list_auto_reply_rules(user_mailer_key: str) -> str:
    """
    List all auto-reply rules for the user.

    Args:
        user_mailer_key (str): Unique identifier for the user's email configuration

    Returns:
        str: List of auto-reply rules
    """
    try:
        rules = await get_user_auto_reply_rules(user_mailer_key)

        if not rules:
            return "No auto-reply rules found."

        output = "Auto-Reply Rules:\n"
        for rule_key, rule in rules.items():
            output += f"- {rule.name} ({'Enabled' if rule.enabled else 'Disabled'})\n"
            output += f"  Conditions: {rule.conditions}\n"
            if rule.template_name:
                output += f"  Template: {rule.template_name}\n"
            else:
                output += f"  Reply Subject: {rule.reply_subject}\n"
            output += f"  Mark as Read: {rule.mark_as_read}\n\n"

        return output
    except Exception as e:
        logger.error(
            f"Error listing auto-reply rules for user {user_mailer_key}: {str(e)}"
        )
        return "Failed to list auto-reply rules. Please try again."


@server.tool()
async def process_auto_replies(user_mailer_key: str) -> str:
    """
    Process auto-replies for all unread emails that match configured rules.

    Args:
        user_mailer_key (str): Unique identifier for the user's email configuration

    Returns:
        str: Processing results
    """
    if not await check_credentials_exist(user_mailer_key):
        logger.info(f"No email credentials configured for user {user_mailer_key}.")
        return f"No email credentials configured for user. Please configure email settings first."

    handler = await init_email_handler(user_mailer_key)
    if not handler:
        return "Failed to initialize email handler."

    try:
        from ..core.helper import process_auto_replies

        return await process_auto_replies(user_mailer_key, handler)
    except Exception as e:
        logger.error(
            f"src.mitex_mailer_mcp.tools.mailer.process_auto_replies:: Error processing auto-replies for user {user_mailer_key}: {str(e)}"
        )
        return "Failed to process auto-replies. Please try again."


@server.tool()
async def enable_auto_reply_rule(user_mailer_key: str, name: str) -> str:
    """
    Enable an auto-reply rule.

    Args:
        user_mailer_key (str): Unique identifier for the user's email configuration
        name (str): Name of the auto-reply rule to enable

    Returns:
        str: Success message
    """
    try:
        rules = await get_user_auto_reply_rules(user_mailer_key)
        if not rules:
            return "No auto-reply rules found."

        rule_key = inflection.underscore(name)
        if rule_key not in rules:
            return f"Auto-reply rule '{name}' not found."

        rules[rule_key].enabled = True

        success = await store_user_auto_reply_rules(user_mailer_key, rules)
        if not success:
            return "Error: Failed to enable auto-reply rule."

        return f"Auto-reply rule '{name}' enabled successfully."
    except Exception as e:
        logger.error(
            f"src.mitex_mailer_mcp.tools.mailer.enable_auto_reply_rule:: Error enabling auto-reply rule for user {user_mailer_key}: {str(e)}"
        )
        return "Failed to enable auto-reply rule. Please try again."


@server.tool()
async def disable_auto_reply_rule(user_mailer_key: str, name: str) -> str:
    """
    Disable an auto-reply rule.

    Args:
        user_mailer_key (str): Unique identifier for the user's email configuration
        name (str): Name of the auto-reply rule to disable

    Returns:
        str: Success message
    """
    try:

        rules = await get_user_auto_reply_rules(user_mailer_key)
        if not rules:
            return "No auto-reply rules found."

        rule_key = inflection.underscore(name)
        if rule_key not in rules:
            return f"Auto-reply rule '{name}' not found."

        rules[rule_key].enabled = False

        success = await store_user_auto_reply_rules(user_mailer_key, rules)
        if not success:
            return "Error: Failed to disable auto-reply rule."

        return f"Auto-reply rule '{name}' disabled successfully."
    except Exception as e:
        logger.error(
            f"src.mitex_mailer_mcp.tools.mailer.disable_auto_reply_rule:: Error disabling auto-reply rule for user {user_mailer_key}: {str(e)}"
        )
        return "Failed to disable auto-reply rule. Please try again."
