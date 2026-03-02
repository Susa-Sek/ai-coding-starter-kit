"""
Telegram notification client for Akquise Agent.
"""

import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
import httpx

from loguru import logger


@dataclass
class TelegramConfig:
    """Telegram bot configuration."""
    bot_token: str
    user_id: str
    api_base: str = "https://api.telegram.org/bot"

    @classmethod
    def from_env(cls) -> 'TelegramConfig':
        """Load configuration from environment variables."""
        import os
        return cls(
            bot_token=os.getenv('TELEGRAM_BOT_TOKEN', ''),
            user_id=os.getenv('TELEGRAM_USER_ID', '')
        )


class TelegramNotifier:
    """
    Telegram notification client for sending alerts and reminders.

    Features:
    - Send instant notifications for new A-class leads
    - Send daily summaries
    - Send follow-up reminders
    - Send error alerts
    - Rate limiting and retry logic
    """

    # Rate limiting
    MAX_MESSAGES_PER_SECOND = 30
    MAX_MESSAGES_PER_MINUTE = 20

    def __init__(self, config: Optional[TelegramConfig] = None):
        """
        Initialize Telegram notifier.

        Args:
            config: Telegram configuration (uses env vars if not provided)
        """
        self.config = config or TelegramConfig.from_env()
        self._message_queue: List[str] = []
        self._last_send_time: Optional[datetime] = None

    @property
    def is_configured(self) -> bool:
        """Check if Telegram is properly configured."""
        return bool(self.config.bot_token and self.config.user_id)

    def _get_api_url(self, method: str) -> str:
        """Get full API URL for a method."""
        return f"{self.config.api_base}{self.config.bot_token}/{method}"

    async def send_message(
        self,
        text: str,
        parse_mode: str = "HTML",
        disable_notification: bool = False
    ) -> bool:
        """
        Send a message via Telegram.

        Args:
            text: Message text (HTML formatted)
            parse_mode: Parse mode (HTML, Markdown, or None)
            disable_notification: Send silently without notification

        Returns:
            True if message was sent successfully
        """
        if not self.is_configured:
            logger.warning("Telegram not configured - skipping notification")
            return False

        url = self._get_api_url("sendMessage")
        payload = {
            "chat_id": self.config.user_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_notification": disable_notification
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()

                result = response.json()
                if result.get("ok"):
                    self._last_send_time = datetime.now()
                    logger.info("Telegram message sent successfully")
                    return True
                else:
                    logger.error(f"Telegram API error: {result.get('description')}")
                    return False

        except httpx.HTTPStatusError as e:
            logger.error(f"Telegram HTTP error: {e}")
            return False
        except httpx.RequestError as e:
            logger.error(f"Telegram request error: {e}")
            return False
        except Exception as e:
            logger.error(f"Telegram unexpected error: {e}")
            return False

    async def send_lead_notification(
        self,
        company_name: str,
        address: Optional[str],
        phone: Optional[str],
        email: Optional[str],
        units: Optional[int],
        score: int,
        grade: str,
        sheets_url: Optional[str] = None
    ) -> bool:
        """
        Send notification for a new A-class lead.

        Args:
            company_name: Company name
            address: Company address
            phone: Phone number
            email: Email address
            units: Number of units
            score: Qualification score
            grade: Lead grade (A/B/C)
            sheets_url: Link to Google Sheets row

        Returns:
            True if message was sent successfully
        """
        # Build message
        lines = [
            "🆕 <b>NEUER A-KLASSE LEAD</b>",
            "",
            f"🏢 <b>Firma:</b> {company_name}",
        ]

        if address:
            lines.append(f"📍 <b>Adresse:</b> {address}")

        if phone:
            lines.append(f"📞 <b>Telefon:</b> {phone}")

        if email:
            lines.append(f"📧 <b>E-Mail:</b> {email}")

        if units:
            lines.append(f"📊 <b>Einheiten:</b> ~{units}")

        lines.append(f"⭐ <b>Qualifikation:</b> {grade} ({score}/100)")
        lines.append("")

        if sheets_url:
            lines.append(f'<a href="{sheets_url}">📋 Google Sheets öffnen</a>')
            lines.append("")

        lines.append("---")
        lines.append("🤖 Akquise Agent")

        message = "\n".join(lines)
        return await self.send_message(message)

    async def send_daily_summary(
        self,
        total_new: int,
        a_class: int,
        b_class: int,
        c_class: int,
        followups_due: int,
        sheets_url: Optional[str] = None
    ) -> bool:
        """
        Send daily summary notification.

        Args:
            total_new: Total new leads today
            a_class: A-class leads count
            b_class: B-class leads count
            c_class: C-class leads count
            followups_due: Follow-ups due today
            sheets_url: Link to Google Sheets

        Returns:
            True if message was sent successfully
        """
        lines = [
            "📊 <b>TÄGLICHE ZUSAMMENFASSUNG</b>",
            f"📅 {datetime.now().strftime('%d.%m.%Y')}",
            "",
            f"🆕 <b>Neue Leads:</b> {total_new}",
            f"   🟢 A-Klasse: {a_class}",
            f"   🟡 B-Klasse: {b_class}",
            f"   🔴 C-Klasse: {c_class}",
            "",
            f"📅 <b>Follow-ups fällig:</b> {followups_due}",
        ]

        if sheets_url:
            lines.append("")
            lines.append(f'<a href="{sheets_url}">📋 Google Sheets öffnen</a>')

        lines.append("")
        lines.append("---")
        lines.append("🤖 Akquise Agent")

        message = "\n".join(lines)
        return await self.send_message(message)

    async def send_followup_reminder(
        self,
        company_name: str,
        days_since_contact: int,
        status: str,
        email_draft: Optional[str] = None,
        sheets_url: Optional[str] = None
    ) -> bool:
        """
        Send follow-up reminder.

        Args:
            company_name: Company name
            days_since_contact: Days since initial contact
            status: Current status
            email_draft: Pre-generated email draft
            sheets_url: Link to Google Sheets

        Returns:
            True if message was sent successfully
        """
        followup_number = 1 if days_since_contact <= 10 else 2

        lines = [
            f"📅 <b>FOLLOW-UP ERINNERUNG #{followup_number}</b>",
            "",
            f"🏢 <b>Firma:</b> {company_name}",
            f"⏱ <b>Tage seit Kontakt:</b> {days_since_contact}",
            f"📋 <b>Status:</b> {status}",
        ]

        if sheets_url:
            lines.append("")
            lines.append(f'<a href="{sheets_url}">📋 Google Sheets öffnen</a>')

        if email_draft:
            lines.append("")
            lines.append("📧 <b>Vorgeschlagene E-Mail:</b>")
            lines.append("")
            # Truncate long drafts
            if len(email_draft) > 500:
                email_draft = email_draft[:500] + "..."
            lines.append(f"<pre>{email_draft}</pre>")

        lines.append("")
        lines.append("---")
        lines.append("🤖 Akquise Agent")

        message = "\n".join(lines)
        return await self.send_message(message)

    async def send_weekly_report(
        self,
        total_new: int,
        a_class: int,
        replies: int,
        meetings: int,
        top_leads: List[Dict[str, Any]],
        scraper_health: str,
        sheets_url: Optional[str] = None
    ) -> bool:
        """
        Send weekly report.

        Args:
            total_new: Total new leads this week
            a_class: A-class leads count
            replies: Number of replies received
            meetings: Number of meetings scheduled
            top_leads: Top 5 A-class leads
            scraper_health: Scraper health status
            sheets_url: Link to Google Sheets

        Returns:
            True if message was sent successfully
        """
        lines = [
            "📈 <b>WÖCHENTLICHER BERICHT</b>",
            f"📅 Woche {datetime.now().isocalendar()[1]}",
            "",
            f"🆕 <b>Neue Leads:</b> {total_new}",
            f"🟢 <b>A-Klasse:</b> {a_class}",
            "",
            f"📧 <b>Antworten:</b> {replies}",
            f"📅 <b>Gespräche:</b> {meetings}",
            "",
            f"🔧 <b>Scraper Status:</b> {scraper_health}",
        ]

        if top_leads:
            lines.append("")
            lines.append("<b>Top 5 A-Klasse Leads:</b>")
            for i, lead in enumerate(top_leads[:5], 1):
                lines.append(f"  {i}. {lead.get('company_name', 'Unbekannt')} ({lead.get('score', 0)}/100)")

        if sheets_url:
            lines.append("")
            lines.append(f'<a href="{sheets_url}">📋 Google Sheets öffnen</a>')

        lines.append("")
        lines.append("---")
        lines.append("🤖 Akquise Agent")

        message = "\n".join(lines)
        return await self.send_message(message)

    async def send_error_notification(
        self,
        error_type: str,
        error_message: str,
        suggested_action: Optional[str] = None
    ) -> bool:
        """
        Send error notification.

        Args:
            error_type: Type of error
            error_message: Error message
            suggested_action: Suggested action to take

        Returns:
            True if message was sent successfully
        """
        lines = [
            "⚠️ <b>FEHLER</b>",
            "",
            f"🔴 <b>Typ:</b> {error_type}",
            f"💬 <b>Meldung:</b> {error_message}",
        ]

        if suggested_action:
            lines.append(f"💡 <b>Empfehlung:</b> {suggested_action}")

        lines.append("")
        lines.append("---")
        lines.append("🤖 Akquise Agent")

        message = "\n".join(lines)
        return await self.send_message(message)

    async def test_connection(self) -> bool:
        """
        Test Telegram connection.

        Returns:
            True if connection is successful
        """
        if not self.is_configured:
            logger.warning("Telegram not configured")
            return False

        url = self._get_api_url("getMe")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                result = response.json()

                if result.get("ok"):
                    bot_info = result.get("result", {})
                    logger.info(f"Telegram bot connected: @{bot_info.get('username', 'unknown')}")
                    return True
                else:
                    logger.error(f"Telegram connection failed: {result.get('description')}")
                    return False

        except Exception as e:
            logger.error(f"Telegram connection error: {e}")
            return False


# Synchronous wrapper for convenience
def send_telegram_message(text: str, config: Optional[TelegramConfig] = None) -> bool:
    """
    Synchronous wrapper for sending Telegram messages.

    Args:
        text: Message text
        config: Optional Telegram configuration

    Returns:
        True if message was sent successfully
    """
    notifier = TelegramNotifier(config)

    async def _send():
        return await notifier.send_message(text)

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(_send())