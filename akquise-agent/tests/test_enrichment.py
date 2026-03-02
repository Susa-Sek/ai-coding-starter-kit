"""
Tests for enrichment module.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.enrichment.email_validator import (
    EmailValidator,
    EmailValidationResult,
    is_business_email,
    extract_domain,
)
from src.enrichment.deduplication import Deduplicator, DuplicateMatch
from src.enrichment.quality_scorer import QualityScorer, LeadQuality
from src.scrapers.base import ScraperResult


class TestEmailValidator:
    """Tests for EmailValidator."""

    def test_syntax_validation(self):
        """Test email syntax validation."""
        validator = EmailValidator()

        # Valid emails
        assert validator.validate_syntax("test@example.com")
        assert validator.validate_syntax("user.name@domain.de")
        assert validator.validate_syntax("info@hausverwaltung-mueller.de")

        # Invalid emails
        assert not validator.validate_syntax("invalid")
        assert not validator.validate_syntax("@example.com")
        assert not validator.validate_syntax("test@")
        assert not validator.validate_syntax("")

    def test_domain_extraction(self):
        """Test domain extraction."""
        assert extract_domain("test@example.com") == "example.com"
        assert extract_domain("info@hausverwaltung.de") == "hausverwaltung.de"
        assert extract_domain("invalid") is None
        assert extract_domain("") is None

    def test_typo_correction(self):
        """Test common typo correction."""
        validator = EmailValidator()

        # Common typos
        assert validator.correct_typos("test@gmial.com") == "test@gmail.com"
        assert validator.correct_typos("test@gmal.de") == "test@gmail.de"
        assert validator.correct_typos("test@hotmail") == "test@hotmail"

        # Already correct
        assert validator.correct_typos("test@gmail.com") == "test@gmail.com"

    def test_disposable_detection(self):
        """Test disposable email detection."""
        validator = EmailValidator()

        assert validator.is_disposable("test@tempmail.com")
        assert validator.is_disposable("test@10minutemail.com")
        assert not validator.is_disposable("test@gmail.com")
        assert not validator.is_disposable("test@company.de")

    def test_business_email_detection(self):
        """Test business email detection."""
        assert is_business_email("info@company.de")
        assert is_business_email("kontakt@hausverwaltung-mueller.de")
        assert not is_business_email("test@gmail.com")
        assert not is_business_email("info@yahoo.de")
        assert not is_business_email("")

    @pytest.mark.asyncio
    async def test_validate_email(self):
        """Test full email validation."""
        validator = EmailValidator()

        result = await validator.validate("test@example.com", check_mx=False)
        assert result.syntax_valid
        assert result.is_valid

    @pytest.mark.asyncio
    async def test_validate_invalid_email(self):
        """Test validation of invalid email."""
        validator = EmailValidator()

        result = await validator.validate("invalid", check_mx=False)
        assert not result.syntax_valid
        assert not result.is_valid


class TestDeduplicator:
    """Tests for Deduplicator."""

    def test_normalize_name(self):
        """Test company name normalization."""
        dedup = Deduplicator()

        assert dedup.normalize_name("Müller GmbH") == "müller"
        assert dedup.normalize_name("Schmidt GmbH & Co. KG") == "schmidt"
        assert dedup.normalize_name("Test AG") == "test"
        assert dedup.normalize_name("Hausverwaltung Müller E.K.") == "hausverwaltung müller"

    def test_normalize_phone(self):
        """Test phone normalization."""
        dedup = Deduplicator()

        assert dedup.normalize_phone("07131 12345") == "+49713112345"
        assert dedup.normalize_phone("+49 7131 12345") == "+49713112345"
        assert dedup.normalize_phone("0049 7131 12345") == "+49713112345"

    def test_similarity_score(self):
        """Test string similarity calculation."""
        dedup = Deduplicator()

        # Identical strings
        assert dedup.similarity_score("test", "test") == 1.0

        # Similar strings
        score = dedup.similarity_score("Hausverwaltung Müller", "Hausverwaltung Mueller")
        assert score > 0.8

        # Different strings
        score = dedup.similarity_score("ABC GmbH", "XYZ AG")
        assert score < 0.5

    def test_is_duplicate_email(self):
        """Test duplicate detection by email."""
        dedup = Deduplicator()

        contact1 = ScraperResult(
            source="test",
            company_name="Test GmbH",
            email="info@test.de"
        )
        contact2 = ScraperResult(
            source="test",
            company_name="Test GmbH",
            email="info@test.de"
        )

        is_dup, match_type, score = dedup.is_duplicate(contact1, contact2)
        assert is_dup
        assert match_type == "email"

    def test_is_duplicate_phone(self):
        """Test duplicate detection by phone."""
        dedup = Deduplicator()

        contact1 = ScraperResult(
            source="test",
            company_name="Test GmbH",
            phone="+49713112345"
        )
        contact2 = ScraperResult(
            source="test",
            company_name="Test GmbH",
            phone="07131 12345"
        )

        is_dup, match_type, score = dedup.is_duplicate(contact1, contact2)
        assert is_dup
        assert match_type == "phone"

    def test_is_duplicate_name(self):
        """Test duplicate detection by name."""
        dedup = Deduplicator()

        contact1 = ScraperResult(
            source="test",
            company_name="Hausverwaltung Müller GmbH"
        )
        contact2 = ScraperResult(
            source="test",
            company_name="Hausverwaltung Müller"
        )

        is_dup, match_type, score = dedup.is_duplicate(contact1, contact2)
        assert is_dup
        assert match_type == "name"

    def test_not_duplicate(self):
        """Test non-duplicate contacts."""
        dedup = Deduplicator()

        contact1 = ScraperResult(
            source="test",
            company_name="Müller GmbH",
            email="info@mueller.de",
            phone="+49713111111"
        )
        contact2 = ScraperResult(
            source="test",
            company_name="Schmidt AG",
            email="info@schmidt.de",
            phone="+49713122222"
        )

        is_dup, match_type, score = dedup.is_duplicate(contact1, contact2)
        assert not is_dup

    def test_find_duplicates(self):
        """Test finding duplicates in a list against existing contacts."""
        dedup = Deduplicator()

        # Existing contacts in database
        existing = [
            ScraperResult(source="test", company_name="Test GmbH", email="info@test.de"),
        ]

        # New contacts to check - one duplicate, one new
        contacts = [
            ScraperResult(source="test", company_name="Test GmbH", email="info@test.de"),  # Duplicate
            ScraperResult(source="test", company_name="Other GmbH", email="info@other.de"),
        ]

        duplicates = dedup.find_duplicates(contacts, existing)
        assert len(duplicates) == 1
        assert duplicates[0].match_type == "email"


class TestQualityScorer:
    """Tests for QualityScorer."""

    def test_business_email_detection(self):
        """Test business email detection."""
        scorer = QualityScorer()

        assert scorer.is_business_email("info@company.de")
        assert not scorer.is_business_email("test@gmail.com")
        assert not scorer.is_business_email("user@yahoo.de")

    def test_location_match(self):
        """Test location matching."""
        scorer = QualityScorer()

        assert scorer.is_location_match("Hauptstraße 1, 74072 Heilbronn")
        assert scorer.is_location_match("Heilbronn")
        assert not scorer.is_location_match("Stuttgart")

    def test_calculate_score(self):
        """Test score calculation."""
        scorer = QualityScorer()

        # Perfect contact
        contact = ScraperResult(
            source="test",
            company_name="Test GmbH",
            email="info@test.de",
            phone="+49713112345",
            address="Hauptstraße 1, 74072 Heilbronn",
            website="https://test.de",
            units=100,
            employees=10
        )

        score = scorer.calculate_score(contact)
        assert score >= 70  # Should be high quality

    def test_classify(self):
        """Test lead classification."""
        scorer = QualityScorer()

        assert scorer.classify(85) == LeadQuality.A
        assert scorer.classify(70) == LeadQuality.A
        assert scorer.classify(55) == LeadQuality.B
        assert scorer.classify(40) == LeadQuality.B
        assert scorer.classify(25) == LeadQuality.C

    def test_assess_contact(self):
        """Test contact assessment."""
        scorer = QualityScorer()

        contact = ScraperResult(
            source="test",
            company_name="Test GmbH",
            email="info@test.de",
            phone="+49713112345"
        )

        assessment = scorer.assess(contact)

        assert assessment.score >= 0
        assert assessment.grade in [LeadQuality.A, LeadQuality.B, LeadQuality.C]
        assert assessment.has_email
        assert assessment.has_phone

    def test_rank_contacts(self):
        """Test contact ranking."""
        scorer = QualityScorer()

        contacts = [
            ScraperResult(source="test", company_name="A GmbH", email="info@a.de", phone="+49111"),
            ScraperResult(source="test", company_name="B GmbH", email="info@b.de"),  # Lower score
            ScraperResult(source="test", company_name="C GmbH", email="info@c.de",
                         phone="+49333", address="Heilbronn", units=100),  # Higher score
        ]

        ranked = scorer.rank_contacts(contacts)

        # Should be sorted by score descending
        assert ranked[0]['score'] >= ranked[1]['score']
        assert ranked[1]['score'] >= ranked[2]['score']

    def test_get_statistics(self):
        """Test statistics calculation."""
        scorer = QualityScorer()

        contacts = [
            ScraperResult(source="test", company_name="A", email="info@a.de",
                         phone="+49111", address="Heilbronn"),
            ScraperResult(source="test", company_name="B", email="test@gmail.com"),
            ScraperResult(source="test", company_name="C"),
        ]

        stats = scorer.get_statistics(contacts)

        assert stats['total'] == 3
        assert stats['with_email'] == 2
        assert stats['with_phone'] == 1
        assert stats['location_matches'] == 1