"""
Tests for HTML email template generation.
"""
import pytest
from pathlib import Path

from src.generators.email_generator import EmailGenerator, EmailDraft


@pytest.fixture
def generator():
    """Create EmailGenerator instance."""
    templates_dir = Path(__file__).parent.parent / 'src' / 'generators' / 'templates'
    return EmailGenerator(templates_dir=templates_dir)


@pytest.fixture
def sample_contact():
    """Create sample contact for testing."""
    from src.scrapers.base import ScraperResult
    from datetime import datetime

    # Use ScraperResult instead of MagicMock to avoid comparison issues
    contact = ScraperResult(
        source="test",
        company_name="Test Hausverwaltung GmbH",
        address="Hauptstraße 123, 74072 Heilbronn",
        phone="+49 7131 12345",
        email="info@test-hausverwaltung.de",
        website="https://test-hausverwaltung.de",
        units=150,
        employees=12,
        rating=4.5,
        reviews=25,
        scraped_at=datetime.now(),
    )
    # Set additional enrichment attributes
    contact.website_description = "Professionelle Hausverwaltung in Heilbronn"
    contact.decision_maker_name = "Max Mustermann"
    contact.decision_maker_title = "Geschäftsführer"
    contact.decision_maker_email = "m.mustermann@test-hausverwaltung.de"
    contact.founding_year = 2010
    return contact


class TestHTMLTemplates:
    """Test HTML template generation."""

    def test_html_template_exists(self, generator):
        """Verify all HTML templates exist."""
        assert 'initial_contact.html' in generator._templates
        assert 'follow_up_1.html' in generator._templates
        assert 'follow_up_2.html' in generator._templates

    def test_generate_text_format(self, generator, sample_contact):
        """Test text format generation (default)."""
        draft = generator.generate(sample_contact, 'initial_contact')

        assert draft is not None
        assert draft.body is not None
        assert draft.html_body is None  # No HTML by default
        # Company name appears in subject, check for personalization in body
        assert "Test Hausverwaltung GmbH" in draft.subject  # In subject
        assert "Heilbronn" in draft.body  # Location personalization

    def test_generate_html_format(self, generator, sample_contact):
        """Test HTML format generation."""
        draft = generator.generate(sample_contact, 'initial_contact', format='html')

        assert draft is not None
        assert draft.body is not None
        assert draft.html_body is not None
        assert "<!DOCTYPE html>" in draft.html_body
        assert "<body" in draft.html_body
        assert "Test Hausverwaltung" in draft.html_body
        assert "style=" in draft.html_body  # Has inline styles

    def test_html_has_proper_structure(self, generator, sample_contact):
        """Test HTML has required elements."""
        draft = generator.generate(sample_contact, 'initial_contact', format='html')

        # Check basic HTML structure
        assert "<html>" in draft.html_body
        assert "</html>" in draft.html_body
        assert "<head>" in draft.html_body
        assert "<body" in draft.html_body

        # Check inline styles (email client compatibility)
        assert "font-family:" in draft.html_body
        assert "font-size:" in draft.html_body

        # Check German umlauts are encoded
        assert "&uuml;" in draft.html_body or "ü" in draft.html_body

    def test_html_uses_template_variables(self, generator, sample_contact):
        """Test HTML template uses all context variables."""
        draft = generator.generate(sample_contact, 'initial_contact', format='html')

        # Check personalization variables are rendered
        assert "Max Mustermann" in draft.html_body
        # decision_maker_title is rendered as raw text (Jinja2 doesn't autoescape variables)
        assert "Geschäftsführer" in draft.html_body
        assert "Heilbronn" in draft.html_body  # Location personalization

    def test_follow_up_templates_html(self, generator, sample_contact):
        """Test follow-up templates also have HTML versions."""
        # Follow-up 1
        draft1 = generator.generate(sample_contact, 'follow_up_1', format='html')
        assert draft1 is not None
        assert draft1.html_body is not None
        assert "dritte und letzte" not in draft1.html_body  # That's follow_up_2

        # Follow-up 2
        draft2 = generator.generate(sample_contact, 'follow_up_2', format='html')
        assert draft2 is not None
        assert draft2.html_body is not None
        assert "dritte und letzte" in draft2.html_body

    def test_html_body_in_to_dict(self, generator, sample_contact):
        """Test html_body is included in dictionary export."""
        draft = generator.generate(sample_contact, 'initial_contact', format='html')
        data = draft.to_dict()

        assert 'html_body' in data
        assert data['html_body'] is not None
        assert '<html>' in data['html_body']