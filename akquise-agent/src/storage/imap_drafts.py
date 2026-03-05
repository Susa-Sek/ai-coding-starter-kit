"""
IMAP Draft Saver - Speichert E-Mail-Entwürfe direkt im E-Mail-Konto.

Verwendet IMAP, um Entwürfe im "Drafts" Ordner des E-Mail-Kontos zu speichern.
So kannst du die Entwürfe direkt in Outlook/Thunderbird öffnen und senden.
"""

import asyncio
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from imaplib import Time2Internaldate
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import os
import time

from loguru import logger

try:
    import aioimaplib
    AIOIMAPLIB_AVAILABLE = True
except ImportError:
    AIOIMAPLIB_AVAILABLE = False
    logger.warning("aioimaplib not installed - IMAP drafts disabled")


@dataclass
class IMAPConfig:
    """IMAP configuration."""
    host: str = "mail.privateemail.com"
    port: int = 993
    user: str = ""
    password: str = ""
    use_ssl: bool = True
    drafts_folder: str = "Drafts"

    @classmethod
    def from_env(cls) -> 'IMAPConfig':
        """Load configuration from environment variables."""
        return cls(
            host=os.getenv('IMAP_HOST', 'mail.privateemail.com'),
            port=int(os.getenv('IMAP_PORT', '993')),
            user=os.getenv('SMTP_USER', ''),  # Same as SMTP
            password=os.getenv('SMTP_PASSWORD', ''),
            use_ssl=os.getenv('IMAP_USE_SSL', 'true').lower() == 'true',
            drafts_folder=os.getenv('IMAP_DRAFTS_FOLDER', 'Drafts')
        )


