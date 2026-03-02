"""
Follow-up email generator that integrates with EmailGenerator.
"""

from typing import Optional, Dict, Any
from datetime import datetime

from loguru import logger
from src.generators.email_generator import EmailGenerator, EmailDraft
from src.scrapers.base import ScraperResult
from src.followup.tracker import FollowUpState


class FollowUpGenerator:
    """
    Generates follow-up emails based on contact state.

    Integrates with EmailGenerator for template-based emails.
    """

    # Template mapping
    TEMPLATE_MAP = {
        1: 'follow_up_1',
        2: 'follow_up_2'
    }

    def __init__(self, email_generator: Optional[EmailGenerator] = None):
        """
        Initialize follow-up generator.

        Args:
            email_generator: EmailGenerator instance for templates
        """
        self.email_generator = email_generator or EmailGenerator()

    def generate_followup(
        self,
        contact: ScraperResult,
        followup_number: int,
        days_since_contact: int,
        previous_status: str = ""
    ) -> Optional[EmailDraft]:
        """
        Generate a follow-up email.

        Args:
            contact: Contact data
            followup_number: Follow-up number (1 or 2)
            days_since_contact: Days since initial contact
            previous_status: Previous contact status

        Returns:
            EmailDraft or None if generation fails
        """
        if followup_number not in self.TEMPLATE_MAP:
            logger.error(f"Invalid follow-up number: {followup_number}")
            return None

        if not contact.email:
            logger.warning(f"Contact {contact.company_name} has no email")
            return None

        template_name = self.TEMPLATE_MAP[followup_number]

        # Create custom context for follow-up
        custom_context = {
            'followup_number': followup_number,
            'days_since_contact': days_since_contact,
            'previous_status': previous_status
        }

        draft = self.email_generator.generate(
            contact,
            template_name=template_name,
            custom_context=custom_context
        )

        if draft:
            # Add follow-up metadata
            draft.metadata['followup_number'] = followup_number
            draft.metadata['days_since_contact'] = days_since_contact
            draft.metadata['previous_status'] = previous_status
            logger.info(
                f"Generated follow-up #{followup_number} for {contact.company_name}"
            )

        return draft

    def get_template_for_state(self, state: FollowUpState) -> Optional[str]:
        """
        Get appropriate template for a follow-up state.

        Args:
            state: Current follow-up state

        Returns:
            Template name or None
        """
        if state == FollowUpState.CONTACTED:
            return self.TEMPLATE_MAP[1]
        elif state == FollowUpState.FOLLOWUP_1:
            return self.TEMPLATE_MAP[2]
        else:
            return None

    def get_followup_number_for_state(self, state: FollowUpState) -> Optional[int]:
        """
        Get follow-up number for a state.

        Args:
            state: Current follow-up state

        Returns:
            Follow-up number (1 or 2) or None
        """
        if state == FollowUpState.CONTACTED:
            return 1
        elif state == FollowUpState.FOLLOWUP_1:
            return 2
        else:
            return None

    def should_send_followup(
        self,
        state: FollowUpState,
        days_since_contact: int
    ) -> bool:
        """
        Check if follow-up should be sent.

        Args:
            state: Current follow-up state
            days_since_contact: Days since last contact

        Returns:
            True if follow-up should be sent
        """
        if state == FollowUpState.CONTACTED and days_since_contact >= 7:
            return True
        elif state == FollowUpState.FOLLOWUP_1 and days_since_contact >= 7:
            return True
        return False

    def get_days_until_next_followup(
        self,
        state: FollowUpState,
        days_since_contact: int
    ) -> int:
        """
        Get days until next follow-up is due.

        Args:
            state: Current follow-up state
            days_since_contact: Days since last contact

        Returns:
            Days until next follow-up (0 if due now, negative if overdue)
        """
        if state == FollowUpState.CONTACTED:
            return 7 - days_since_contact
        elif state == FollowUpState.FOLLOWUP_1:
            return 7 - days_since_contact
        else:
            return 0  # No follow-up scheduled

    def create_followup_summary(
        self,
        contact: ScraperResult,
        followup_number: int,
        days_since_contact: int
    ) -> Dict[str, Any]:
        """
        Create a summary of follow-up for Telegram notification.

        Args:
            contact: Contact data
            followup_number: Follow-up number
            days_since_contact: Days since contact

        Returns:
            Summary dictionary
        """
        return {
            'company_name': contact.company_name,
            'email': contact.email,
            'phone': contact.phone,
            'address': contact.address,
            'units': contact.units,
            'followup_number': followup_number,
            'days_since_contact': days_since_contact,
            'generated_at': datetime.now().isoformat()
        }