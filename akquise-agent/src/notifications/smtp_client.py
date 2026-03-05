"""
SMTP Email Client for sending emails via Namecheap Private Email.

Features:
- Async email sending
- Rate limiting
- Connection testing
- HTML and plain text support
"""

import asyncio
import os
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from loguru import logger

try:
    import aiosmtplib
    AIOSMTPLIB_AVAILABLE = True
except ImportError:
    AIOSMTPLIB_AVAILABLE = False
    logger.warning("aiosmtplib not installed - SMTP features disabled")


@dataclass
class SMTPConfig:
    """SMTP configuration."""
    host: str = "mail.privateemail.com"
    port: int = 587
    user: str = ""
    password: str = ""
    from_name: str = "SE Handwerk GbR"
    from_email: str = "kontakt@sehandwerk.de"
    use_tls: bool = True
    daily_limit: int = 100
    rate_limit_seconds: float = 10.0

    @classmethod
    def from_env(cls) -> 'SMTPConfig':
        """Load configuration from environment variables."""
        return cls(
            host=os.getenv('SMTP_HOST', 'mail.privateemail.com'),
            port=int(os.getenv('SMTP_PORT', '587')),
            user=os.getenv('SMTP_USER', ''),
            password=os.getenv('SMTP_PASSWORD', ''),
            from_name=os.getenv('SMTP_FROM_NAME', 'SE Handwerk GbR'),
            from_email=os.getenv('SMTP_FROM_EMAIL', 'kontakt@sehandwerk.de'),
            use_tls=os.getenv('SMTP_USE_TLS', 'true').lower() == 'true',
            daily_limit=int(os.getenv('SMTP_DAILY_LIMIT', '100')),
            rate_limit_seconds=float(os.getenv('SMTP_RATE_LIMIT_SECONDS', '10.0')),
        )


class RateLimiter:
    """Rate limiter for email sending."""

    def __init__(self, max_per_hour: int = 100, min_delay_seconds: float = 10.0):
        """
        Initialize rate limiter.

        Args:
            max_per_hour: Maximum emails per hour
            min_delay_seconds: Minimum delay between emails
        """
        self.max_per_hour = max_per_hour
        self.min_delay_seconds = min_delay_seconds
        self.sent_times: List[datetime] = []
        self.last_sent: Optional[datetime] = None

    async def wait_if_needed(self) -> None:
        """Wait if necessary to respect rate limits."""
        now = datetime.now()

        # Clean up old timestamps
        hour_ago = now - timedelta(hours=1)
        self.sent_times = [t for t in self.sent_times if t > hour_ago]

        # Check hourly limit
        if len(self.sent_times) >= self.max_per_hour:
            wait_seconds = (self.sent_times[0] - hour_ago).total_seconds() + 1
            logger.warning(f"Hourly rate limit reached, waiting {wait_seconds:.0f}s")
            await asyncio.sleep(wait_seconds)

        # Check minimum delay
        if self.last_sent:
            elapsed = (now - self.last_sent).total_seconds()
            if elapsed < self.min_delay_seconds:
                wait_seconds = self.min_delay_seconds - elapsed
                logger.debug(f"Rate limit: waiting {wait_seconds:.1f}s")
                await asyncio.sleep(wait_seconds)

    def record_sent(self) -> None:
        """Record that an email was sent."""
        self.last_sent = datetime.now()
        self.sent_times.append(self.last_sent)


