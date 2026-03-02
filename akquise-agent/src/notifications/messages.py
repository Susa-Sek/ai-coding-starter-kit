"""
Message templates for Telegram notifications.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime


class MessageTemplates:
    """Templates for Telegram notifications."""

    @staticmethod
    def new_lead(
        company_name: str,
        address: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        units: Optional[int] = None,
        employees: Optional[int] = None,
        score: int = 0,
        grade: str = "C",
        sheets_url: Optional[str] = None
    ) -> str:
        """
        Generate new lead notification message.

        Args:
            company_name: Company name
            address: Company address
            phone: Phone number
            email: Email address
            units: Number of units
            employees: Number of employees
            score: Qualification score
            grade: Lead grade (A/B/C)
            sheets_url: Link to Google Sheets row

        Returns:
            Formatted message string
        """
        grade_emoji = {"A": "🟢", "B": "🟡", "C": "🔴"}.get(grade, "⚪")

        lines = [
            "🆕 <b>NEUER LEAD GEFUNDEN</b>",
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

        if employees:
            lines.append(f"👥 <b>Mitarbeiter:</b> ~{employees}")

        lines.append(f"⭐ <b>Qualifikation:</b> {grade_emoji} {grade} ({score}/100)")

        if sheets_url:
            lines.append("")
            lines.append(f'<a href="{sheets_url}">📋 In Google Sheets öffnen</a>')

        lines.append("")
        lines.append("---")
        lines.append("🤖 Akquise Agent")

        return "\n".join(lines)

    @staticmethod
    def daily_summary(
        date: Optional[datetime] = None,
        new_leads: int = 0,
        a_class: int = 0,
        b_class: int = 0,
        c_class: int = 0,
        followups_due: int = 0,
        emails_sent: int = 0,
        sheets_url: Optional[str] = None
    ) -> str:
        """
        Generate daily summary message.

        Args:
            date: Summary date (defaults to today)
            new_leads: Total new leads
            a_class: A-class count
            b_class: B-class count
            c_class: C-class count
            followups_due: Follow-ups due today
            emails_sent: Emails sent today
            sheets_url: Link to Google Sheets

        Returns:
            Formatted message string
        """
        date = date or datetime.now()

        lines = [
            "📊 <b>TÄGLICHE ZUSAMMENFASSUNG</b>",
            f"📅 {date.strftime('%d.%m.%Y')}",
            "",
            f"<b>Neue Leads heute:</b> {new_leads}",
            f"   🟢 A-Klasse: {a_class}",
            f"   🟡 B-Klasse: {b_class}",
            f"   🔴 C-Klasse: {c_class}",
            "",
            f"📅 <b>Follow-ups fällig:</b> {followups_due}",
            f"📧 <b>E-Mails gesendet:</b> {emails_sent}",
        ]

        if sheets_url:
            lines.append("")
            lines.append(f'<a href="{sheets_url}">📋 Google Sheets öffnen</a>')

        lines.append("")
        lines.append("---")
        lines.append("🤖 Akquise Agent")

        return "\n".join(lines)

    @staticmethod
    def followup_reminder(
        company_name: str,
        days_since_contact: int,
        status: str,
        followup_number: int = 1,
        last_contact: Optional[str] = None,
        email_preview: Optional[str] = None,
        sheets_url: Optional[str] = None
    ) -> str:
        """
        Generate follow-up reminder message.

        Args:
            company_name: Company name
            days_since_contact: Days since initial contact
            status: Current status
            followup_number: Follow-up number (1 or 2)
            last_contact: Date of last contact
            email_preview: Preview of suggested email
            sheets_url: Link to Google Sheets

        Returns:
            Formatted message string
        """
        urgency = "🔴" if followup_number == 2 else "🟡"

        lines = [
            f"{urgency} <b>FOLLOW-UP ERINNERUNG #{followup_number}</b>",
            "",
            f"🏢 <b>Firma:</b> {company_name}",
            f"⏱ <b>Tage seit Kontakt:</b> {days_since_contact}",
            f"📋 <b>Status:</b> {status}",
        ]

        if last_contact:
            lines.append(f"📅 <b>Letzter Kontakt:</b> {last_contact}")

        if sheets_url:
            lines.append("")
            lines.append(f'<a href="{sheets_url}">📋 Google Sheets öffnen</a>')

        if email_preview:
            lines.append("")
            lines.append("📧 <b>Vorgeschlagener E-Mail-Text:</b>")
            lines.append("")
            # Truncate for Telegram
            preview = email_preview[:400] + "..." if len(email_preview) > 400 else email_preview
            lines.append(f"<code>{preview}</code>")

        lines.append("")
        lines.append("---")
        lines.append("🤖 Akquise Agent")

        return "\n".join(lines)

    @staticmethod
    def weekly_report(
        week_number: int,
        total_leads: int = 0,
        a_class: int = 0,
        replies: int = 0,
        meetings: int = 0,
        conversion_rate: float = 0.0,
        top_leads: Optional[List[Dict[str, Any]]] = None,
        scraper_health: str = "✅ OK",
        sheets_url: Optional[str] = None
    ) -> str:
        """
        Generate weekly report message.

        Args:
            week_number: Week number
            total_leads: Total leads this week
            a_class: A-class leads count
            replies: Number of replies
            meetings: Number of meetings
            conversion_rate: Conversion rate percentage
            top_leads: List of top leads
            scraper_health: Scraper health status
            sheets_url: Link to Google Sheets

        Returns:
            Formatted message string
        """
        lines = [
            "📈 <b>WÖCHENTLICHER BERICHT</b>",
            f"📅 Kalenderwoche {week_number}",
            "",
            f"🆕 <b>Neue Leads:</b> {total_leads}",
            f"🟢 <b>A-Klasse:</b> {a_class}",
            "",
            f"📧 <b>Antworten:</b> {replies}",
            f"📅 <b>Gespräche:</b> {meetings}",
            f"📊 <b>Konversionsrate:</b> {conversion_rate:.1f}%",
            "",
            f"🔧 <b>Scraper Status:</b> {scraper_health}",
        ]

        if top_leads:
            lines.append("")
            lines.append("<b>🏆 Top 5 A-Klasse Leads:</b>")
            for i, lead in enumerate(top_leads[:5], 1):
                name = lead.get('company_name', 'Unbekannt')
                score = lead.get('score', 0)
                lines.append(f"  {i}. {name} ({score}/100)")

        if sheets_url:
            lines.append("")
            lines.append(f'<a href="{sheets_url}">📋 Google Sheets öffnen</a>')

        lines.append("")
        lines.append("---")
        lines.append("🤖 Akquise Agent")

        return "\n".join(lines)

    @staticmethod
    def error_alert(
        error_type: str,
        error_message: str,
        timestamp: Optional[datetime] = None,
        suggested_action: Optional[str] = None,
        retry_count: int = 0
    ) -> str:
        """
        Generate error alert message.

        Args:
            error_type: Type of error
            error_message: Error message
            timestamp: Error timestamp
            suggested_action: Suggested action
            retry_count: Number of retries

        Returns:
            Formatted message string
        """
        timestamp = timestamp or datetime.now()

        lines = [
            "⚠️ <b>FEHLER ALERT</b>",
            f"🕐 {timestamp.strftime('%d.%m.%Y %H:%M')}",
            "",
            f"🔴 <b>Typ:</b> {error_type}",
            f"💬 <b>Meldung:</b>",
            f"<code>{error_message[:200]}</code>",
        ]

        if retry_count > 0:
            lines.append(f"🔄 <b>Versuche:</b> {retry_count}")

        if suggested_action:
            lines.append("")
            lines.append(f"💡 <b>Empfehlung:</b>")
            lines.append(f"   {suggested_action}")

        lines.append("")
        lines.append("---")
        lines.append("🤖 Akquise Agent")

        return "\n".join(lines)

    @staticmethod
    def scraper_status(
        source: str,
        status: str,
        leads_found: int = 0,
        errors: int = 0,
        last_run: Optional[datetime] = None
    ) -> str:
        """
        Generate scraper status message.

        Args:
            source: Scraper source name
            status: Status (running, completed, failed)
            leads_found: Number of leads found
            errors: Number of errors
            last_run: Last run timestamp

        Returns:
            Formatted message string
        """
        status_emoji = {
            "running": "🔄",
            "completed": "✅",
            "failed": "❌"
        }.get(status, "❓")

        lines = [
            f"{status_emoji} <b>SCRAPER STATUS</b>",
            "",
            f"📡 <b>Quelle:</b> {source}",
            f"📊 <b>Status:</b> {status}",
            f"🆕 <b>Leads gefunden:</b> {leads_found}",
        ]

        if errors > 0:
            lines.append(f"⚠️ <b>Fehler:</b> {errors}")

        if last_run:
            lines.append(f"🕐 <b>Letzter Lauf:</b> {last_run.strftime('%d.%m.%Y %H:%M')}")

        lines.append("")
        lines.append("---")
        lines.append("🤖 Akquise Agent")

        return "\n".join(lines)