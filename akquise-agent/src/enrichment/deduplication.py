"""
Deduplication module for contact data.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from difflib import SequenceMatcher
import re

from loguru import logger
from src.scrapers.base import ScraperResult
from src.scrapers.utils import clean_text, extract_phone


@dataclass
class DuplicateMatch:
    """Information about a duplicate match."""
    original_id: str
    duplicate_id: str
    match_type: str  # 'name', 'phone', 'email', 'address'
    match_score: float
    original_data: Dict[str, Any]
    duplicate_data: Dict[str, Any]


class Deduplicator:
    """
    Identifies and merges duplicate contacts.

    Match strategies:
    - Exact match on company name
    - Exact match on phone number (normalized)
    - Exact match on email domain
    - Fuzzy match on company name
    - Address similarity
    """

    # Minimum similarity for fuzzy matching
    FUZZY_THRESHOLD = 0.85

    # Common name variations
    NAME_VARIATIONS = {
        'gmbh': '',
        'gmbh & co. kg': '',
        '& co. kg': '',
        'kg': '',
        'ag': '',
        'e.k.': '',
        'e.k': '',
        ' ohg': '',
        ' ug': '',
        ' limited': '',
        ' ltd': '',
    }

    def __init__(self, fuzzy_threshold: float = 0.85):
        """
        Initialize deduplicator.

        Args:
            fuzzy_threshold: Minimum similarity for fuzzy matching (0-1)
        """
        self.fuzzy_threshold = fuzzy_threshold
        self._seen_contacts: Dict[str, ScraperResult] = {}

    def normalize_name(self, name: str) -> str:
        """
        Normalize company name for comparison.

        Removes common suffixes and normalizes whitespace.

        Args:
            name: Company name

        Returns:
            Normalized name
        """
        if not name:
            return ""

        name = clean_text(name.lower())

        # Remove common suffixes
        for suffix, replacement in self.NAME_VARIATIONS.items():
            name = name.replace(suffix, replacement)

        # Remove special characters
        name = re.sub(r'[^\w\s]', ' ', name)

        # Normalize whitespace
        name = ' '.join(name.split())

        return name.strip()

    def normalize_phone(self, phone: Optional[str]) -> Optional[str]:
        """
        Normalize phone number for comparison.

        Args:
            phone: Phone number

        Returns:
            Normalized phone (digits only with country code)
        """
        if not phone:
            return None

        # Remove all non-digits except +
        phone = re.sub(r'[^\d+]', '', phone)

        # Normalize German numbers
        if phone.startswith('0049'):
            phone = '+49' + phone[4:]
        elif phone.startswith('0'):
            phone = '+49' + phone[1:]

        return phone

    def normalize_email_domain(self, email: Optional[str]) -> Optional[str]:
        """
        Extract domain from email for comparison.

        Args:
            email: Email address

        Returns:
            Domain or None
        """
        if not email or '@' not in email:
            return None

        return email.split('@')[-1].lower().strip()

    def similarity_score(self, str1: str, str2: str) -> float:
        """
        Calculate similarity between two strings.

        Args:
            str1: First string
            str2: Second string

        Returns:
            Similarity score (0-1)
        """
        if not str1 or not str2:
            return 0.0

        return SequenceMatcher(None, str1, str2).ratio()

    def is_duplicate(
        self,
        contact: ScraperResult,
        existing: ScraperResult
    ) -> Tuple[bool, str, float]:
        """
        Check if contact is a duplicate of existing.

        Args:
            contact: New contact to check
            existing: Existing contact to compare against

        Returns:
            Tuple of (is_duplicate, match_type, score)
        """
        # 1. Exact email match (strongest)
        if contact.email and existing.email:
            if contact.email.lower() == existing.email.lower():
                return True, 'email', 1.0

        # 2. Exact phone match (strong)
        contact_phone = self.normalize_phone(contact.phone)
        existing_phone = self.normalize_phone(existing.phone)

        if contact_phone and existing_phone:
            if contact_phone == existing_phone:
                return True, 'phone', 1.0

        # 3. Exact company name match (strong)
        contact_name = self.normalize_name(contact.company_name)
        existing_name = self.normalize_name(existing.company_name)

        if contact_name and existing_name:
            if contact_name == existing_name:
                return True, 'name', 1.0

        # 4. Email domain match (moderate)
        contact_domain = self.normalize_email_domain(contact.email)
        existing_domain = self.normalize_email_domain(existing.email)

        if contact_domain and existing_domain:
            # Exclude common email providers
            common_providers = {'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
                              'web.de', 'gmx.de', 'gmx.net', 't-online.de'}
            if contact_domain not in common_providers:
                if contact_domain == existing_domain:
                    return True, 'domain', 0.9

        # 5. Fuzzy name match
        if contact_name and existing_name:
            score = self.similarity_score(contact_name, existing_name)
            if score >= self.fuzzy_threshold:
                return True, 'fuzzy_name', score

        # 6. Address similarity (moderate)
        if contact.address and existing.address:
            # Normalize addresses
            contact_addr = clean_text(contact.address.lower())
            existing_addr = clean_text(existing.address.lower())

            # Check for same ZIP code (German: 5 digits)
            contact_zip = re.search(r'\d{5}', contact_addr)
            existing_zip = re.search(r'\d{5}', existing_addr)

            if contact_zip and existing_zip:
                if contact_zip.group() == existing_zip.group():
                    # Same ZIP code - check street similarity
                    score = self.similarity_score(contact_addr, existing_addr)
                    if score >= 0.7:
                        return True, 'address', score

        return False, '', 0.0

    def find_duplicates(
        self,
        contacts: List[ScraperResult],
        existing: Optional[List[ScraperResult]] = None
    ) -> List[DuplicateMatch]:
        """
        Find duplicates among contacts.

        Args:
            contacts: List of contacts to check
            existing: Optional list of existing contacts to check against

        Returns:
            List of duplicate matches
        """
        duplicates = []
        existing_contacts = existing or []

        # Build lookup maps for existing contacts
        existing_by_phone: Dict[str, ScraperResult] = {}
        existing_by_email: Dict[str, ScraperResult] = {}
        existing_by_name: Dict[str, ScraperResult] = {}

        for contact in existing_contacts:
            if contact.phone:
                phone = self.normalize_phone(contact.phone)
                if phone:
                    existing_by_phone[phone] = contact

            if contact.email:
                existing_by_email[contact.email.lower()] = contact

            name = self.normalize_name(contact.company_name)
            if name:
                existing_by_name[name] = contact

        # Check each contact
        for i, contact in enumerate(contacts):
            contact_id = f"new_{i}"

            # Check by phone
            if contact.phone:
                phone = self.normalize_phone(contact.phone)
                if phone and phone in existing_by_phone:
                    duplicates.append(DuplicateMatch(
                        original_id=str(id(existing_by_phone[phone])),
                        duplicate_id=contact_id,
                        match_type='phone',
                        match_score=1.0,
                        original_data=existing_by_phone[phone].to_dict(),
                        duplicate_data=contact.to_dict()
                    ))
                    continue

            # Check by email
            if contact.email:
                email = contact.email.lower()
                if email in existing_by_email:
                    duplicates.append(DuplicateMatch(
                        original_id=str(id(existing_by_email[email])),
                        duplicate_id=contact_id,
                        match_type='email',
                        match_score=1.0,
                        original_data=existing_by_email[email].to_dict(),
                        duplicate_data=contact.to_dict()
                    ))
                    continue

            # Check by name
            name = self.normalize_name(contact.company_name)
            if name:
                # Exact match
                if name in existing_by_name:
                    duplicates.append(DuplicateMatch(
                        original_id=str(id(existing_by_name[name])),
                        duplicate_id=contact_id,
                        match_type='name',
                        match_score=1.0,
                        original_data=existing_by_name[name].to_dict(),
                        duplicate_data=contact.to_dict()
                    ))
                    continue

                # Fuzzy match
                for existing_name_key, existing_contact in existing_by_name.items():
                    score = self.similarity_score(name, existing_name_key)
                    if score >= self.fuzzy_threshold:
                        duplicates.append(DuplicateMatch(
                            original_id=str(id(existing_contact)),
                            duplicate_id=contact_id,
                            match_type='fuzzy_name',
                            match_score=score,
                            original_data=existing_contact.to_dict(),
                            duplicate_data=contact.to_dict()
                        ))
                        break

        logger.info(f"Found {len(duplicates)} duplicates among {len(contacts)} contacts")
        return duplicates

    def merge_contacts(
        self,
        primary: ScraperResult,
        secondary: ScraperResult
    ) -> ScraperResult:
        """
        Merge two contacts, keeping the best data from each.

        Args:
            primary: Primary contact (higher quality)
            secondary: Secondary contact to merge

        Returns:
            Merged contact
        """
        merged = ScraperResult(
            source=primary.source,
            company_name=primary.company_name,
        )

        # Take non-None values, preferring primary
        merged.address = primary.address or secondary.address
        merged.phone = primary.phone or secondary.phone
        merged.email = primary.email or secondary.email
        merged.website = primary.website or secondary.website
        merged.units = primary.units or secondary.units
        merged.employees = primary.employees or secondary.employees
        merged.rating = primary.rating or secondary.rating
        merged.reviews = primary.reviews or secondary.reviews

        # Merge additional data
        merged.additional_data = {**(primary.additional_data or {})}
        if secondary.additional_data:
            merged.additional_data.update(secondary.additional_data)

        # Add sources
        merged.additional_data['sources'] = list(set([
            primary.source,
            secondary.source
        ]))

        # Recalculate quality score
        merged.calculate_quality_score()

        return merged

    def deduplicate(
        self,
        contacts: List[ScraperResult],
        existing: Optional[List[ScraperResult]] = None
    ) -> Tuple[List[ScraperResult], List[DuplicateMatch]]:
        """
        Remove duplicates from contact list.

        Args:
            contacts: List of contacts to deduplicate
            existing: Optional list of existing contacts to check against

        Returns:
            Tuple of (deduplicated_contacts, duplicates_found)
        """
        duplicates = self.find_duplicates(contacts, existing)
        duplicate_ids = {d.duplicate_id for d in duplicates}

        # Filter out duplicates
        deduplicated = [
            contact for i, contact in enumerate(contacts)
            if f"new_{i}" not in duplicate_ids
        ]

        logger.info(
            f"Deduplicated {len(contacts)} contacts -> {len(deduplicated)} "
            f"({len(duplicates)} duplicates removed)"
        )

        return deduplicated, duplicates