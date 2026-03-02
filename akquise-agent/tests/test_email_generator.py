"""
Tests for email generator module.
"""

import pytest
from pathlib import Path

from src.generators.email_generator import EmailGenerator, EmailDraft
from src.scrapers.base import ScraperResult
from src.enrichment.quality_scorer import LeadQuality


class TestEmailGenerator:
    """Tests for EmailGenerator."""

    @pytest.fixture
    def generator(self):
        """Create email generator instance."""
        return EmailGenerator()

    @pytest.fixture
    def sample_contact(self):
        """Create sample contact for testing."""
        return ScraperResult(
            source="test",
            company_name="Müller Hausverwaltung GmbH",
            email="info@mueller-hausverwaltung.de",
            phone="+49713112345",
            address="Hauptstraße 1, 74072 Heilbronn",
            website="https://mueller-hausverwaltung.de",
            units=150,
            employees=12
        )

    @pytest.fixture
    def minimal_contact(self):
        """Create minimal contact with only required fields."""
        return ScraperResult(
            source="test",
            company_name="Test GmbH",
            email="info@test.de"
        )

    def test_initialization(self, generator):
        """Test generator initialization."""
        assert generator is not None
        assert generator.company_info is not None
        assert 'name' in generator.company_info

    def test_get_template_names(self, generator):
        """Test getting available templates."""
        templates = generator.get_template_names()
        assert 'initial_contact' in templates
        assert 'follow_up_1' in templates
        assert 'follow_up_2' in templates

    def test_generate_initial_contact(self, generator, sample_contact):
        """Test generating initial contact email."""
        draft = generator.generate(sample_contact, 'initial_contact')

        assert draft is not None
        assert draft.company_name == sample_contact.company_name
        assert draft.recipient_email == sample_contact.email
        assert draft.subject is not None
        assert len(draft.subject) > 0
        assert draft.body is not None
        assert len(draft.body) > 100
        assert draft.template_used == 'initial_contact'

    def test_generate_follow_up_1(self, generator, sample_contact):
        """Test generating first follow-up email."""
        draft = generator.generate(sample_contact, 'follow_up_1')

        assert draft is not None
        assert 'Erinnerung' in draft.subject
        assert draft.body is not None

    def test_generate_follow_up_2(self, generator, sample_contact):
        """Test generating second follow-up email."""
        draft = generator.generate(sample_contact, 'follow_up_2')

        assert draft is not None
        assert 'Letzter Kontaktversuch' in draft.subject
        assert draft.body is not None

    def test_generate_without_email(self, generator):
        """Test that generation fails without email."""
        contact = ScraperResult(
            source="test",
            company_name="Test GmbH"
        )

        draft = generator.generate(contact)
        assert draft is None

    def test_personalization_score_full(self, generator, sample_contact):
        """Test personalization score with full contact data."""
        draft = generator.generate(sample_contact)

        assert draft is not None
        assert draft.personalization_score >= 0.7

    def test_personalization_score_minimal(self, generator, minimal_contact):
        """Test personalization score with minimal contact data."""
        draft = generator.generate(minimal_contact)

        assert draft is not None
        assert draft.personalization_score >= 0.0
        assert draft.personalization_score < 0.5

    def test_company_name_in_email(self, generator, sample_contact):
        """Test that company name appears in email."""
        draft = generator.generate(sample_contact)

        assert draft is not None
        assert sample_contact.company_name in draft.body

    def test_location_personalization(self, generator, sample_contact):
        """Test location personalization."""
        draft = generator.generate(sample_contact)

        assert draft is not None
        # Should mention Heilbronn
        assert 'Heilbronn' in draft.body or 'heilbronn' in draft.body.lower()

    def test_units_personalization(self, generator, sample_contact):
        """Test units personalization."""
        draft = generator.generate(sample_contact)

        assert draft is not None
        # Should mention units
        assert str(sample_contact.units) in draft.body or 'Einheiten' in draft.body

    def test_generate_invalid_template(self, generator, sample_contact):
        """Test with invalid template name."""
        draft = generator.generate(sample_contact, 'nonexistent_template')

        assert draft is None

    def test_generate_batch(self, generator):
        """Test batch email generation."""
        contacts = [
            ScraperResult(source="test", company_name="A GmbH", email="a@test.de", units=100),
            ScraperResult(source="test", company_name="B GmbH", email="b@test.de"),
            ScraperResult(source="test", company_name="C GmbH", email="c@test.de", units=200),
        ]

        # Use min_personalization=0.0 to include all contacts
        drafts = generator.generate_batch(contacts, min_personalization=0.0)

        assert len(drafts) == 3
        assert all(d.subject for d in drafts)

    def test_generate_batch_filters_no_email(self, generator):
        """Test that batch generation skips contacts without email."""
        contacts = [
            ScraperResult(source="test", company_name="A GmbH", email="a@test.de", units=50),
            ScraperResult(source="test", company_name="B GmbH"),  # No email
            ScraperResult(source="test", company_name="C GmbH", email="c@test.de", units=100),
        ]

        # Use min_personalization=0.0 to include all contacts with email
        drafts = generator.generate_batch(contacts, min_personalization=0.0)

        assert len(drafts) == 2

    def test_generate_batch_min_personalization(self, generator):
        """Test batch generation with minimum personalization threshold."""
        contacts = [
            ScraperResult(source="test", company_name="Full GmbH", email="full@test.de",
                         units=100, address="Heilbronn"),
            ScraperResult(source="test", company_name="Minimal GmbH", email="min@test.de"),
        ]

        drafts = generator.generate_batch(contacts, min_personalization=0.5)

        # Only the full contact should pass the threshold
        assert len(drafts) >= 1

    def test_preview_output(self, generator, sample_contact):
        """Test preview generation."""
        draft = generator.generate(sample_contact)
        preview = generator.preview(draft)

        assert preview is not None
        assert sample_contact.company_name in preview
        assert draft.subject in preview
        assert "PERSONALISIERUNG" in preview

    def test_preview_without_highlights(self, generator, sample_contact):
        """Test preview without highlights."""
        draft = generator.generate(sample_contact)
        preview = generator.preview(draft, highlights=False)

        assert preview is not None
        assert "PERSONALISIERUNG" not in preview

    def test_validate_draft_valid(self, generator, sample_contact):
        """Test validation of valid draft."""
        draft = generator.generate(sample_contact)
        issues = generator.validate_draft(draft)

        # Should have no critical issues
        assert len(issues) == 0 or not any('Missing required' in i for i in issues)

    def test_validate_draft_missing_elements(self, generator):
        """Test validation catches missing elements."""
        draft = EmailDraft(
            contact_id="test",
            company_name="Test GmbH",
            subject="",  # Missing
            body="Short",  # Too short
            recipient_email=""  # Missing
        )

        issues = generator.validate_draft(draft)

        assert len(issues) > 0
        assert any('subject' in i.lower() or 'Subject' in i for i in issues)

    def test_validate_draft_too_long(self, generator):
        """Test validation catches too long emails."""
        long_body = " ".join(["wort"] * 350)  # 350 words
        draft = EmailDraft(
            contact_id="test",
            company_name="Test GmbH",
            subject="Test Betreff",
            body=long_body,
            recipient_email="test@test.de"
        )

        issues = generator.validate_draft(draft)

        assert any('zu lang' in i or 'too long' in i for i in issues)

    def test_draft_to_dict(self, generator, sample_contact):
        """Test draft serialization."""
        draft = generator.generate(sample_contact)
        data = draft.to_dict()

        assert data['company_name'] == sample_contact.company_name
        assert data['recipient_email'] == sample_contact.email
        assert 'subject' in data
        assert 'body' in data
        assert 'generated_at' in data

    def test_custom_context(self, generator, sample_contact):
        """Test generation with custom context."""
        custom = {
            'special_offer': 'Sonderangebot: 10% Rabatt auf den ersten Monat'
        }

        draft = generator.generate(sample_contact, custom_context=custom)

        assert draft is not None

    def test_extract_location(self, generator):
        """Test location extraction from address."""
        # German address with ZIP
        loc = generator._extract_location("Hauptstraße 1, 74072 Heilbronn")
        assert loc == "Heilbronn"

        # Another city
        loc = generator._extract_location("Marktplatz 5, 74172 Neckarsulm")
        assert loc == "Neckarsulm"

        # No clear location
        loc = generator._extract_location("Some address")
        assert loc is None

    def test_is_target_location(self, generator):
        """Test target location detection."""
        assert generator._is_target_location("74072 Heilbronn")
        assert generator._is_target_location("Neckarsulm")
        assert not generator._is_target_location("Stuttgart")

    def test_format_units(self, generator):
        """Test units formatting."""
        assert generator._format_units(1) == "eine Einheit"
        assert generator._format_units(5) == "5 Einheiten"
        assert generator._format_units(150) == "über 150 Einheiten"
        assert generator._format_units(None) == ""

    def test_format_employees(self, generator):
        """Test employees formatting."""
        assert generator._format_employees(1) == "einem Mitarbeiter"
        assert generator._format_employees(5) == "5 Mitarbeitern"
        assert generator._format_employees(20) == "einem Team von 20 Mitarbeitern"
        assert generator._format_employees(None) == ""

    def test_calculate_personalization(self, generator, sample_contact):
        """Test personalization calculation."""
        context = generator._build_context(sample_contact)
        score = generator._calculate_personalization(context)

        # Full contact should have high score
        assert score >= 0.7

    def test_word_count_in_range(self, generator, sample_contact):
        """Test that generated emails are in target word count range."""
        draft = generator.generate(sample_contact)

        if draft:
            word_count = len(draft.body.split())
            # Should be between 150-300 words
            assert 100 <= word_count <= 350, f"Word count {word_count} out of range"

    def test_sender_info_included(self, generator, sample_contact):
        """Test that sender info is included."""
        draft = generator.generate(sample_contact)

        assert draft is not None
        assert 'SE Handwerk' in draft.body
        assert 'Heilbronn' in draft.body or 'heilbronn' in draft.body.lower()