import mailbox
import email
from email.header import decode_header
from bs4 import BeautifulSoup
from datetime import datetime
import hashlib
import asyncio
from sqlalchemy.orm import Session
from database import SessionLocal, init_db
from models import Email, EmailThread
from vector_store import VectorStore
from config import Settings
import email.utils
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = Settings()
vector_store = VectorStore(settings)


def decode_header_value(value):
    """Safely decode email header values"""
    if value is None:
        return ""
    if isinstance(value, bytes):
        try:
            return value.decode()
        except UnicodeDecodeError:
            return value.decode("latin1")
    return str(value)


def parse_email_message(msg):
    """Parse email message into structured format"""
    try:
        # Get subject
        subject_header = decode_header(msg.get("subject", "No Subject"))[0]
        subject = decode_header_value(subject_header[0])

        # Get sender
        from_header = decode_header(msg.get("from", "Unknown"))[0]
        from_addr = decode_header_value(from_header[0])

        # Parse date
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
                        html_content = part.get_payload(decode=True).decode("latin1")
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

        # Generate message ID if not present
        message_id = msg.get("message-id", "")
        if not message_id:
            message_id = f"<{hashlib.md5(content.encode()).hexdigest()}@generated>"

        return {
            "message_id": message_id,
            "subject": subject,
            "sender": from_addr,
            "content": content or "No content",
            "html_content": html_content,
            "received_date": received_date,
            "thread_id": thread_id,
        }
    except Exception as e:
        logger.error(f"Error parsing email: {str(e)}")
        return None


async def process_email(email_data: dict, db: Session):
    """Process a single email and add it to the database"""
    try:
        # Create embedding
        embedding_id = await vector_store.add_text(
            email_data["content"],
            metadata={
                "subject": email_data["subject"],
                "thread_id": email_data["thread_id"],
            },
        )

        # Create or update thread
        thread = (
            db.query(EmailThread)
            .filter(EmailThread.thread_id == email_data["thread_id"])
            .first()
        )

        if not thread:
            thread = EmailThread(
                thread_id=email_data["thread_id"],
                subject=email_data["subject"],
                last_updated=email_data["received_date"],
            )
            db.add(thread)
            db.flush()
        else:
            thread.last_updated = email_data["received_date"]
            thread.email_count += 1

        # Create email record
        email_record = Email(
            message_id=email_data["message_id"],
            subject=email_data["subject"],
            sender=email_data["sender"],
            recipient="topics@googlegroups.com",
            content=email_data["content"],
            html_content=email_data["html_content"],
            received_date=email_data["received_date"],
            thread_id=email_data["thread_id"],
            embedding_id=embedding_id,
            is_processed=True,
        )

        db.add(email_record)
        return email_record

    except Exception as e:
        logger.error(f"Error processing email: {str(e)}")
        return None


async def import_mbox(mbox_path: str, limit: int = 300):
    """Import emails from mbox file"""
    try:
        # Initialize database
        init_db()

        # Open mbox file
        mbox = mailbox.mbox(mbox_path)

        # Get total number of messages
        total_messages = len(mbox)
        start_index = max(0, total_messages - limit)

        logger.info(f"Found {total_messages} messages, importing last {limit} messages")

        # Create database session
        db = SessionLocal()

        try:
            processed_count = 0
            for i in range(start_index, total_messages):
                message = mbox[i]

                # Parse email
                email_data = parse_email_message(message)
                if not email_data:
                    continue

                # Check if email already exists
                existing_email = (
                    db.query(Email)
                    .filter(Email.message_id == email_data["message_id"])
                    .first()
                )

                if existing_email:
                    logger.info(
                        f"Email {email_data['message_id']} already exists, skipping"
                    )
                    continue

                # Process email
                email_record = await process_email(email_data, db)
                if email_record:
                    processed_count += 1
                    if processed_count % 10 == 0:
                        logger.info(f"Processed {processed_count} emails")
                        db.commit()  # Commit every 10 emails

            db.commit()
            logger.info(f"Successfully imported {processed_count} emails")

        except Exception as e:
            db.rollback()
            logger.error(f"Error during import: {str(e)}")
            raise
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error opening mbox file: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(import_mbox("../topics.mbox"))