class SMTPSender:
    """
    SMTP email sender with rate limiting.

    Features:
    - Async email sending via aiosmtplib
    - Rate limiting to avoid provider blocks
    - Connection testing
    - Support for HTML and plain text emails
    """

    def __init__(self, config: Optional[SMTPConfig] = None):
        """
        Initialize SMTP sender.

        Args:
            config: SMTP configuration (uses env vars if not provided)
        """
        self.config = config or SMTPConfig.from_env()
        self.rate_limiter = RateLimiter(
            max_per_hour=self.config.daily_limit,
            min_delay_seconds=self.config.rate_limit_seconds
        )
        self._sent_count = 0
        self._failed_count = 0

    @property
    def is_configured(self) -> bool:
        """Check if SMTP is properly configured."""
        return bool(
            self.config.user and
            self.config.password and
            self.config.host
        )

    @property
    def from_address(self) -> str:
        """Get formatted from address."""
        if self.config.from_name:
            return f"{self.config.from_name} <{self.config.from_email}>"
        return self.config.from_email

    async def test_connection(self) -> bool:
        """
        Test SMTP connection.

        Returns:
            True if connection successful
        """
        if not AIOSMTPLIB_AVAILABLE:
            logger.error("aiosmtplib not installed")
            return False

        if not self.is_configured:
            logger.warning("SMTP not configured")
            return False

        try:
            # Port 587 uses start_tls=True for STARTTLS
            smtp = aiosmtplib.SMTP(
                hostname=self.config.host,
                port=self.config.port,
                start_tls=True  # Use STARTTLS for port 587
            )
            await smtp.connect()
            await smtp.login(self.config.user, self.config.password)
            await smtp.quit()
            logger.info(f"SMTP connection test successful: {self.config.host}:{self.config.port}")
            return True
        except Exception as e:
            logger.error(f"SMTP connection test failed: {e}")
            return False

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html: bool = True,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> bool:
        """
        Send an email.

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body (HTML or plain text)
            html: Whether body is HTML
            cc: CC recipients
            bcc: BCC recipients

        Returns:
            True if sent successfully
        """
        if not AIOSMTPLIB_AVAILABLE:
            logger.error("aiosmtplib not installed - cannot send email")
            return False

        if not self.is_configured:
            logger.warning("SMTP not configured - cannot send email")
            return False

        # Wait for rate limiter
        await self.rate_limiter.wait_if_needed()

        try:
            # Create message
            if html:
                message = MIMEMultipart("alternative")
                message.attach(MIMEText(body, "html", "utf-8"))
                # Also attach plain text version
                plain_text = self._html_to_plain(body)
                message.attach(MIMEText(plain_text, "plain", "utf-8"))
            else:
                message = MIMEText(body, "plain", "utf-8")

            message["From"] = self.from_address
            message["To"] = to
            message["Subject"] = subject

            if cc:
                message["Cc"] = ", ".join(cc)
            if bcc:
                message["Bcc"] = ", ".join(bcc)

            # Connect and send using async context manager
            async with aiosmtplib.SMTP(
                hostname=self.config.host,
                port=self.config.port,
                start_tls=True
            ) as smtp:
                await smtp.login(self.config.user, self.config.password)
                await smtp.send_message(message)
                # Context manager handles cleanup

            # Record success
            self.rate_limiter.record_sent()
            self._sent_count += 1
            logger.info(f"Email sent to {to}: {subject}")

            return True

        except Exception as e:
            self._failed_count += 1
            logger.error(f"Failed to send email to {to}: {e}")
            return False

    async def send_with_template(
        self,
        to: str,
        subject: str,
        body: str,
        recipient_name: Optional[str] = None
    ) -> bool:
        """
        Send an email using a pre-generated template.

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body (HTML)
            recipient_name: Recipient name for personalization

        Returns:
            True if sent successfully
        """
        # Add greeting if name provided
        if recipient_name:
            # Insert greeting at beginning of body
            greeting = f"<p>Sehr geehrte(r) {recipient_name},</p>"
            if "<body>" in body:
                body = body.replace("<body>", f"<body>{greeting}")
            else:
                body = greeting + body

        return await self.send_email(to=to, subject=subject, body=body, html=True)

    def _html_to_plain(self, html: str) -> str:
        """Convert HTML to plain text."""
        import re
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html)
        # Decode HTML entities
        import html as html_module
        text = html_module.unescape(text)
        # Normalize whitespace
        text = ' '.join(text.split())
        return text

    def get_stats(self) -> dict:
        """Get sending statistics."""
        return {
            'sent': self._sent_count,
            'failed': self._failed_count,
            'total': self._sent_count + self._failed_count,
            'success_rate': self._sent_count / max(1, self._sent_count + self._failed_count),
        }


# Synchronous wrapper for convenience
def send_email_sync(
    to: str,
    subject: str,
    body: str,
    config: Optional[SMTPConfig] = None
) -> bool:
    """
    Synchronous wrapper for sending emails.

    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body
        config: SMTP configuration

    Returns:
        True if sent successfully
    """
    sender = SMTPSender(config)

    async def _send():
        return await sender.send_email(to=to, subject=subject, body=body)

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(_send())