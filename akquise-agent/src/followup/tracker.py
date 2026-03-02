"""
Follow-up state tracking for contacts.
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from loguru import logger


class FollowUpState(Enum):
    """Follow-up states for contacts."""
    NEW = "new"  # New contact, not yet contacted
    CONTACTED = "contacted"  # Initial contact made
    FOLLOWUP_1 = "followup_1"  # First follow-up sent (day 7)
    FOLLOWUP_2 = "followup_2"  # Second follow-up sent (day 14)
    REPLIED = "replied"  # Contact replied
    MEETING = "meeting"  # Meeting scheduled
    CLOSED = "closed"  # Deal closed
    NO_RESPONSE = "no_response"  # No response after all follow-ups
    OPT_OUT = "opt_out"  # Contact opted out


@dataclass
class ContactState:
    """State tracking for a single contact."""
    contact_id: str
    company_name: str
    state: FollowUpState = FollowUpState.NEW
    created_at: datetime = field(default_factory=datetime.now)
    last_contact: Optional[datetime] = None
    next_followup: Optional[datetime] = None
    followup_count: int = 0
    email_sent: bool = False
    replied: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'contact_id': self.contact_id,
            'company_name': self.company_name,
            'state': self.state.value,
            'created_at': self.created_at.isoformat(),
            'last_contact': self.last_contact.isoformat() if self.last_contact else None,
            'next_followup': self.next_followup.isoformat() if self.next_followup else None,
            'followup_count': self.followup_count,
            'email_sent': self.email_sent,
            'replied': self.replied,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContactState':
        """Create from dictionary."""
        return cls(
            contact_id=data['contact_id'],
            company_name=data['company_name'],
            state=FollowUpState(data['state']),
            created_at=datetime.fromisoformat(data['created_at']),
            last_contact=datetime.fromisoformat(data['last_contact']) if data.get('last_contact') else None,
            next_followup=datetime.fromisoformat(data['next_followup']) if data.get('next_followup') else None,
            followup_count=data.get('followup_count', 0),
            email_sent=data.get('email_sent', False),
            replied=data.get('replied', False),
            metadata=data.get('metadata', {})
        )


class FollowUpTracker:
    """
    Tracks follow-up states for all contacts.

    State transitions:
    NEW -> CONTACTED (initial email sent)
    CONTACTED -> FOLLOWUP_1 (7 days later)
    FOLLOWUP_1 -> FOLLOWUP_2 (7 days later)
    FOLLOWUP_2 -> NO_RESPONSE (7 days later, no reply)
    Any -> REPLIED (contact replied)
    REPLIED -> MEETING (meeting scheduled)
    MEETING -> CLOSED (deal closed)
    Any -> OPT_OUT (contact opted out)
    """

    # Follow-up intervals in days
    FOLLOWUP_1_DAYS = 7
    FOLLOWUP_2_DAYS = 14
    NO_RESPONSE_DAYS = 21

    def __init__(self):
        """Initialize follow-up tracker."""
        self._contacts: Dict[str, ContactState] = {}

    def add_contact(
        self,
        contact_id: str,
        company_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ContactState:
        """
        Add a new contact to tracking.

        Args:
            contact_id: Unique contact identifier
            company_name: Company name
            metadata: Additional metadata

        Returns:
            ContactState for the new contact
        """
        if contact_id in self._contacts:
            logger.warning(f"Contact {contact_id} already exists")
            return self._contacts[contact_id]

        state = ContactState(
            contact_id=contact_id,
            company_name=company_name,
            metadata=metadata or {}
        )
        self._contacts[contact_id] = state
        logger.info(f"Added contact {company_name} to tracking")
        return state

    def mark_contacted(self, contact_id: str) -> Optional[ContactState]:
        """
        Mark contact as contacted (initial email sent).

        Args:
            contact_id: Contact identifier

        Returns:
            Updated ContactState or None if not found
        """
        if contact_id not in self._contacts:
            logger.warning(f"Contact {contact_id} not found")
            return None

        state = self._contacts[contact_id]
        state.state = FollowUpState.CONTACTED
        state.last_contact = datetime.now()
        state.next_followup = datetime.now() + timedelta(days=self.FOLLOWUP_1_DAYS)
        state.email_sent = True
        logger.info(f"Contact {state.company_name} marked as contacted")
        return state

    def mark_followup_sent(self, contact_id: str, followup_number: int) -> Optional[ContactState]:
        """
        Mark follow-up as sent.

        Args:
            contact_id: Contact identifier
            followup_number: Follow-up number (1 or 2)

        Returns:
            Updated ContactState or None if not found
        """
        if contact_id not in self._contacts:
            logger.warning(f"Contact {contact_id} not found")
            return None

        state = self._contacts[contact_id]
        state.last_contact = datetime.now()
        state.followup_count = max(state.followup_count, followup_number)

        if followup_number == 1:
            state.state = FollowUpState.FOLLOWUP_1
            state.next_followup = datetime.now() + timedelta(days=self.FOLLOWUP_2_DAYS - self.FOLLOWUP_1_DAYS)
        elif followup_number == 2:
            state.state = FollowUpState.FOLLOWUP_2
            state.next_followup = datetime.now() + timedelta(days=self.NO_RESPONSE_DAYS - self.FOLLOWUP_2_DAYS)

        logger.info(f"Follow-up #{followup_number} sent for {state.company_name}")
        return state

    def mark_replied(self, contact_id: str) -> Optional[ContactState]:
        """
        Mark contact as replied.

        Args:
            contact_id: Contact identifier

        Returns:
            Updated ContactState or None if not found
        """
        if contact_id not in self._contacts:
            logger.warning(f"Contact {contact_id} not found")
            return None

        state = self._contacts[contact_id]
        state.state = FollowUpState.REPLIED
        state.replied = True
        state.next_followup = None
        logger.info(f"Contact {state.company_name} replied")
        return state

    def mark_meeting(self, contact_id: str) -> Optional[ContactState]:
        """
        Mark meeting scheduled.

        Args:
            contact_id: Contact identifier

        Returns:
            Updated ContactState or None if not found
        """
        if contact_id not in self._contacts:
            logger.warning(f"Contact {contact_id} not found")
            return None

        state = self._contacts[contact_id]
        state.state = FollowUpState.MEETING
        state.next_followup = None
        logger.info(f"Meeting scheduled with {state.company_name}")
        return state

    def mark_closed(self, contact_id: str) -> Optional[ContactState]:
        """
        Mark deal closed.

        Args:
            contact_id: Contact identifier

        Returns:
            Updated ContactState or None if not found
        """
        if contact_id not in self._contacts:
            logger.warning(f"Contact {contact_id} not found")
            return None

        state = self._contacts[contact_id]
        state.state = FollowUpState.CLOSED
        state.next_followup = None
        logger.info(f"Deal closed with {state.company_name}")
        return state

    def mark_no_response(self, contact_id: str) -> Optional[ContactState]:
        """
        Mark as no response after all follow-ups.

        Args:
            contact_id: Contact identifier

        Returns:
            Updated ContactState or None if not found
        """
        if contact_id not in self._contacts:
            logger.warning(f"Contact {contact_id} not found")
            return None

        state = self._contacts[contact_id]
        state.state = FollowUpState.NO_RESPONSE
        state.next_followup = None
        logger.info(f"No response from {state.company_name}")
        return state

    def mark_opt_out(self, contact_id: str) -> Optional[ContactState]:
        """
        Mark contact as opted out.

        Args:
            contact_id: Contact identifier

        Returns:
            Updated ContactState or None if not found
        """
        if contact_id not in self._contacts:
            logger.warning(f"Contact {contact_id} not found")
            return None

        state = self._contacts[contact_id]
        state.state = FollowUpState.OPT_OUT
        state.next_followup = None
        logger.info(f"Contact {state.company_name} opted out")
        return state

    def get_due_followups(self) -> List[ContactState]:
        """
        Get all contacts with due follow-ups.

        Returns:
            List of contacts needing follow-up
        """
        now = datetime.now()
        due = []

        for state in self._contacts.values():
            if state.next_followup and state.next_followup <= now:
                if state.state in [FollowUpState.CONTACTED, FollowUpState.FOLLOWUP_1]:
                    due.append(state)

        return due

    def get_contact(self, contact_id: str) -> Optional[ContactState]:
        """
        Get contact state by ID.

        Args:
            contact_id: Contact identifier

        Returns:
            ContactState or None if not found
        """
        return self._contacts.get(contact_id)

    def get_all_contacts(self) -> List[ContactState]:
        """
        Get all contact states.

        Returns:
            List of all ContactState objects
        """
        return list(self._contacts.values())

    def get_contacts_by_state(self, state: FollowUpState) -> List[ContactState]:
        """
        Get contacts by state.

        Args:
            state: State to filter by

        Returns:
            List of contacts in the specified state
        """
        return [c for c in self._contacts.values() if c.state == state]

    def get_statistics(self) -> Dict[str, int]:
        """
        Get statistics by state.

        Returns:
            Dictionary with counts by state
        """
        stats = {s.value: 0 for s in FollowUpState}
        for state in self._contacts.values():
            stats[state.state.value] += 1
        return stats

    def process_overdue(self) -> List[ContactState]:
        """
        Process overdue contacts (no response after all follow-ups).

        Returns:
            List of newly marked NO_RESPONSE contacts
        """
        now = datetime.now()
        overdue = []

        for state in self._contacts.values():
            if state.state == FollowUpState.FOLLOWUP_2:
                if state.last_contact:
                    days_since = (now - state.last_contact).days
                    if days_since >= 7:  # 7 days after last follow-up
                        state.state = FollowUpState.NO_RESPONSE
                        state.next_followup = None
                        overdue.append(state)
                        logger.info(f"Marked {state.company_name} as no response")

        return overdue

    def export_state(self) -> List[Dict[str, Any]]:
        """
        Export all contact states.

        Returns:
            List of contact state dictionaries
        """
        return [c.to_dict() for c in self._contacts.values()]

    def import_state(self, data: List[Dict[str, Any]]) -> int:
        """
        Import contact states.

        Args:
            data: List of contact state dictionaries

        Returns:
            Number of contacts imported
        """
        count = 0
        for item in data:
            try:
                state = ContactState.from_dict(item)
                self._contacts[state.contact_id] = state
                count += 1
            except Exception as e:
                logger.error(f"Error importing contact state: {e}")

        logger.info(f"Imported {count} contact states")
        return count