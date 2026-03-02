"""
Sync manager for coordinating data between components.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

from loguru import logger

from .models import Contact, FollowUp, ContactStatus
from .sheets import GoogleSheetsClient
from src.scrapers.base import ScraperResult
from src.enrichment.quality_scorer import QualityScorer
from src.generators.email_generator import EmailGenerator


@dataclass
class SyncResult:
    """Result of a sync operation."""
    added: int = 0
    updated: int = 0
    duplicates: int = 0
    errors: int = 0
    details: List[str] = None

    def __post_init__(self):
        if self.details is None:
            self.details = []


class SyncManager:
    """
    Manages synchronization between scrapers, enrichment, and storage.

    Features:
    - Import scraper results to Google Sheets
    - Update contact statuses
    - Sync follow-up states
    - Generate email drafts
    """

    def __init__(
        self,
        sheets_client: Optional[GoogleSheetsClient] = None,
        quality_scorer: Optional[QualityScorer] = None,
        email_generator: Optional[EmailGenerator] = None
    ):
        """
        Initialize sync manager.

        Args:
            sheets_client: Google Sheets client
            quality_scorer: Quality scorer for leads
            email_generator: Email generator for drafts
        """
        self.sheets = sheets_client
        self.scorer = quality_scorer or QualityScorer()
        self.generator = email_generator or EmailGenerator()

    def sync_scraper_results(
        self,
        results: List[ScraperResult],
        generate_emails: bool = True,
        skip_duplicates: bool = True
    ) -> SyncResult:
        """
        Sync scraper results to Google Sheets.

        Args:
            results: List of scraper results
            generate_emails: Whether to generate email drafts
            skip_duplicates: Whether to skip duplicates

        Returns:
            SyncResult with counts
        """
        sync_result = SyncResult()

        if not self.sheets or not self.sheets.is_available:
            logger.warning("Google Sheets not available - skipping sync")
            sync_result.errors = len(results)
            sync_result.details.append("Google Sheets not available")
            return sync_result

        contacts_to_add = []

        for result in results:
            # Calculate quality score
            score = self.scorer.calculate_score(result)
            grade = self.scorer.classify(score)

            # Create contact
            contact = Contact.from_scraper_result(result, score, grade.value)

            # Check for duplicates
            if skip_duplicates:
                duplicate = self.sheets.find_duplicate(contact)
                if duplicate:
                    sync_result.duplicates += 1
                    sync_result.details.append(f"Duplicate: {contact.company_name} (existing ID: {duplicate.id})")
                    continue

            # Generate email draft
            if generate_emails and contact.email:
                draft = self.generator.generate(contact)
                if draft:
                    contact.email_draft = draft.body[:500]  # Truncate for storage

            # Calculate follow-up dates
            contact.follow_up_1 = datetime.now() + timedelta(days=7)
            contact.follow_up_2 = datetime.now() + timedelta(days=14)

            contacts_to_add.append(contact)

        # Batch add contacts
        if contacts_to_add:
            added = self.sheets.add_contacts_batch(contacts_to_add)
            sync_result.added = added

            # Create follow-ups for each contact
            for contact in contacts_to_add[:added]:
                self._create_followups(contact)

        return sync_result

    def _create_followups(self, contact: Contact) -> None:
        """Create follow-up entries for a contact."""
        if not self.sheets or not contact.id:
            return

        # First follow-up
        followup_1 = FollowUp(
            contact_id=contact.id,
            followup_type=1,
            scheduled_date=contact.follow_up_1,
            status="Offen"
        )
        self.sheets.add_followup(followup_1)

        # Second follow-up
        followup_2 = FollowUp(
            contact_id=contact.id,
            followup_type=2,
            scheduled_date=contact.follow_up_2,
            status="Offen"
        )
        self.sheets.add_followup(followup_2)

    def update_status(
        self,
        contact_id: str,
        status: ContactStatus,
        notes: Optional[str] = None
    ) -> bool:
        """
        Update contact status.

        Args:
            contact_id: Contact ID
            status: New status
            notes: Optional notes

        Returns:
            True if successful
        """
        if not self.sheets:
            return False

        success = self.sheets.update_contact_status(contact_id, status)
        if success and notes:
            # Get contact and update notes
            contact = self.sheets.get_contact(contact_id)
            if contact:
                contact.notes = notes
                self.sheets.update_contact(contact)

        return success

    def get_due_followups(self) -> List[Dict[str, Any]]:
        """
        Get follow-ups that are due today.

        Returns:
            List of due follow-ups with contact info
        """
        if not self.sheets:
            return []

        followups = self.sheets.get_open_followups()
        today = datetime.now().date()
        due = []

        for followup in followups:
            if followup.scheduled_date:
                followup_date = followup.scheduled_date.date()
                if followup_date <= today:
                    contact = self.sheets.get_contact(followup.contact_id)
                    if contact:
                        due.append({
                            'followup': followup,
                            'contact': contact,
                            'days_overdue': (today - followup_date).days
                        })

        return due

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics from the sheet.

        Returns:
            Dictionary with statistics
        """
        if not self.sheets:
            return {}

        contacts = self.sheets.get_all_contacts()

        stats = {
            'total': len(contacts),
            'by_status': {},
            'by_qualification': {'A': 0, 'B': 0, 'C': 0},
            'with_email': 0,
            'with_phone': 0,
            'contacted': 0,
            'replied': 0
        }

        for contact in contacts:
            # By status
            status = contact.status.value
            stats['by_status'][status] = stats['by_status'].get(status, 0) + 1

            # By qualification
            if contact.qualification in stats['by_qualification']:
                stats['by_qualification'][contact.qualification] += 1

            # With contact info
            if contact.email:
                stats['with_email'] += 1
            if contact.phone:
                stats['with_phone'] += 1

            # Response stats
            if contact.status in [ContactStatus.CONTACTED, ContactStatus.REPLIED,
                                   ContactStatus.MEETING]:
                stats['contacted'] += 1
            if contact.status in [ContactStatus.REPLIED, ContactStatus.MEETING]:
                stats['replied'] += 1

        return stats

    def export_contacts(
        self,
        status: Optional[ContactStatus] = None,
        qualification: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[Contact]:
        """
        Export contacts with optional filters.

        Args:
            status: Filter by status
            qualification: Filter by qualification (A, B, C)
            date_from: Filter by creation date (from)
            date_to: Filter by creation date (to)

        Returns:
            Filtered list of contacts
        """
        if not self.sheets:
            return []

        contacts = self.sheets.get_all_contacts()

        # Apply filters
        if status:
            contacts = [c for c in contacts if c.status == status]

        if qualification:
            contacts = [c for c in contacts if c.qualification.upper() == qualification.upper()]

        if date_from:
            contacts = [c for c in contacts if c.created_at and c.created_at >= date_from]

        if date_to:
            contacts = [c for c in contacts if c.created_at and c.created_at <= date_to]

        return contacts

    def mark_followup_done(self, followup_id: str) -> bool:
        """
        Mark a follow-up as completed.

        Args:
            followup_id: Follow-up ID

        Returns:
            True if successful
        """
        if not self.sheets:
            return False

        return self.sheets.mark_followup_completed(followup_id)

    def get_contact_count(self) -> int:
        """Get total contact count."""
        if not self.sheets:
            return 0
        return len(self.sheets.get_all_contacts())

    def get_a_class_contacts(self) -> List[Contact]:
        """Get all A-class contacts."""
        return self.export_contacts(qualification='A')

    def get_new_contacts(self) -> List[Contact]:
        """Get all new (uncontacted) contacts."""
        return self.export_contacts(status=ContactStatus.NEW)