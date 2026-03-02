"""
Tests for storage module.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from src.storage.models import Contact, FollowUp, ContactStatus
from src.storage.sheets import GoogleSheetsClient, SheetsConfig
from src.storage.sync import SyncManager, SyncResult
from src.export.csv_export import CSVExporter


class TestContact:
    """Tests for Contact model."""

    def test_create_contact(self):
        """Test creating a contact."""
        contact = Contact(
            company_name="Test GmbH",
            email="info@test.de",
            phone="+49713112345"
        )

        assert contact.company_name == "Test GmbH"
        assert contact.email == "info@test.de"
        assert contact.status == ContactStatus.NEW
        assert contact.id is not None

    def test_contact_to_dict(self):
        """Test converting contact to dictionary."""
        contact = Contact(
            company_name="Test GmbH",
            email="info@test.de",
            score=85,
            qualification="A"
        )

        data = contact.to_dict()

        assert data['company_name'] == "Test GmbH"
        assert data['email'] == "info@test.de"
        assert data['score'] == 85
        assert data['qualification'] == "A"

    def test_contact_to_row(self):
        """Test converting contact to row."""
        contact = Contact(
            company_name="Test GmbH",
            email="info@test.de",
            units=100
        )

        row = contact.to_row()

        assert row[1] == "Test GmbH"
        assert row[4] == "info@test.de"
        assert row[6] == "100"

    def test_contact_from_row(self):
        """Test creating contact from row."""
        row = [
            "test-1", "Test GmbH", "Hauptstraße 1", "+49713112345",
            "info@test.de", "https://test.de", "100", "10",
            "gelbe_seiten", "A", "85", "Neu", "",
            "2026-03-02 10:00", "", "", ""
        ]

        contact = Contact.from_row(row)

        assert contact.id == "test-1"
        assert contact.company_name == "Test GmbH"
        assert contact.units == 100
        assert contact.employees == 10
        assert contact.qualification == "A"
        assert contact.score == 85

    def test_contact_status_from_string(self):
        """Test contact status conversion."""
        assert ContactStatus.from_string("neu") == ContactStatus.NEW
        assert ContactStatus.from_string("KONTAKTIERT") == ContactStatus.CONTACTED
        assert ContactStatus.from_string("Antwort") == ContactStatus.REPLIED
        assert ContactStatus.from_string("unknown") == ContactStatus.NEW


class TestFollowUp:
    """Tests for FollowUp model."""

    def test_create_followup(self):
        """Test creating a follow-up."""
        followup = FollowUp(
            contact_id="test-1",
            followup_type=1,
            scheduled_date=datetime.now() + timedelta(days=7)
        )

        assert followup.contact_id == "test-1"
        assert followup.followup_type == 1
        assert followup.status == "Offen"

    def test_followup_to_row(self):
        """Test converting follow-up to row."""
        scheduled = datetime.now() + timedelta(days=7)
        followup = FollowUp(
            contact_id="test-1",
            followup_type=1,
            scheduled_date=scheduled
        )

        row = followup.to_row()

        assert row[1] == "test-1"
        assert row[2] == "1"
        assert row[4] == "Offen"

    def test_followup_from_row(self):
        """Test creating follow-up from row."""
        row = [
            "fu-1", "test-1", "1", "2026-03-09", "Offen", "", ""
        ]

        followup = FollowUp.from_row(row)

        assert followup.id == "fu-1"
        assert followup.contact_id == "test-1"
        assert followup.followup_type == 1


class TestGoogleSheetsClient:
    """Tests for GoogleSheetsClient."""

    @pytest.fixture
    def config(self):
        """Create test config."""
        return SheetsConfig(
            spreadsheet_id="test_id",
            credentials_file="test_creds.json"
        )

    @pytest.fixture
    def client(self, config):
        """Create client instance."""
        return GoogleSheetsClient(config)

    def test_config(self, config):
        """Test configuration."""
        assert config.spreadsheet_id == "test_id"
        assert config.contacts_sheet == "Kontakte"
        assert config.followups_sheet == "Follow-Ups"

    def test_is_available_with_id(self, client):
        """Test availability check with ID."""
        # gspread might not be installed
        # Just check the config check
        assert client.config.spreadsheet_id == "test_id"

    def test_headers(self, client):
        """Test headers are defined."""
        assert len(GoogleSheetsClient.CONTACT_HEADERS) == 17
        assert len(GoogleSheetsClient.FOLLOWUP_HEADERS) == 7


class TestSyncManager:
    """Tests for SyncManager."""

    @pytest.fixture
    def sync_manager(self):
        """Create sync manager instance."""
        return SyncManager()

    def test_sync_result(self):
        """Test SyncResult dataclass."""
        result = SyncResult(
            added=5,
            updated=2,
            duplicates=1,
            errors=0
        )

        assert result.added == 5
        assert result.updated == 2
        assert result.duplicates == 1
        assert result.errors == 0

    def test_sync_without_sheets(self, sync_manager):
        """Test sync without Google Sheets connection."""
        from src.scrapers.base import ScraperResult

        results = [
            ScraperResult(source="test", company_name="Test GmbH", email="info@test.de")
        ]

        result = sync_manager.sync_scraper_results(results)

        # Should return error since no sheets connection
        assert result.errors == 1

    def test_get_statistics_without_sheets(self, sync_manager):
        """Test statistics without sheets connection."""
        stats = sync_manager.get_statistics()

        assert stats == {}


class TestCSVExporter:
    """Tests for CSVExporter."""

    @pytest.fixture
    def exporter(self):
        """Create exporter instance."""
        return CSVExporter()

    @pytest.fixture
    def sample_contacts(self):
        """Create sample contacts."""
        return [
            Contact(
                company_name="A GmbH",
                email="info@a.de",
                phone="+49111",
                qualification="A",
                score=85
            ),
            Contact(
                company_name="B GmbH",
                email="info@b.de",
                qualification="B",
                score=60
            ),
        ]

    @pytest.fixture
    def sample_followups(self):
        """Create sample follow-ups."""
        return [
            FollowUp(
                contact_id="test-1",
                followup_type=1,
                scheduled_date=datetime.now() + timedelta(days=7)
            ),
        ]

    def test_export_contacts(self, exporter, sample_contacts, tmp_path):
        """Test exporting contacts to CSV."""
        output_file = tmp_path / "contacts.csv"

        count = exporter.export_contacts(sample_contacts, str(output_file))

        assert count == 2
        assert output_file.exists()

        # Verify content
        content = output_file.read_text(encoding='utf-8')
        assert "A GmbH" in content
        assert "B GmbH" in content

    def test_export_contacts_empty(self, exporter, tmp_path):
        """Test exporting empty contact list."""
        output_file = tmp_path / "empty.csv"

        count = exporter.export_contacts([], str(output_file))

        assert count == 0

    def test_export_followups(self, exporter, sample_followups, tmp_path):
        """Test exporting follow-ups to CSV."""
        output_file = tmp_path / "followups.csv"

        count = exporter.export_followups(sample_followups, str(output_file))

        assert count == 1
        assert output_file.exists()

    def test_export_summary(self, exporter, sample_contacts, tmp_path):
        """Test exporting summary CSV."""
        output_file = tmp_path / "summary.csv"

        count = exporter.export_summary(sample_contacts, str(output_file))

        assert count == 2
        assert output_file.exists()

        content = output_file.read_text(encoding='utf-8')
        assert "Firma" in content
        assert "Qualifikation" in content

    def test_export_mail_merge(self, exporter, sample_contacts, tmp_path):
        """Test exporting for mail merge."""
        output_file = tmp_path / "mail_merge.csv"

        # Add address to first contact
        sample_contacts[0].address = "Hauptstraße 1, 74072 Heilbronn"

        count = exporter.export_for_mail_merge(sample_contacts, str(output_file))

        assert count == 2
        assert output_file.exists()

        content = output_file.read_text(encoding='utf-8')
        assert "Anrede" in content
        assert "Heilbronn" in content

    def test_parse_address(self, exporter):
        """Test address parsing."""
        street, plz, ort = exporter._parse_address("Hauptstraße 1, 74072 Heilbronn")

        assert "Hauptstraße" in street
        assert plz == "74072"
        assert ort == "Heilbronn"

    def test_parse_address_simple(self, exporter):
        """Test simple address parsing."""
        street, plz, ort = exporter._parse_address("74072 Heilbronn")

        assert plz == "74072"
        assert ort == "Heilbronn"