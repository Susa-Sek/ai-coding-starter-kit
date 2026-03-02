"""
Enrichment module for Akquise Agent.

Provides email validation, website parsing, deduplication, and quality scoring.
"""

from .email_validator import EmailValidator, EmailValidationResult, is_business_email
from .website_parser import WebsiteParser, WebsiteInfo
from .deduplication import Deduplicator, DuplicateMatch
from .quality_scorer import QualityScorer, QualityAssessment, LeadQuality

__all__ = [
    # Email validation
    "EmailValidator",
    "EmailValidationResult",
    "is_business_email",

    # Website parsing
    "WebsiteParser",
    "WebsiteInfo",

    # Deduplication
    "Deduplicator",
    "DuplicateMatch",

    # Quality scoring
    "QualityScorer",
    "QualityAssessment",
    "LeadQuality",
]
