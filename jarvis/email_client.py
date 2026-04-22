"""jarvis.email_client

Email integration for reading and sending emails via IMAP/SMTP.
"""

from __future__ import annotations

import email
import imaplib
import logging
import smtplib
from dataclasses import dataclass
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from jarvis.secure_storage import secure_storage

logger = logging.getLogger(__name__)


@dataclass
class EmailMessage:
    """Email message data class."""
    id: str
    subject: str
    sender: str
    recipient: str
    date: datetime
    body: str
    is_read: bool
    has_attachments: bool


class EmailManager:
    """Manage email operations."""
    
    def __init__(self) -> None:
        self.imap_connection: imaplib.IMAP4_SSL | None = None
        self.smtp_connection: smtplib.SMTP_SSL | None = None
        self.connected_account: str | None = None
    
    def _get_credentials(self) -> dict[str, str] | None:
        """Get email credentials from secure storage."""
        email_addr = secure_storage.get("EMAIL_ADDRESS")
        password = secure_storage.get("EMAIL_PASSWORD")
        imap_server = secure_storage.get("IMAP_SERVER", "imap.gmail.com")
        smtp_server = secure_storage.get("SMTP_SERVER", "smtp.gmail.com")
        
        if not email_addr or not password:
            return None
        
        return {
            "email": email_addr,
            "password": password,
            "imap_server": imap_server,
            "smtp_server": smtp_server,
        }
    
    def connect(self) -> bool:
        """Connect to email server."""
        creds = self._get_credentials()
        if not creds:
            logger.error("Email credentials not configured")
            return False
        
        try:
            # IMAP connection
            self.imap_connection = imaplib.IMAP4_SSL(creds["imap_server"])
            self.imap_connection.login(creds["email"], creds["password"])
            
            self.connected_account = creds["email"]
            logger.info(f"Email connected: {creds['email']}")
            return True
            
        except Exception as e:
            logger.error(f"Email connection failed: {e}")
            return False
    
    def disconnect(self) -> None:
        """Disconnect from email server."""
        if self.imap_connection:
            try:
                self.imap_connection.logout()
            except Exception:
                pass
            self.imap_connection = None
        
        if self.smtp_connection:
            try:
                self.smtp_connection.quit()
            except Exception:
                pass
            self.smtp_connection = None
        
        self.connected_account = None
    
    def read_emails(
        self,
        folder: str = "INBOX",
        limit: int = 10,
        unread_only: bool = False,
    ) -> list[EmailMessage]:
        """Read emails from folder."""
        if not self.imap_connection and not self.connect():
            return []
        
        try:
            self.imap_connection.select(folder)
            
            # Search criteria
            if unread_only:
                _, message_ids = self.imap_connection.search(None, "UNSEEN")
            else:
                _, message_ids = self.imap_connection.search(None, "ALL")
            
            message_ids = message_ids[0].split()
            message_ids = message_ids[-limit:]  # Get most recent
            
            emails = []
            for msg_id in reversed(message_ids):  # Newest first
                try:
                    _, msg_data = self.imap_connection.fetch(msg_id, "(RFC822)")
                    raw_email = msg_data[0][1]
                    email_msg = email.message_from_bytes(raw_email)
                    
                    # Parse email
                    subject = email_msg.get("Subject", "No Subject")
                    sender = email_msg.get("From", "Unknown")
                    recipient = email_msg.get("To", "")
                    date_str = email_msg.get("Date", "")
                    
                    # Parse date
                    try:
                        date = email.utils.parsedate_to_datetime(date_str)
                    except Exception:
                        date = datetime.now()
                    
                    # Get body
                    body = self._get_email_body(email_msg)
                    
                    # Check attachments
                    has_attachments = any(
                        part.get_content_disposition() == "attachment"
                        for part in email_msg.walk()
                    )
                    
                    emails.append(EmailMessage(
                        id=msg_id.decode(),
                        subject=subject,
                        sender=sender,
                        recipient=recipient,
                        date=date,
                        body=body[:500],  # Limit preview
                        is_read=False,  # Would need to check flags
                        has_attachments=has_attachments,
                    ))
                    
                except Exception as e:
                    logger.error(f"Error parsing email {msg_id}: {e}")
                    continue
            
            return emails
            
        except Exception as e:
            logger.error(f"Failed to read emails: {e}")
            return []
    
    def _get_email_body(self, email_msg: email.message.Message) -> str:
        """Extract text body from email."""
        body = ""
        
        if email_msg.is_multipart():
            for part in email_msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode()
                        break
                    except Exception:
                        continue
                elif content_type == "text/html" and not body:
                    try:
                        html = part.get_payload(decode=True).decode()
                        # Simple HTML to text
                        import re
                        body = re.sub(r"<[^>]+>", " ", html)
                    except Exception:
                        continue
        else:
            try:
                body = email_msg.get_payload(decode=True).decode()
            except Exception:
                body = str(email_msg.get_payload())
        
        return body.strip()
    
    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html: bool = False,
    ) -> bool:
        """Send an email."""
        creds = self._get_credentials()
        if not creds:
            logger.error("Email credentials not configured")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg["From"] = creds["email"]
            msg["To"] = to
            msg["Subject"] = subject
            
            # Attach body
            content_type = "html" if html else "plain"
            msg.attach(MIMEText(body, content_type))
            
            # Send via SMTP
            with smtplib.SMTP_SSL(creds["smtp_server"], 465) as server:
                server.login(creds["email"], creds["password"])
                server.send_message(msg)
            
            logger.info(f"Email sent to {to}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def search_emails(self, query: str, folder: str = "INBOX") -> list[EmailMessage]:
        """Search emails by query."""
        if not self.imap_connection and not self.connect():
            return []
        
        try:
            self.imap_connection.select(folder)
            
            # Search in subject and body
            _, message_ids = self.imap_connection.search(None, f'SUBJECT "{query}"')
            
            # Also try body search if server supports it
            try:
                _, body_ids = self.imap_connection.search(None, f'BODY "{query}"')
                all_ids = set(message_ids[0].split()) | set(body_ids[0].split())
            except Exception:
                all_ids = set(message_ids[0].split())
            
            # Fetch and filter
            emails = []
            for msg_id in list(all_ids)[:20]:  # Limit results
                try:
                    _, msg_data = self.imap_connection.fetch(msg_id, "(RFC822)")
                    raw_email = msg_data[0][1]
                    email_msg = email.message_from_bytes(raw_email)
                    
                    emails.append(EmailMessage(
                        id=msg_id.decode(),
                        subject=email_msg.get("Subject", "No Subject"),
                        sender=email_msg.get("From", "Unknown"),
                        recipient=email_msg.get("To", ""),
                        date=datetime.now(),  # Simplified
                        body=self._get_email_body(email_msg)[:200],
                        is_read=True,
                        has_attachments=False,
                    ))
                except Exception:
                    continue
            
            return emails
            
        except Exception as e:
            logger.error(f"Email search failed: {e}")
            return []
    
    def get_unread_count(self, folder: str = "INBOX") -> int:
        """Get count of unread emails."""
        if not self.imap_connection and not self.connect():
            return 0
        
        try:
            self.imap_connection.select(folder)
            _, message_ids = self.imap_connection.search(None, "UNSEEN")
            return len(message_ids[0].split())
        except Exception as e:
            logger.error(f"Failed to get unread count: {e}")
            return 0


# Global email manager
email_manager = EmailManager()


def setup_email(email: str, password: str, imap: str = "imap.gmail.com") -> str:
    """Setup email credentials."""
    secure_storage.set("EMAIL_ADDRESS", email)
    secure_storage.set("EMAIL_PASSWORD", password)
    secure_storage.set("IMAP_SERVER", imap)
    secure_storage.set("SMTP_SERVER", imap.replace("imap", "smtp"))
    return "Email credentials saved securely"


def read_my_emails(limit: int = 5, unread_only: bool = False) -> str:
    """Read recent emails."""
    emails = email_manager.read_emails(limit=limit, unread_only=unread_only)
    if not emails:
        return "No emails found or not connected"
    
    lines = [f"Found {len(emails)} emails:"]
    for i, e in enumerate(emails, 1):
        lines.append(f"{i}. From: {e.sender}")
        lines.append(f"   Subject: {e.subject}")
        lines.append(f"   Date: {e.date.strftime('%Y-%m-%d %H:%M')}")
        lines.append("")
    
    return "\n".join(lines)


def send_email(to: str, subject: str, body: str) -> str:
    """Send an email."""
    success = email_manager.send_email(to, subject, body)
    if success:
        return f"Email sent to {to}"
    return "Failed to send email"
