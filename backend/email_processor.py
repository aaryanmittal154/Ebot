from imapclient import IMAPClient
import email
from email.header import decode_header
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Optional, Union
import hashlib
from sqlalchemy.orm import Session
import email.utils
import logging
from fastapi import HTTPException

from models import Email, EmailThread
from vector_store import VectorStore
from config import Settings


class EmailProcessor:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.vector_store = VectorStore(settings)

    async def connect_to_imap(self) -> IMAPClient:
        """Establish IMAP connection"""
        try:
            server = IMAPClient(
                self.settings.imap_server,
                port=self.settings.imap_port,
                use_uid=True,
                ssl=True,
            )
            server.login(self.settings.email_address, self.settings.email_password)
            return server
        except Exception as e:
            logging.error(f"Failed to connect to IMAP server: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Failed to connect to email server: {str(e)}"
            )

    def decode_header_value(self, value: Union[str, bytes, None]) -> str:
        """Safely decode email header values"""
        if value is None:
            return ""
        if isinstance(value, bytes):
            try:
                return value.decode()
            except UnicodeDecodeError:
                return value.decode("latin1")
        return str(value)

    def parse_email_message(self, msg) -> dict:
        """Parse email message into structured format"""
        try:
            # Get subject
            subject_header = decode_header(msg.get("subject", "No Subject"))[0]
            subject = self.decode_header_value(subject_header[0])

            # Get sender
            from_header = decode_header(msg.get("from", "Unknown"))[0]
            from_addr = self.decode_header_value(from_header[0])

            # Parse date with email.utils for better compatibility
            date_str = msg.get(
                "date", datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")
            )
            try:
                received_date = datetime.fromtimestamp(
                    email.utils.mktime_tz(email.utils.parsedate_tz(date_str))
                )
            except Exception:
                received_date = datetime.utcnow()

            # Get email content
            content = ""
            html_content = None

            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        try:
                            content = part.get_payload(decode=True).decode()
                        except UnicodeDecodeError:
                            content = part.get_payload(decode=True).decode("latin1")
                    elif part.get_content_type() == "text/html":
                        try:
                            html_content = part.get_payload(decode=True).decode()
                        except UnicodeDecodeError:
                            html_content = part.get_payload(decode=True).decode(
                                "latin1"
                            )
            else:
                try:
                    content = msg.get_payload(decode=True).decode()
                except UnicodeDecodeError:
                    content = msg.get_payload(decode=True).decode("latin1")

            if html_content:
                # Extract text from HTML
                soup = BeautifulSoup(html_content, "html.parser")
                if not content:  # Only use HTML content if we don't have plain text
                    content = soup.get_text(separator=" ", strip=True)

            # Generate thread ID based on normalized subject
            clean_subject = "".join(e for e in subject if e.isalnum()).lower()
            thread_id = hashlib.md5(clean_subject.encode()).hexdigest()

            return {
                "subject": subject,
                "sender": from_addr,
                "content": content or "No content",
                "html_content": html_content,
                "received_date": received_date,
                "thread_id": thread_id,
            }
        except Exception as e:
            logging.error(f"Error parsing email: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Error parsing email: {str(e)}"
            )

    async def process_new_emails(self, db: Session) -> List[Email]:
        """Process new emails from IMAP server"""
        try:
            server = await self.connect_to_imap()
            server.select_folder("INBOX")

            # Search for unprocessed emails
            messages = server.search(["NOT", "FLAGGED"])
            if not messages:
                return []

            processed_emails = []

            for uid, message_data in server.fetch(messages, ["RFC822"]).items():
                try:
                    email_message = email.message_from_bytes(message_data[b"RFC822"])
                    parsed_email = self.parse_email_message(email_message)

                    # Create embedding
                    embedding_id = await self.vector_store.add_text(
                        parsed_email["content"],
                        metadata={
                            "subject": parsed_email["subject"],
                            "thread_id": parsed_email["thread_id"],
                        },
                    )

                    # Create or update thread
                    thread = (
                        db.query(EmailThread)
                        .filter(EmailThread.thread_id == parsed_email["thread_id"])
                        .first()
                    )

                    if not thread:
                        thread = EmailThread(
                            thread_id=parsed_email["thread_id"],
                            subject=parsed_email["subject"],
                            last_updated=parsed_email["received_date"],
                        )
                        db.add(thread)
                        db.flush()  # Ensure thread is created before email
                    else:
                        thread.last_updated = parsed_email["received_date"]
                        thread.email_count += 1

                    # Create email record
                    email_record = Email(
                        message_id=str(uid),
                        subject=parsed_email["subject"],
                        sender=parsed_email["sender"],
                        recipient=self.settings.email_address,
                        content=parsed_email["content"],
                        html_content=parsed_email["html_content"],
                        received_date=parsed_email["received_date"],
                        thread_id=parsed_email["thread_id"],
                        embedding_id=embedding_id,
                        is_processed=True,
                    )

                    db.add(email_record)
                    processed_emails.append(email_record)

                    # Mark as processed in IMAP
                    server.add_flags(uid, ["\\Flagged"])

                except Exception as e:
                    logging.error(f"Error processing email {uid}: {str(e)}")
                    continue

            db.commit()
            server.logout()

            return processed_emails

        except Exception as e:
            db.rollback()
            logging.error(f"Error in process_new_emails: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Error processing emails: {str(e)}"
            )
