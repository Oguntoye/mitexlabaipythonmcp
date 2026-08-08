import email.utils
import logging
from collections.abc import AsyncGenerator
from datetime import datetime
from email.encoders import encode_base64
from email.header import Header
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.parser import BytesParser
from email.policy import default
from typing import Any
import aiosmtplib

from .schemas import EmailServer


logger = logging.getLogger(__name__)


class SMTPClient:
    """Dedicated SMTP client for sending emails with context manager support."""
    
    def __init__(self, email_server: EmailServer, sender: str | None = None, timeout: float = 120):
        self.email_server = email_server
        self.sender = sender or email_server.user_name
        self.timeout = timeout  # Default 2 minutes
        self.smtp_client = None

    async def __aenter__(self):
        """Async context manager entry - connect to SMTP server."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - disconnect from SMTP server."""
        await self.disconnect()
        return False  # Don't suppress exceptions

    async def connect(self):
        """Connect and authenticate with SMTP server."""
        if self.smtp_client:
            return self.smtp_client
            
        try:
            self.smtp_client = aiosmtplib.SMTP(
                hostname=self.email_server.host,
                port=self.email_server.port,
                start_tls=self.email_server.start_ssl,
                use_tls=self.email_server.use_ssl,
                timeout=self.timeout,  # Add timeout parameter
            )
            
            # Connect to server
            await self.smtp_client.connect()
            
            # Authenticate
            await self.smtp_client.login(
                self.email_server.user_name, 
                self.email_server.password
            )
            
            return self.smtp_client
            
        except Exception as e:
            logger.error(f"SMTP connection failed: {e}")
            self.smtp_client = None
            raise

    async def disconnect(self):
        """Disconnect from SMTP server."""
        if self.smtp_client:
            try:
                await self.smtp_client.quit()
            except Exception as e:
                logger.error(f"Error disconnecting from SMTP: {e}")
            finally:
                self.smtp_client = None

    async def test_connection(self) -> bool:
        """Test SMTP connection and authentication (using existing connection if available)."""
        try:
            # if not self.smtp_client:
            #     await self.connect()
            
            # Send NOOP to test connection
            await self.smtp_client.noop()
            return True
            
        except Exception as e:
            logger.error(f"SMTP connection test failed: {e}")
            return False

    # async def send_email(
    #     self,
    #     recipients: list[str],
    #     subject: str,
    #     body: str,
    #     cc: list[str] | None = None,
    #     bcc: list[str] | None = None,
    #     attachments: list[dict] | None = None,
    # ):
    #     """Send an email with optional CC, BCC, and attachments."""
    #     # if not self.smtp_client:
    #     #     await self.connect()
            
    #     try:
    #         # Create message
    #         if attachments:
    #             msg = MIMEMultipart()
    #             text_part = MIMEText(body, "plain", "utf-8")
    #             msg.attach(text_part)
    #         else:
    #             msg = MIMEText(body, "plain", "utf-8")

    #         # Set headers with proper encoding
    #         if any(ord(c) > 127 for c in subject):
    #             msg["Subject"] = str(Header(subject, "utf-8"))
    #         else:
    #             msg["Subject"] = subject

    #         if any(ord(c) > 127 for c in self.sender):
    #             msg["From"] = str(Header(self.sender, "utf-8"))
    #         else:
    #             msg["From"] = self.sender

    #         msg["To"] = ", ".join(recipients)

    #         if cc:
    #             msg["Cc"] = ", ".join(cc)

    #         # Add attachments
    #         if attachments:
    #             for attachment in attachments:
    #                 filename = attachment.get("filename", "attachment")
    #                 content = attachment.get("content", b"")
    #                 mime_type = attachment.get("mime_type", "application/octet-stream")

    #                 part = MIMEBase(*mime_type.split("/"))
    #                 part.set_payload(content)
    #                 encode_base64(part)
    #                 part.add_header(
    #                     "Content-Disposition", f"attachment; filename={filename}"
    #                 )
    #                 msg.attach(part)

    #         # Send email using existing connection
    #         all_recipients = recipients.copy()
    #         if cc:
    #             all_recipients.extend(cc)
    #         if bcc:
    #             all_recipients.extend(bcc)

    #         await self.smtp_client.send_message(msg, recipients=all_recipients)

    #     except Exception as e:
    #         logger.error(f"Error sending email: {e}")
    #         raise

    async def send_email(
        self,
        recipients: list[str],
        subject: str,
        body: str,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        attachments: list[dict] | None = None,
        content_type: str = "plain",  # Add content_type parameter,
        custom_headers: dict | None = None
    ):
        """Send an email with optional CC, BCC, and attachments."""
        # if not self.smtp_client:
        #     await self.connect()
        
        try:
            # Detect HTML content automatically if not specified
            if content_type == "plain" and ("<" in body and ">" in body):
                content_type = "html"
                
            # Create message
            if attachments:
                msg = MIMEMultipart()
                text_part = MIMEText(body, content_type, "utf-8")  # Use content_type
                msg.attach(text_part)
            else:
                msg = MIMEText(body, content_type, "utf-8")        # Use content_type

            # Set headers with proper encoding
            if any(ord(c) > 127 for c in subject):
                msg["Subject"] = str(Header(subject, "utf-8"))
            else:
                msg["Subject"] = subject

            if any(ord(c) > 127 for c in self.sender):
                msg["From"] = str(Header(self.sender, "utf-8"))
            else:
                msg["From"] = self.sender

            msg["To"] = ", ".join(recipients)

            if cc:
                msg["Cc"] = ", ".join(cc)

            if custom_headers:
                for key, value in custom_headers.items():
                    msg[key] = value

            # Add attachments
            if attachments:
                for attachment in attachments:
                    filename = attachment.get("filename", "attachment")
                    content = attachment.get("content", b"")
                    mime_type = attachment.get("mime_type", "application/octet-stream")

                    part = MIMEBase(*mime_type.split("/"))
                    part.set_payload(content)
                    encode_base64(part)
                    part.add_header(
                        "Content-Disposition", f"attachment; filename={filename}"
                    )
                    msg.attach(part)

            # Send email using existing connection
            all_recipients = recipients.copy()
            if cc:
                all_recipients.extend(cc)
            if bcc:
                all_recipients.extend(bcc)

            await self.smtp_client.send_message(msg, recipients=all_recipients)

        except Exception as e:
            logger.error(f"Error sending email: {e}")
            raise

    
    async def send_multiple_emails(self, emails: list[dict]):
        """Send multiple emails using the same connection for efficiency."""
        # if not self.smtp_client:
        #     await self.connect()
            
        for email_data in emails:
            try:
                await self.send_email(**email_data)
            except Exception as e:
                logger.error(f"Failed to send email to {email_data.get('recipients', [])}: {e}")
                # Continue with next email instead of failing all