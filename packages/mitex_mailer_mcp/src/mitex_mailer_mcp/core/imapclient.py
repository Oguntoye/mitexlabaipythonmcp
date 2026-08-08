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

import aioimaplib 
import aiosmtplib
from collections.abc import AsyncGenerator
import asyncio

from .schemas import EmailServer

logger = logging.getLogger(__name__)


class IMAPClient:
    """Dedicated IMAP client for receiving emails with context manager support."""
    
    def __init__(self, email_server: EmailServer):
        self.email_server = email_server
        self.imap_client = None
        
        self.imap_class = (
            aioimaplib.IMAP4_SSL if self.email_server.use_ssl else aioimaplib.IMAP4
        )

    async def __aenter__(self):
        """Async context manager entry - connect to IMAP server."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - disconnect from IMAP server."""
        await self.disconnect()
        return False  # Don't suppress exceptions

    async def connect(self):
        """Connect and login to IMAP server."""
        if self.imap_client:
            return self.imap_client
            
        self.imap_client = self.imap_class(
            host=self.email_server.host,
            port=self.email_server.port
        )
        
        # Wait for the connection to be established
        await self.imap_client.wait_hello_from_server()
        
        # Login and wait for completion
        login_response = await self.imap_client.login(
            self.email_server.user_name, 
            self.email_server.password
        )
        
        # Verify login was successful
        if login_response.result != 'OK':
            raise Exception(f"Login failed: {login_response.result}")
            
        return self.imap_client

    async def disconnect(self):
        """Disconnect from IMAP server."""
        if self.imap_client:
            try:
                await self.imap_client.logout()
            except Exception as e:
                logger.error(f"Error logging out from IMAP: {e}")
            finally:
                self.imap_client = None

    async def select_folder(self, folder='INBOX'):
        """Select a mailbox folder."""
        if not self.imap_client:
            await self.connect()
        
        # Check if we have a valid connection by trying to select
        try:
            select_response = await self.imap_client.select(folder)
            if select_response.result != 'OK':
                raise Exception(f"Failed to select folder {folder}: {select_response.result}")
            logger.debug(f"Successfully selected folder: {folder}")
        except Exception as e:
            logger.error(f"Error selecting folder {folder}: {e}")
            raise

    def _parse_email_data(self, raw_email: bytes, uid: str) -> dict[str, Any]:
        """Parse raw email data into a structured dictionary."""
        parser = BytesParser(policy=default)
        email_message = parser.parsebytes(raw_email)

        subject = email_message.get("Subject", "")
        sender = email_message.get("From", "")
        date_str = email_message.get("Date", "")

        try:
            date_tuple = email.utils.parsedate_tz(date_str)
            date = (
                datetime.fromtimestamp(email.utils.mktime_tz(date_tuple))
                if date_tuple
                else datetime.now()
            )
        except Exception:
            date = datetime.now()

        body = ""
        attachments = []

        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))

                if "attachment" in content_disposition:
                    filename = part.get_filename()
                    if filename:
                        attachments.append(filename)
                elif content_type == "text/plain":
                    body_part = part.get_payload(decode=True)
                    if body_part and isinstance(body_part, bytes):
                        charset = part.get_content_charset("utf-8")
                        try:
                            body += body_part.decode(charset)
                        except UnicodeDecodeError:
                            body += body_part.decode("utf-8", errors="replace")
        else:
            payload = email_message.get_payload(decode=True)
            if payload and isinstance(payload, bytes):
                charset = email_message.get_content_charset("utf-8")
                try:
                    body = payload.decode(charset)
                except UnicodeDecodeError:
                    body = payload.decode("utf-8", errors="replace")

        return {
            "subject": subject,
            "from": sender,
            "body": body,
            "date": date,
            "attachments": attachments,
            "uid": uid,
        }

    @staticmethod
    def _build_search_criteria(
        before: datetime | None = None,
        since: datetime | None = None,
        subject: str | None = None,
        body: str | None = None,
        text: str | None = None,
        from_address: str | None = None,
        to_address: str | None = None,
        unread: bool = False,
    ):
        """Build IMAP search criteria."""
        search_criteria = []
        if before:
            search_criteria.extend(["BEFORE", before.strftime("%d-%b-%Y").upper()])
        if since:
            search_criteria.extend(["SINCE", since.strftime("%d-%b-%Y").upper()])
        if subject:
            search_criteria.extend(["SUBJECT", subject])
        if body:
            search_criteria.extend(["BODY", body])
        if text:
            search_criteria.extend(["TEXT", text])
        if from_address:
            search_criteria.extend(["FROM", from_address])
        if to_address:
            search_criteria.extend(["TO", to_address])
        if unread:
            search_criteria.append("UNSEEN")

        if not search_criteria:
            search_criteria = ["ALL"]

        return search_criteria

    # async def get_emails_stream(
    #     self,
    #     page: int = 1,
    #     page_size: int = 10,
    #     before: datetime | None = None,
    #     since: datetime | None = None,
    #     subject: str | None = None,
    #     body: str | None = None,
    #     text: str | None = None,
    #     from_address: str | None = None,
    #     to_address: str | None = None,
    #     order: str = "desc",
    #     unread: bool = False,
    #     uid_start: int | None = None,  # Add this parameter
    # ) -> AsyncGenerator[dict[str, Any], None]:
    #     """Stream emails based on search criteria."""
    #     await self.select_folder("INBOX")

    #     try:
    #         search_criteria = self._build_search_criteria(
    #             before, since, subject, body, text, from_address, to_address, unread
    #         )

    #         _, messages = await self.imap_client.uid_search(*search_criteria)

    #         if not messages or not messages[0]:
    #             message_ids = []
    #         else:
    #             message_ids = messages[0].split()

    #         start = (page - 1) * page_size
    #         end = start + page_size

    #         if order == "desc":
    #             message_ids.reverse()

    #         for message_id in message_ids[start:end]:
    #             try:
    #                 message_id_str = message_id.decode("utf-8")

    #                 # Try different fetch formats for compatibility
    #                 fetch_formats = ["RFC822", "BODY[]", "BODY.PEEK[]", "(BODY.PEEK[])"]
    #                 raw_email = None

    #                 for fetch_format in fetch_formats:
    #                     try:
    #                         _, data = await self.imap_client.uid("fetch", message_id_str, fetch_format)
                            
    #                         if data and len(data) > 1 and isinstance(data[1], bytearray):
    #                             raw_email = bytes(data[1])
    #                             break
    #                     except Exception:
    #                         continue

    #                 if raw_email:
    #                     try:
    #                         parsed_email = self._parse_email_data(raw_email, message_id_str)
    #                         yield parsed_email
    #                     except Exception as e:
    #                         logger.error(f"Error parsing email data: {e}")

    #             except Exception as e:
    #                 logger.error(f"Error fetching email: {e}")

    #     except Exception as e:
    #         logger.error(f"Error in get_emails_stream: {e}")
    #         raise



    async def get_emails_stream(
        self,
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
        uid_start: int | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream emails based on search criteria."""
        await self.select_folder("INBOX")

        try:
            if uid_start:
                # Use UID-based search - follow same pattern as _build_search_criteria
                search_criteria = [f"{uid_start + 1}:*"]
                _, messages = await self.imap_client.uid_search(*search_criteria)
                # print(f"UID search criteria: {search_criteria}")
                # print(f"messages:{messages}")
            else:
                # Use regular search criteria
                search_criteria = self._build_search_criteria(
                    before, since, subject, body, text, from_address, to_address, unread
                )
                _, messages = await self.imap_client.uid_search(*search_criteria)

            if not messages or not messages[0]:
                message_ids = []
            else:
                message_ids = messages[0].split()

            start = (page - 1) * page_size
            end = start + page_size

            if order == "desc":
                message_ids.reverse()

            for message_id in message_ids[start:end]:
                try:
                    message_id_str = message_id.decode("utf-8")

                    # Try different fetch formats for compatibility
                    fetch_formats = ["RFC822", "BODY[]", "BODY.PEEK[]", "(BODY.PEEK[])"]
                    raw_email = None

                    for fetch_format in fetch_formats:
                        try:
                            _, data = await self.imap_client.uid("fetch", message_id_str, fetch_format)
                            
                            if data and len(data) > 1 and isinstance(data[1], bytearray):
                                raw_email = bytes(data[1])
                                break
                        except Exception:
                            continue

                    if raw_email:
                        try:
                            parsed_email = self._parse_email_data(raw_email, message_id_str)
                            yield parsed_email
                        except Exception as e:
                            logger.error(f"Error parsing email data: {e}")

                except Exception as e:
                    logger.error(f"Error fetching email: {e}")

        except Exception as e:
            logger.error(f"Error in get_emails_stream: {e}")
            raise


    async def get_email_count(
        self,
        before: datetime | None = None,
        since: datetime | None = None,
        subject: str | None = None,
        body: str | None = None,
        text: str | None = None,
        from_address: str | None = None,
        to_address: str | None = None,
        unread: bool = False,
    ) -> int:
        """Get count of emails matching search criteria."""
        await self.select_folder("INBOX")

        search_criteria = self._build_search_criteria(
            before, since, subject, body, text, from_address, to_address, unread
        )
        _, messages = await self.imap_client.uid_search(*search_criteria)
        
        if not messages or not messages[0]:
            return 0
        return len(messages[0].split())

    async def mark_emails_as_read(self, message_ids: list[str]):
        """Mark emails as read by setting the \\Seen flag."""
        await self.select_folder("INBOX")

        for msg_id in message_ids:
            try:
                await self.imap_client.uid("STORE", msg_id, "+FLAGS", r"\\Seen")
            except Exception as e:
                logger.error(f"Error marking email {msg_id} as read: {e}")

    async def mark_emails_as_unread(self, message_ids: list[str]):
        """Mark emails as unread by removing the \\Seen flag."""
        await self.select_folder("INBOX")

        for msg_id in message_ids:
            try:
                await self.imap_client.uid("STORE", msg_id, "-FLAGS", r"\\Seen")
            except Exception as e:
                logger.error(f"Error marking email {msg_id} as unread: {e}")

    async def idle_forever(self):
        """Listen for new incoming mails in real-time using IMAP IDLE."""
        await self.select_folder("INBOX")

        while True:
            logger.info("Entering IDLE mode...")
            try:
                idle = await self.imap_client.idle_start(timeout=60 * 5)  # 5 min max

                while True:
                    try:
                        response = await self.imap_client.wait_server_push()
                        if response:
                            logger.debug(f"Server push: {response}")

                            # Response is a list of lines, not an object with .lines
                            for line in response:
                                if b"EXISTS" in line:
                                    logger.info("📩 New mail detected!")
                                    # Handle new mail here
                                    await self._handle_new_mail()
                                    break
                                elif b"EXPUNGE" in line:
                                    logger.info("📧 Mail deleted")
                                    break

                    except asyncio.TimeoutError:
                        logger.debug("IDLE timed out, restarting...")
                        break
                    except Exception as e:
                        logger.error(f"Idle wait error: {e}")
                        break

            except Exception as e:
                logger.error(f"Idle start error: {e}")
            finally:
                # Always properly exit IDLE mode
                try:
                    done_result = self.imap_client.idle_done()
                    if done_result:  # Check if it returns a coroutine
                        await done_result
                except Exception as e:
                    logger.error(f"Error exiting IDLE: {e}")
            
            # Brief pause before restarting IDLE
            await asyncio.sleep(1)

    async def _handle_new_mail(self):
        """Handle new incoming mail."""
        try:
            # Exit IDLE mode first
            done_result = self.imap_client.idle_done()
            if done_result:
                await done_result
            
            # Brief pause to allow server to process
            await asyncio.sleep(0.1)
            
            # Get the latest email
            async for email in self.get_emails_stream(page=1, page_size=1):
                logger.info(f"📧 New email: {email['subject']} from {email['from']}")
                # Add your mail processing logic here
                break
                
        except Exception as e:
            logger.error(f"Error handling new mail: {e}")
        
        # Restart IDLE mode
        try:
            await self.imap_client.idle_start(timeout=60 * 5)
        except Exception as e:
            logger.error(f"Error restarting IDLE: {e}")
            raise  # Let the outer loop handle reconnection