class IMAPDraftSaver:
    """
    Saves email drafts directly to IMAP Drafts folder.
    
    This allows you to open drafts in your email client (Outlook, Thunderbird)
    and send them manually with just one click.
    """
    
    def __init__(self, config: Optional[IMAPConfig] = None):
        """
        Initialize IMAP draft saver.
        
        Args:
            config: IMAP configuration (uses env vars if not provided)
        """
        self.config = config or IMAPConfig.from_env()
        self._client = None
        
    @property
    def is_configured(self) -> bool:
        """Check if IMAP is properly configured."""
        return bool(
            self.config.user and
            self.config.password and
            self.config.host
        )
    
    async def connect(self) -> bool:
        """
        Connect to IMAP server.
        
        Returns:
            True if connection successful
        """
        if not AIOIMAPLIB_AVAILABLE:
            logger.error("aioimaplib not installed")
            return False
        
        if not self.is_configured:
            logger.warning("IMAP not configured")
            return False
        
        try:
            self._client = aioimaplib.IMAP4_SSL(
                host=self.config.host,
                port=self.config.port
            )
            await self._client.wait_hello_from_server()
            
            result = await self._client.login(
                self.config.user,
                self.config.password
            )
            
            if result.result != 'OK':
                logger.error(f"IMAP login failed: {result}")
                return False
            
            logger.info(f"Connected to IMAP: {self.config.host}")
            return True
            
        except Exception as e:
            logger.error(f"IMAP connection failed: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from IMAP server."""
        if self._client:
            try:
                await self._client.logout()
            except Exception:
                pass
            self._client = None
    
    async def find_drafts_folder(self) -> Optional[str]:
        """
        Find the Drafts folder name.

        Different email providers use different names:
        - Drafts, Draft, Entwürfe, Brouillons, etc.

        Returns:
            Folder name or None
        """
        if not self._client:
            return None

        # List all folders - need to provide reference and pattern
        result, data = await self._client.list('', '*')

        if result != 'OK':
            logger.error("Failed to list folders")
            return None

        # Common draft folder names
        draft_names = [
            'Drafts', 'Draft', 'Entwürfe', 'Entwurf',
            'Brouillons', 'Borradores', 'Bozze',
            'INBOX.Drafts', 'INBOX/Drafts'
        ]

        for line in data:
            if isinstance(line, bytes):
                line = line.decode('utf-8', errors='ignore')

            line_lower = line.lower()
            for name in draft_names:
                if name.lower() in line_lower:
                    # Extract folder name from LIST response
                    # Format: (\\HasChildren) "." "INBOX.Drafts"
                    parts = line.split('"')
                    if len(parts) >= 3:
                        folder = parts[-2] or parts[-1]
                        return folder.strip().strip('"')

        # Default to "Drafts"
        return self.config.drafts_folder
    
    async def save_draft(
        self,
        to: str,
        subject: str,
        body_html: str,
        body_text: str = None,
        from_name: str = "SE Handwerk GbR",
        from_email: str = None
    ) -> bool:
        """
        Save a draft email to the Drafts folder.

        Args:
            to: Recipient email address
            subject: Email subject
            body_html: HTML body
            body_text: Plain text body (generated from HTML if not provided)
            from_name: Sender name
            from_email: Sender email (uses config if not provided)

        Returns:
            True if draft saved successfully
        """
        if not AIOIMAPLIB_AVAILABLE:
            logger.error("aioimaplib not installed - cannot save draft")
            return False

        if not self._client:
            if not await self.connect():
                return False

        try:
            # Generate plain text from HTML if not provided
            if not body_text:
                body_text = self._html_to_text(body_html)

            from_email = from_email or self.config.user

            # Create email message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{from_name} <{from_email}>"
            msg['To'] = to
            msg['Subject'] = subject
            msg['Date'] = formatdate(localtime=True)
            msg['Message-ID'] = make_msgid(domain=from_email.split('@')[1] if '@' in from_email else 'sehandwerk.de')

            # Attach parts
            msg.attach(MIMEText(body_text, 'plain', 'utf-8'))
            msg.attach(MIMEText(body_html, 'html', 'utf-8'))

            # Set draft flags
            msg.add_header('X-Auto-Response-Suppress', 'All')

            # Find drafts folder
            drafts_folder = await self.find_drafts_folder()

            if not drafts_folder:
                logger.warning("Drafts folder not found, using default 'Drafts'")
                drafts_folder = "Drafts"

            # Select drafts folder (create if not exists)
            try:
                result, data = await self._client.select(drafts_folder)
                if result != 'OK':
                    # Try to create the folder
                    await self._client.create(drafts_folder)
                    result, data = await self._client.select(drafts_folder)
            except Exception:
                # Use INBOX.Drafts as fallback
                drafts_folder = "INBOX.Drafts"
                try:
                    await self._client.create(drafts_folder)
                except Exception:
                    pass
                result, data = await self._client.select(drafts_folder)

            # Append draft
            draft_content = msg.as_string()

            # Convert to bytes
            if isinstance(draft_content, str):
                draft_content = draft_content.encode('utf-8')

            # aioimaplib append signature: append(message_bytes, mailbox, flags, date)
            # Try different folder names
            folder_names = ['Drafts', 'INBOX.Drafts', 'Draft', 'Entwürfe', 'INBOX']

            for folder in folder_names:
                try:
                    result = await self._client.append(
                        draft_content,  # message_bytes first!
                        mailbox=folder,
                        flags='\\Draft',
                        date=None  # Server will use current time
                    )
                    if result.result == 'OK':
                        logger.info(f"Draft saved to {folder}: {subject}")
                        return True
                except Exception as e:
                    logger.debug(f"Failed to save to {folder}: {e}")
                    continue

            logger.error("Failed to save draft to any folder")
            return False

        except Exception as e:
            logger.error(f"Error saving draft: {e}")
            return False
    
    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text."""
        import re
        # Remove HTML tags
        text = re.sub(r'<br\s*/?>', '\n', html)
        text = re.sub(r'</p>', '\n\n', text)
        text = re.sub(r'</div>', '\n', text)
        text = re.sub(r'<li[^>]*>', '\n- ', text)
        text = re.sub(r'<[^>]+>', '', text)
        # Decode HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&quot;', '"')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        # Clean up whitespace
        text = text.replace('\n\n\n', '\n\n')
        return text.strip()
    
    async def test_connection(self) -> bool:
        """
        Test IMAP connection.
        
        Returns:
            True if connection successful
        """
        if not await self.connect():
            return False
        
        try:
            # List mailboxes to verify connection
            result, data = await self._client.list()
            await self.disconnect()
            return result == 'OK'
        except Exception as e:
            logger.error(f"IMAP test failed: {e}")
            return False


# Sync wrapper for convenience
def save_draft_sync(
    to: str,
    subject: str,
    body_html: str,
    config: Optional[IMAPConfig] = None
) -> bool:
    """
    Synchronous wrapper for saving a draft.
    
    Args:
        to: Recipient email
        subject: Email subject
        body_html: HTML body
        config: IMAP config
        
    Returns:
        True if saved successfully
    """
    async def _save():
        saver = IMAPDraftSaver(config)
        return await saver.save_draft(
            to=to,
            subject=subject,
            body_html=body_html
        )
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_save())
