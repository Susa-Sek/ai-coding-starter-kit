"""
Tests for follow-up module.
"""

import pytest
from datetime import datetime, timedelta

from src.followup.tracker import FollowUpTracker, FollowUpState, ContactState
from src.followup.generator import FollowUpGenerator
from src.scrapers.base import ScraperResult


class TestFollowUpTracker:
    """Tests for FollowUpTracker."""

    @pytest.fixture
    def tracker(self):
        """Create tracker instance."""
        return FollowUpTracker()

    def test_add_contact(self, tracker):
        """Test adding a contact."""
        state = tracker.add_contact(
            contact_id="test-1",
            company_name="Test GmbH"
        )

        assert state.contact_id == "test-1"
        assert state.company_name == "Test GmbH"
        assert state.state == FollowUpState.NEW

    def test_add_duplicate_contact(self, tracker):
        """Test adding duplicate contact."""
        tracker.add_contact("test-1", "Test GmbH")
        state = tracker.add_contact("test-1", "Test GmbH")

        # Should return existing contact
        assert state.contact_id == "test-1"

    def test_mark_contacted(self, tracker):
        """Test marking as contacted."""
        tracker.add_contact("test-1", "Test GmbH")
        state = tracker.mark_contacted("test-1")

        assert state.state == FollowUpState.CONTACTED
        assert state.email_sent is True
        assert state.next_followup is not None

    def test_mark_followup_sent(self, tracker):
        """Test marking follow-up as sent."""
        tracker.add_contact("test-1", "Test GmbH")
        tracker.mark_contacted("test-1")

        state = tracker.mark_followup_sent("test-1", 1)
        assert state.state == FollowUpState.FOLLOWUP_1

        state = tracker.mark_followup_sent("test-1", 2)
        assert state.state == FollowUpState.FOLLOWUP_2

    def test_mark_replied(self, tracker):
        """Test marking as replied."""
        tracker.add_contact("test-1", "Test GmbH")
        state = tracker.mark_replied("test-1")

        assert state.state == FollowUpState.REPLIED
        assert state.replied is True

    def test_mark_meeting(self, tracker):
        """Test marking meeting scheduled."""
        tracker.add_contact("test-1", "Test GmbH")
        state = tracker.mark_meeting("test-1")

        assert state.state == FollowUpState.MEETING

    def test_mark_closed(self, tracker):
        """Test marking deal closed."""
        tracker.add_contact("test-1", "Test GmbH")
        state = tracker.mark_closed("test-1")

        assert state.state == FollowUpState.CLOSED

    def test_mark_no_response(self, tracker):
        """Test marking no response."""
        tracker.add_contact("test-1", "Test GmbH")
        state = tracker.mark_no_response("test-1")

        assert state.state == FollowUpState.NO_RESPONSE

    def test_mark_opt_out(self, tracker):
        """Test marking opt out."""
        tracker.add_contact("test-1", "Test GmbH")
        state = tracker.mark_opt_out("test-1")

        assert state.state == FollowUpState.OPT_OUT

    def test_get_due_followups(self, tracker):
        """Test getting due follow-ups."""
        # Add contact with past follow-up date
        tracker.add_contact("test-1", "Test GmbH")
        state = tracker.mark_contacted("test-1")
        # Manually set next_followup to past
        state.next_followup = datetime.now() - timedelta(days=1)

        due = tracker.get_due_followups()
        assert len(due) == 1
        assert due[0].contact_id == "test-1"

    def test_get_contacts_by_state(self, tracker):
        """Test getting contacts by state."""
        tracker.add_contact("test-1", "Test A")
        tracker.add_contact("test-2", "Test B")
        tracker.mark_contacted("test-1")

        new_contacts = tracker.get_contacts_by_state(FollowUpState.NEW)
        contacted = tracker.get_contacts_by_state(FollowUpState.CONTACTED)

        assert len(new_contacts) == 1
        assert len(contacted) == 1

    def test_get_statistics(self, tracker):
        """Test getting statistics."""
        tracker.add_contact("test-1", "Test A")
        tracker.add_contact("test-2", "Test B")
        tracker.mark_contacted("test-1")
        tracker.mark_replied("test-2")

        stats = tracker.get_statistics()
        assert stats['new'] == 0
        assert stats['contacted'] == 1
        assert stats['replied'] == 1

    def test_export_import_state(self, tracker):
        """Test exporting and importing state."""
        tracker.add_contact("test-1", "Test A")
        tracker.mark_contacted("test-1")
        tracker.add_contact("test-2", "Test B")

        # Export
        exported = tracker.export_state()
        assert len(exported) == 2

        # Import to new tracker
        new_tracker = FollowUpTracker()
        count = new_tracker.import_state(exported)
        assert count == 2

        # Verify state preserved
        state = new_tracker.get_contact("test-1")
        assert state.state == FollowUpState.CONTACTED

    def test_process_overdue(self, tracker):
        """Test processing overdue contacts."""
        tracker.add_contact("test-1", "Test A")
        tracker.mark_contacted("test-1")
        tracker.mark_followup_sent("test-1", 1)
        tracker.mark_followup_sent("test-1", 2)

        # Manually set old last_contact
        state = tracker.get_contact("test-1")
        state.last_contact = datetime.now() - timedelta(days=10)

        overdue = tracker.process_overdue()
        assert len(overdue) == 1
        assert overdue[0].state == FollowUpState.NO_RESPONSE


