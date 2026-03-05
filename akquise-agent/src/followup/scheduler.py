"""
Follow-Up Scheduler for automated email follow-ups.

Plans and sends follow-up emails based on configured intervals.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from loguru import logger

try:
    from src.notifications.smtp_client import SMTPSender, SMTPConfig
    SMTP_AVAILABLE = True
except ImportError:
    SMTP_AVAILABLE = False
    logger.warning("SMTP client not available - follow-up emails disabled")


class FollowUpStatus(Enum):
    """Status of a follow-up."""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class FollowUp:
    """Represents a scheduled follow-up."""
    id: str
    contact_id: str
    company_name: str
    email: str
    followup_num: int  # 1 or 2
    scheduled_date: datetime
    status: str = FollowUpStatus.PENDING.value
    sent_at: Optional[datetime] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'contact_id': self.contact_id,
            'company_name': self.company_name,
            'email': self.email,
            'followup_num': self.followup_num,
            'scheduled_date': self.scheduled_date.isoformat() if self.scheduled_date else None,
            'status': self.status,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'error': self.error,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FollowUp':
        """Create from dictionary."""
        return cls(
            id=data.get('id', ''),
            contact_id=data.get('contact_id', ''),
            company_name=data.get('company_name', ''),
            email=data.get('email', ''),
            followup_num=data.get('followup_num', 1),
            scheduled_date=datetime.fromisoformat(data['scheduled_date']) if data.get('scheduled_date') else None,
            status=data.get('status', FollowUpStatus.PENDING.value),
            sent_at=datetime.fromisoformat(data['sent_at']) if data.get('sent_at') else None,
            error=data.get('error'),
            metadata=data.get('metadata', {})
        )


class FollowUpScheduler:
    """
    Scheduler for automated follow-up emails.

    Features:
    - Schedule follow-ups based on intervals (default: Day 7 and Day 14)
    - Track follow-up status
    - Send follow-up emails via SMTP
    - Prevent duplicate follow-ups
    """

    # Default intervals in days
    DEFAULT_INTERVALS = [7, 14]  # First follow-up at day 7, second at day 14

    def __init__(
        self,
        smtp_sender: Optional[SMTPSender] = None,
        intervals: Optional[List[int]] = None,
        data_dir: str = "data"
    ):
        """
        Initialize follow-up scheduler.

        Args:
            smtp_sender: SMTP sender instance for sending emails
            intervals: List of days for follow-ups (default: [7, 14])
            data_dir: Directory for storing follow-up data
        """
        self.smtp_sender = smtp_sender
        self.intervals = intervals or self.DEFAULT_INTERVALS
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.followups: List[FollowUp] = []
        self._load_followups()

        logger.info(f"FollowUpScheduler initialized with intervals: {self.intervals}")

    def _load_followups(self) -> None:
        """Load follow-ups from storage."""
        import json

        followups_file = self.data_dir / "followups.json"
        if followups_file.exists():
            try:
                with open(followups_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.followups = [FollowUp.from_dict(item) for item in data]
                logger.info(f"Loaded {len(self.followups)} follow-ups")
            except Exception as e:
                logger.error(f"Failed to load follow-ups: {e}")
                self.followups = []

    def _save_followups(self) -> None:
        """Save follow-ups to storage."""
        import json

        followups_file = self.data_dir / "followups.json"
        try:
            data = [f.to_dict() for f in self.followups]
            with open(followups_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save follow-ups: {e}")

    def schedule_followup(
        self,
        contact_id: str,
        company_name: str,
        email: str,
        initial_email_date: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[FollowUp]:
        """
        Schedule follow-ups for a contact.

        Args:
            contact_id: Contact ID
            company_name: Company name
            email: Email address
            initial_email_date: Date of initial email (default: now)
            metadata: Additional metadata

        Returns:
            List of scheduled follow-ups
        """
        import uuid

        initial_email_date = initial_email_date or datetime.now()
        scheduled = []

        for i, days in enumerate(self.intervals):
            followup_id = f"{contact_id}-fu{i+1}"
            
            # Check if already scheduled
            existing = next(
                (f for f in self.followups if f.id == followup_id),
                None
            )
            if existing:
                logger.debug(f"Follow-up {followup_id} already exists")
                continue

            scheduled_date = initial_email_date + timedelta(days=days)

            followup = FollowUp(
                id=followup_id,
                contact_id=contact_id,
                company_name=company_name,
                email=email,
                followup_num=i + 1,
                scheduled_date=scheduled_date,
                status=FollowUpStatus.SCHEDULED.value,
                metadata=metadata or {}
            )

            self.followups.append(followup)
            scheduled.append(followup)
            logger.info(
                f"Scheduled follow-up {i+1} for {company_name} "
                f"on {scheduled_date.strftime('%Y-%m-%d')}"
            )

        if scheduled:
            self._save_followups()

        return scheduled

    def get_pending_followups(self, include_today: bool = True) -> List[FollowUp]:
        """
        Get follow-ups that are due.

        Args:
            include_today: Whether to include follow-ups scheduled for today

        Returns:
            List of pending follow-ups
        """
        now = datetime.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)

        pending = []
        for f in self.followups:
            if f.status not in [FollowUpStatus.SCHEDULED.value, FollowUpStatus.PENDING.value]:
                continue

            scheduled_day = f.scheduled_date.replace(hour=0, minute=0, second=0, microsecond=0)
            
            if include_today:
                # Due if scheduled date is today or in the past
                if scheduled_day <= today:
                    pending.append(f)
            else:
                # Due only if scheduled date is in the past
                if f.scheduled_date < now:
                    pending.append(f)

        return pending

    def skip_responded(
        self,
        responded_emails: List[str]
    ) -> int:
        """
        Skip follow-ups for contacts that have responded.

        Args:
            responded_emails: List of email addresses that responded

        Returns:
            Number of follow-ups skipped
        """
        skipped = 0
        responded_lower = {e.lower() for e in responded_emails}

        for f in self.followups:
            if f.status not in [FollowUpStatus.SCHEDULED.value, FollowUpStatus.PENDING.value]:
                continue

            if f.email.lower() in responded_lower:
                f.status = FollowUpStatus.CANCELLED.value
                f.error = "Contact responded - follow-up cancelled"
                skipped += 1
                logger.info(f"Cancelled follow-up for {f.email} - contact responded")

        if skipped > 0:
            self._save_followups()
            logger.info(f"Cancelled {skipped} follow-ups for responded contacts")

        return skipped

    def get_responded_contacts(self) -> List[str]:
        """
        Get list of contacts that have responded (follow-ups cancelled).

        Returns:
            List of email addresses that have responded
        """
        responded = []
        for f in self.followups:
            if f.status == FollowUpStatus.CANCELLED.value and "responded" in (f.error or "").lower():
                responded.append(f.email)
        return list(set(responded))

    async def send_followup(
        self,
        followup: FollowUp,
        subject: str,
        body: str
    ) -> bool:
        """
        Send a follow-up email.

        Args:
            followup: Follow-up to send
            subject: Email subject
            body: Email body (HTML)

        Returns:
            True if sent successfully
        """
        if not SMTP_AVAILABLE or not self.smtp_sender:
            logger.warning("SMTP not available - cannot send follow-up")
            followup.status = FollowUpStatus.FAILED.value
            followup.error = "SMTP not available"
            self._save_followups()
            return False

        try:
            success = await self.smtp_sender.send_email(
                to=followup.email,
                subject=subject,
                body=body,
                html=True
            )

            if success:
                followup.status = FollowUpStatus.SENT.value
                followup.sent_at = datetime.now()
                logger.info(f"Follow-up {followup.id} sent to {followup.email}")
            else:
                followup.status = FollowUpStatus.FAILED.value
                followup.error = "SMTP send failed"

            self._save_followups()
            return success

        except Exception as e:
            logger.error(f"Failed to send follow-up: {e}")
            followup.status = FollowUpStatus.FAILED.value
            followup.error = str(e)
            self._save_followups()
            return False

    async def process_pending(
        self,
        email_generator=None,
        max_send: int = 50
    ) -> Dict[str, Any]:
        """
        Process all pending follow-ups.

        Args:
            email_generator: EmailGenerator instance for creating follow-up emails
            max_send: Maximum number of follow-ups to send

        Returns:
            Summary of processed follow-ups
        """
        pending = self.get_pending_followups()
        results = {
            'total_pending': len(pending),
            'sent': 0,
            'failed': 0,
            'skipped': 0
        }

        if not pending:
            logger.info("No pending follow-ups")
            return results

        logger.info(f"Processing {len(pending)} pending follow-ups")

        for followup in pending[:max_send]:
            if followup.status == FollowUpStatus.SENT.value:
                results['skipped'] += 1
                continue

            # Generate follow-up email content
            template_name = f"follow_up_{followup.followup_num}"

            if email_generator:
                # Create a minimal contact object for the generator
                class MockContact:
                    def __init__(self, data):
                        for key, value in data.items():
                            setattr(self, key, value)

                contact = MockContact(followup.metadata or {})
                contact.company_name = followup.company_name
                contact.email = followup.email

                draft = email_generator.generate(contact, template_name)
                if draft:
                    success = await self.send_followup(
                        followup,
                        draft.subject,
                        draft.body
                    )
                else:
                    success = False
                    followup.error = "Failed to generate email"
                    self._save_followups()
            else:
                # Use generic follow-up content
                subject = f"Nachfrage: Zusammenarbeit mit {followup.company_name}"
                body = f"<p>Sehr geehrte Damen und Herren,</p><p>Folge-E-Mail {followup.followup_num}...</p>"
                success = await self.send_followup(followup, subject, body)

            if success:
                results['sent'] += 1
            else:
                results['failed'] += 1

            # Rate limiting
            await asyncio.sleep(10)

        return results

    def cancel_followups(self, contact_id: str) -> int:
        """
        Cancel all follow-ups for a contact.

        Args:
            contact_id: Contact ID

        Returns:
            Number of cancelled follow-ups
        """
        cancelled = 0
        for f in self.followups:
            if f.contact_id == contact_id and f.status in [
                FollowUpStatus.SCHEDULED.value,
                FollowUpStatus.PENDING.value
            ]:
                f.status = FollowUpStatus.CANCELLED.value
                cancelled += 1

        if cancelled > 0:
            self._save_followups()
            logger.info(f"Cancelled {cancelled} follow-ups for contact {contact_id}")

        return cancelled

    def get_stats(self) -> Dict[str, Any]:
        """Get follow-up statistics."""
        stats = {
            'total': len(self.followups),
            'scheduled': 0,
            'sent': 0,
            'failed': 0,
            'cancelled': 0,
            'by_interval': {}
        }

        for f in self.followups:
            stats[f.status] = stats.get(f.status, 0) + 1

            interval_key = f"day_{self.intervals[f.followup_num - 1] if f.followup_num <= len(self.intervals) else 'unknown'}"
            if interval_key not in stats['by_interval']:
                stats['by_interval'][interval_key] = 0
            stats['by_interval'][interval_key] += 1

        return stats
