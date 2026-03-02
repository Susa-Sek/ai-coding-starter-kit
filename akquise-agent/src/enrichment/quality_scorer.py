"""
Quality scoring for contact data.
"""

from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum

from loguru import logger
from src.scrapers.base import ScraperResult


class LeadQuality(Enum):
    """Lead quality classification."""
    A = "A"  # High priority, ready for contact
    B = "B"  # Medium priority, needs more info
    C = "C"  # Low priority, long-term potential


@dataclass
class QualityAssessment:
    """Assessment of contact quality."""
    score: int  # 0-100
    grade: LeadQuality
    has_email: bool
    has_phone: bool
    has_address: bool
    has_website: bool
    has_units: bool
    has_employees: bool
    location_match: bool
    unit_range_match: bool
    employee_range_match: bool
    business_email: bool
    recommendations: List[str]


class QualityScorer:
    """
    Scores contact data quality and provides recommendations.

    Scoring factors:
    - Contact completeness (email, phone, address)
    - Business information (units, employees)
    - Location match (Heilbronn + 50km)
    - Email type (business vs free)
    - Data source reliability
    """

    # Target parameters
    TARGET_LOCATION = "Heilbronn"
    TARGET_RADIUS_KM = 50
    MIN_UNITS = 50
    MAX_UNITS = 500
    MAX_EMPLOYEES = 100

    # Scoring weights
    WEIGHTS = {
        'email': 20,
        'phone': 15,
        'address': 10,
        'website': 10,
        'units': 15,
        'employees': 5,
        'rating': 5,
        'reviews': 5,
        'location': 10,
        'business_email': 5,
    }

    # Free email providers (lower priority)
    FREE_EMAIL_PROVIDERS = {
        'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
        'live.com', 'aol.com', 'icloud.com', 'mail.com',
        'gmx.de', 'gmx.net', 'web.de', 't-online.de',
        'freenet.de', 'yahoo.de', 'googlemail.com'
    }

    def __init__(
        self,
        target_location: str = "Heilbronn",
        min_units: int = 50,
        max_units: int = 500,
        max_employees: int = 100
    ):
        """
        Initialize quality scorer.

        Args:
            target_location: Target location for matching
            min_units: Minimum units for ideal match
            max_units: Maximum units for ideal match
            max_employees: Maximum employees for ideal match
        """
        self.target_location = target_location.lower()
        self.min_units = min_units
        self.max_units = max_units
        self.max_employees = max_employees

    def is_business_email(self, email: str) -> bool:
        """
        Check if email is a business email (not free provider).

        Args:
            email: Email address

        Returns:
            True if business email
        """
        if not email or '@' not in email:
            return False

        domain = email.split('@')[-1].lower()
        return domain not in self.FREE_EMAIL_PROVIDERS

    def is_location_match(self, address: str) -> bool:
        """
        Check if address is in target location.

        Args:
            address: Address string

        Returns:
            True if in target location
        """
        if not address:
            return False

        address_lower = address.lower()

        # Direct match
        if self.target_location in address_lower:
            return True

        # German state variations
        location_variants = {
            'heilbronn': ['heilbronn', 'hn', 'heil'],
            'heidelberg': ['heidelberg', 'hd'],
            'stuttgart': ['stuttgart', 's'],
        }

        if self.target_location in location_variants:
            for variant in location_variants[self.target_location]:
                if variant in address_lower:
                    return True

        return False

    def calculate_score(self, contact: ScraperResult) -> int:
        """
        Calculate quality score for contact.

        Args:
            contact: Contact to score

        Returns:
            Score (0-100)
        """
        score = 0

        # Contact completeness
        if contact.email:
            score += self.WEIGHTS['email']
        if contact.phone:
            score += self.WEIGHTS['phone']
        if contact.address:
            score += self.WEIGHTS['address']
        if contact.website:
            score += self.WEIGHTS['website']

        # Business information
        if contact.units:
            if self.min_units <= contact.units <= self.max_units:
                score += self.WEIGHTS['units']
            elif contact.units < self.min_units:
                score += int(self.WEIGHTS['units'] * (contact.units / self.min_units))
            else:
                # Over max, partial credit
                score += int(self.WEIGHTS['units'] * (self.max_units / contact.units))

        if contact.employees:
            if contact.employees <= self.max_employees:
                score += self.WEIGHTS['employees']
            else:
                # Penalize large companies
                score += max(0, self.WEIGHTS['employees'] - int((contact.employees - self.max_employees) / 10))

        # Reputation
        if contact.rating:
            score += int(self.WEIGHTS['rating'] * (contact.rating / 5.0))
        if contact.reviews:
            score += min(self.WEIGHTS['reviews'], int(self.WEIGHTS['reviews'] * (contact.reviews / 100)))

        # Location match
        if contact.address and self.is_location_match(contact.address):
            score += self.WEIGHTS['location']

        # Business email bonus
        if contact.email and self.is_business_email(contact.email):
            score += self.WEIGHTS['business_email']

        return min(score, 100)

    def classify(self, score: int) -> LeadQuality:
        """
        Classify lead quality based on score.

        Args:
            score: Quality score (0-100)

        Returns:
            LeadQuality classification
        """
        if score >= 70:
            return LeadQuality.A
        elif score >= 40:
            return LeadQuality.B
        else:
            return LeadQuality.C

    def assess(self, contact: ScraperResult) -> QualityAssessment:
        """
        Assess contact quality with detailed analysis.

        Args:
            contact: Contact to assess

        Returns:
            QualityAssessment with details
        """
        score = self.calculate_score(contact)
        grade = self.classify(score)

        recommendations = []

        # Generate recommendations
        if not contact.email:
            recommendations.append("E-Mail-Adresse fehlt - Recherche empfohlen")
        elif not self.is_business_email(contact.email):
            recommendations.append("Private E-Mail-Adresse - Geschäftliche Adresse bevorzugt")

        if not contact.phone:
            recommendations.append("Telefonnummer fehlt - Direkter Kontakt nicht möglich")

        if not contact.address:
            recommendations.append("Adresse fehlt - Standort nicht überprüfbar")
        elif not self.is_location_match(contact.address):
            recommendations.append(f"Adresse außerhalb von {self.target_location.title()} - Relevanz prüfen")

        if not contact.units:
            recommendations.append("Anzahl Einheiten unbekannt - Größe nicht bewertbar")
        elif contact.units and (contact.units < self.min_units or contact.units > self.max_units):
            recommendations.append(f"Einheiten außerhalb Zielbereich ({self.min_units}-{self.max_units})")

        if contact.employees and contact.employees > self.max_employees:
            recommendations.append(f"Großes Unternehmen ({contact.employees} Mitarbeiter) - Möglicherweise weniger agil")

        if not contact.website:
            recommendations.append("Website fehlt - Online-Recherche eingeschränkt")

        return QualityAssessment(
            score=score,
            grade=grade,
            has_email=bool(contact.email),
            has_phone=bool(contact.phone),
            has_address=bool(contact.address),
            has_website=bool(contact.website),
            has_units=bool(contact.units),
            has_employees=bool(contact.employees),
            location_match=self.is_location_match(contact.address) if contact.address else False,
            unit_range_match=contact.units and self.min_units <= contact.units <= self.max_units if contact.units else False,
            employee_range_match=contact.employees and contact.employees <= self.max_employees if contact.employees else False,
            business_email=self.is_business_email(contact.email) if contact.email else False,
            recommendations=recommendations
        )

    def rank_contacts(
        self,
        contacts: List[ScraperResult]
    ) -> List[Dict[str, Any]]:
        """
        Rank contacts by quality score.

        Args:
            contacts: List of contacts to rank

        Returns:
            List of contacts with scores, sorted by score descending
        """
        ranked = []

        for contact in contacts:
            score = self.calculate_score(contact)
            grade = self.classify(score)

            ranked.append({
                'contact': contact,
                'score': score,
                'grade': grade.value,
                'assessment': self.assess(contact)
            })

        # Sort by score descending
        ranked.sort(key=lambda x: x['score'], reverse=True)

        logger.info(
            f"Ranked {len(contacts)} contacts: "
            f"{sum(1 for r in ranked if r['grade'] == 'A')} A-grade, "
            f"{sum(1 for r in ranked if r['grade'] == 'B')} B-grade, "
            f"{sum(1 for r in ranked if r['grade'] == 'C')} C-grade"
        )

        return ranked

    def get_statistics(self, contacts: List[ScraperResult]) -> Dict[str, Any]:
        """
        Get statistics about contact quality.

        Args:
            contacts: List of contacts

        Returns:
            Dictionary with statistics
        """
        if not contacts:
            return {
                'total': 0,
                'a_grade': 0,
                'b_grade': 0,
                'c_grade': 0,
                'avg_score': 0,
                'with_email': 0,
                'with_phone': 0,
                'with_address': 0,
                'with_website': 0,
                'business_emails': 0,
                'location_matches': 0
            }

        scores = [self.calculate_score(c) for c in contacts]
        grades = [self.classify(s) for s in scores]

        return {
            'total': len(contacts),
            'a_grade': sum(1 for g in grades if g == LeadQuality.A),
            'b_grade': sum(1 for g in grades if g == LeadQuality.B),
            'c_grade': sum(1 for g in grades if g == LeadQuality.C),
            'avg_score': sum(scores) / len(scores),
            'with_email': sum(1 for c in contacts if c.email),
            'with_phone': sum(1 for c in contacts if c.phone),
            'with_address': sum(1 for c in contacts if c.address),
            'with_website': sum(1 for c in contacts if c.website),
            'business_emails': sum(1 for c in contacts if c.email and self.is_business_email(c.email)),
            'location_matches': sum(1 for c in contacts if c.address and self.is_location_match(c.address))
        }