class TestFollowUpGenerator:
    """Tests for FollowUpGenerator."""

    @pytest.fixture
    def generator(self):
        """Create generator instance."""
        return FollowUpGenerator()

    @pytest.fixture
    def sample_contact(self):
        """Create sample contact."""
        return ScraperResult(
            source="test",
            company_name="Test GmbH",
            email="info@test.de",
            phone="+49713112345",
            address="Heilbronn"
        )

    def test_template_map(self, generator):
        """Test template mapping."""
        assert generator.TEMPLATE_MAP[1] == 'follow_up_1'
        assert generator.TEMPLATE_MAP[2] == 'follow_up_2'

    def test_generate_followup_1(self, generator, sample_contact):
        """Test generating first follow-up."""
        draft = generator.generate_followup(
            contact=sample_contact,
            followup_number=1,
            days_since_contact=7
        )

        assert draft is not None
        assert draft.company_name == sample_contact.company_name
        assert draft.template_used == 'follow_up_1'
        assert draft.metadata['followup_number'] == 1

    def test_generate_followup_2(self, generator, sample_contact):
        """Test generating second follow-up."""
        draft = generator.generate_followup(
            contact=sample_contact,
            followup_number=2,
            days_since_contact=14
        )

        assert draft is not None
        assert draft.template_used == 'follow_up_2'
        assert draft.metadata['followup_number'] == 2

    def test_generate_followup_invalid_number(self, generator, sample_contact):
        """Test with invalid follow-up number."""
        draft = generator.generate_followup(
            contact=sample_contact,
            followup_number=3,
            days_since_contact=21
        )

        assert draft is None

    def test_generate_followup_no_email(self, generator):
        """Test with contact without email."""
        contact = ScraperResult(
            source="test",
            company_name="Test GmbH"
        )

        draft = generator.generate_followup(
            contact=contact,
            followup_number=1,
            days_since_contact=7
        )

        assert draft is None

    def test_get_template_for_state(self, generator):
        """Test getting template for state."""
        assert generator.get_template_for_state(FollowUpState.CONTACTED) == 'follow_up_1'
        assert generator.get_template_for_state(FollowUpState.FOLLOWUP_1) == 'follow_up_2'
        assert generator.get_template_for_state(FollowUpState.NEW) is None

    def test_get_followup_number_for_state(self, generator):
        """Test getting follow-up number for state."""
        assert generator.get_followup_number_for_state(FollowUpState.CONTACTED) == 1
        assert generator.get_followup_number_for_state(FollowUpState.FOLLOWUP_1) == 2
        assert generator.get_followup_number_for_state(FollowUpState.NEW) is None

    def test_should_send_followup(self, generator):
        """Test should send follow-up check."""
        assert generator.should_send_followup(FollowUpState.CONTACTED, 7) is True
        assert generator.should_send_followup(FollowUpState.CONTACTED, 6) is False
        assert generator.should_send_followup(FollowUpState.FOLLOWUP_1, 7) is True
        assert generator.should_send_followup(FollowUpState.NEW, 7) is False

    def test_get_days_until_next_followup(self, generator):
        """Test days until next follow-up calculation."""
        assert generator.get_days_until_next_followup(FollowUpState.CONTACTED, 5) == 2
        assert generator.get_days_until_next_followup(FollowUpState.CONTACTED, 7) == 0
        assert generator.get_days_until_next_followup(FollowUpState.CONTACTED, 10) == -3

    def test_create_followup_summary(self, generator, sample_contact):
        """Test creating follow-up summary."""
        summary = generator.create_followup_summary(
            contact=sample_contact,
            followup_number=1,
            days_since_contact=7
        )

        assert summary['company_name'] == sample_contact.company_name
        assert summary['email'] == sample_contact.email
        assert summary['followup_number'] == 1
        assert summary['days_since_contact'] == 7
        assert 'generated_at' in summary


class TestContactState:
    """Tests for ContactState dataclass."""

    def test_create_state(self):
        """Test creating contact state."""
        state = ContactState(
            contact_id="test-1",
            company_name="Test GmbH"
        )

        assert state.contact_id == "test-1"
        assert state.state == FollowUpState.NEW
        assert state.followup_count == 0

    def test_to_dict(self):
        """Test converting to dictionary."""
        state = ContactState(
            contact_id="test-1",
            company_name="Test GmbH",
            state=FollowUpState.CONTACTED,
            email_sent=True
        )

        data = state.to_dict()
        assert data['contact_id'] == "test-1"
        assert data['state'] == "contacted"
        assert data['email_sent'] is True

    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            'contact_id': 'test-1',
            'company_name': 'Test GmbH',
            'state': 'contacted',
            'created_at': datetime.now().isoformat(),
            'last_contact': datetime.now().isoformat(),
            'next_followup': None,
            'followup_count': 1,
            'email_sent': True,
            'replied': False,
            'metadata': {}
        }

        state = ContactState.from_dict(data)
        assert state.contact_id == "test-1"
        assert state.state == FollowUpState.CONTACTED
        assert state.followup_count == 1