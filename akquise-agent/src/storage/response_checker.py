"""
IMAP Response Checker - Prüft auf eingehende Antworten.

Verbindet sich mit dem IMAP-Postfach und prüft, ob Kontakte geantwortet haben.
Wichtig um Follow-Ups nur an nicht-antwortierte Kontakte zu senden.
"""

import asyncio
import email
from email.header import decode_header
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Set
from dataclasses import dataclass, field
from loguru import logger

try:
    import aioimaplib
    AIOIMAPLIB_AVAILABLE = True
except ImportError:
    AIOIMAPLIB_AVAILABLE = False
    logger.warning("aioimaplib not installed - response checking disabled")


@dataclass
class EmailReply:
    """Represents an incoming email reply."""
    sender: str
    sender_name: str = ""
    subject: str = ""
    date: datetime = None
    message_id: str = ""
    in_reply_to: str = ""
    references: List[str] = field(default_factory=list)
    body_preview: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            'sender': self.sender,
            'sender_name': self.sender_name,
            'subject': self.subject,
            'date': self.date.isoformat() if self.date else None,
            'message_id': self.message_id,
            'in_reply_to': self.in_reply_to,
            'body_preview': self.body_preview[:200]
        }


class ResponseChecker:
    """
    Checks IMAP inbox for replies to sent emails.

    This allows the system to:
    - Skip follow-ups for contacts who already responded
    - Track response rates
    - Personalize follow-ups based on responses
    """

    def __init__(self, config=None):
        """
        Initialize response checker.

        Args:
            config: IMAPConfig (uses env vars if not provided)
        """
        from src.storage.imap_drafts import IMAPConfig
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
        """Connect to IMAP server."""
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

    async def find_inbox_folder(self) -> Optional[str]:
        """Find the Inbox folder name."""
        if not self._client:
            return None

        result, data = await self._client.list('', '*')

        if result != 'OK':
            return None

        inbox_names = ['INBOX', 'Inbox', 'inbox']

        for line in data:
            if isinstance(line, bytes):
                line = line.decode('utf-8', errors='ignore')

            line_lower = line.lower()
            for name in inbox_names:
                if name.lower() in line_lower:
                    return 'INBOX'

        return 'INBOX'

    async def get_replies(
        self,
        sent_emails: List[Dict[str, Any]],
        days_back: int = 30,
        mark_as_read: bool = False
    ) -> Dict[str, EmailReply]:
        """
        Check for replies to sent emails.

        Args:
            sent_emails: List of sent emails with 'to' and 'subject' fields
            days_back: How many days back to search
            mark_as_read: Whether to mark replies as read

        Returns:
            Dict mapping email addresses to their replies
        """
        if not AIOIMAPLIB_AVAILABLE:
            logger.error("aioimaplib not installed")
            return {}

        if not self._client:
            if not await self.connect():
                return {}

        replies = {}
        sender_emails = {e.get('to', '').lower() for e in sent_emails if e.get('to')}

        try:
            # Select inbox
            inbox = await self.find_inbox_folder() or 'INBOX'
            result, data = await self._client.select(inbox)

            if result != 'OK':
                logger.error(f"Could not select inbox: {result}")
                return {}

            # Search for unread messages in date range
            since_date = (datetime.now() - timedelta(days=days_back)).strftime('%d-%b-%Y')
            result, data = await self._client.search(
                None,
                'SINCE', since_date,
                'UNSEEN'  # Only unread messages
            )

            if result != 'OK':
                logger.error(f"Search failed: {result}")
                return {}

            message_ids = data[0].split() if data[0] else []

            logger.info(f"Found {len(message_ids)} unread messages to check")

            for msg_id in message_ids:
                reply = await self._check_message_for_reply(
                    msg_id,
                    sender_emails,
                    mark_as_read
                )

                if reply:
                    replies[reply.sender.lower()] = reply

            return replies

        except Exception as e:
            logger.error(f"Error checking replies: {e}")
            return {}

    async def _check_message_for_reply(
        self,
        msg_id: bytes,
        sender_emails: Set[str],
        mark_as_read: bool = False
    ) -> Optional[EmailReply]:
        """
        Check a single message if it's a reply from our contacts.

        Args:
            msg_id: IMAP message ID
            sender_emails: Set of email addresses we sent to
            mark_as_read: Whether to mark as read

        Returns:
            EmailReply if it's from a contact, None otherwise
        """
        try:
            result, data = await self._client.fetch(msg_id, '(BODY.PEEK[HEADER] BODY.PEEK[TEXT])')

            if result != 'OK' or not data:
                return None

            # Parse email
            raw_header = data[0][1] if len(data) > 0 and len(data[0]) > 1 else b''
            raw_body = data[1][1] if len(data) > 1 and len(data[1]) > 1 else b''

            # Decode header
            if isinstance(raw_header, bytes):
                raw_header = raw_header.decode('utf-8', errors='ignore')

            # Parse sender
            sender = None
            sender_name = ""
            subject = ""
            message_id = ""
            in_reply_to = ""
            date = None

            for line in raw_header.split('\n'):
                line_lower = line.lower()

                if line_lower.startswith('from:'):
                    # Parse From: field
                    from_value = line[5:].strip()
                    # Extract email from "Name <email>" or "email"
                    if '<' in from_value and '>' in from_value:
                        sender = from_value.split('<')[1].split('>')[0].strip()
                        sender_name = from_value.split('<')[0].strip().strip('"')
                    else:
                        sender = from_value.strip()
                        sender_name = sender

                elif line_lower.startswith('subject:'):
                    subject = self._decode_header_value(line[9:].strip())

                elif line_lower.startswith('message-id:'):
                    message_id = line[11:].strip()

                elif line_lower.startswith('in-reply-to:'):
                    in_reply_to = line[12:].strip()

                elif line_lower.startswith('date:'):
                    try:
                        date_str = line[6:].strip()
                        # Parse date...
                        date = datetime.now()  # Simplified
                    except:
                        pass

            if not sender or sender.lower() not in sender_emails:
                return None

            # Decode body preview
            body_preview = ""
            if isinstance(raw_body, bytes):
                body_preview = raw_body.decode('utf-8', errors='ignore')[:500]

            reply = EmailReply(
                sender=sender,
                sender_name=sender_name,
                subject=subject,
                date=date or datetime.now(),
                message_id=message_id,
                in_reply_to=in_reply_to,
                body_preview=body_preview
            )

            logger.info(f"Found reply from {sender}: {subject}")

            # Mark as read if requested
            if mark_as_read:
                await self._client.store(msg_id, '+FLAGS', '\\Seen')

            return reply

        except Exception as e:
            logger.debug(f"Error parsing message: {e}")
            return None

    def _decode_header_value(self, value: str) -> str:
        """Decode MIME encoded header value."""
        try:
            decoded_parts = decode_header(value)
            result = []
            for part, charset in decoded_parts:
                if isinstance(part, bytes):
                    result.append(part.decode(charset or 'utf-8', errors='ignore'))
                else:
                    result.append(part)
            return ''.join(result)
        except:
            return value

    async def check_specific_contact(
        self,
        email_address: str,
        days_back: int = 30
    ) -> Optional[EmailReply]:
        """
        Check if a specific contact has replied.

        Args:
            email_address: Email address to check
            days_back: How many days back to search

        Returns:
            EmailReply if found, None otherwise
        """
        result = await self.get_replies(
            [{'to': email_address}],
            days_back=days_back
        )
        return result.get(email_address.lower())

    def get_responded_contacts(
        self,
        sent_emails: List[Dict[str, Any]],
        days_back: int = 30
    ) -> Set[str]:
        """
        Synchronous wrapper to get set of contacts who responded.

        Args:
            sent_emails: List of sent emails
            days_back: How many days back to check

        Returns:
            Set of email addresses that responded
        """
        async def _check():
            replies = await self.get_replies(sent_emails, days_back)
            return set(replies.keys())

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(_check())


# Convenience function
async def check_for_replies(
    sent_emails: List[Dict[str, Any]],
    days_back: int = 30,
    config=None
) -> Dict[str, EmailReply]:
    """
    Check for replies to sent emails.

    Args:
        sent_emails: List of sent emails with 'to' field
        days_back: How many days back to check
        config: IMAP config (optional)

    Returns:
        Dict mapping email addresses to replies
    """
    checker = ResponseChecker(config)

    if not await checker.connect():
        return {}

    try:
        return await checker.get_replies(sent_emails, days_back)
    finally:
        await checker.disconnect()