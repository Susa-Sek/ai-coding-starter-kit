"""
Email validation module for contact enrichment.
"""

import re
import asyncio
import dns.resolver
from typing import Optional, List, Tuple
from dataclasses import dataclass
from loguru import logger


@dataclass
class EmailValidationResult:
    """Result of email validation."""
    email: str
    is_valid: bool
    syntax_valid: bool
    mx_valid: bool
    domain: str
    error: Optional[str] = None


class EmailValidator:
    """
    Validates email addresses without sending emails.

    Features:
    - Syntax validation (regex)
    - Domain MX record check
    - Disposable email detection
    - Common typo correction
    """

    # Common email typos
    COMMON_TYPOS = {
        "gmial": "gmail",
        "gmal": "gmail",
        "gmai": "gmail",
        "gamil": "gmail",
        "hotmai": "hotmail",
        "hotmal": "hotmail",
        "hotmil": "hotmail",
        "yaho": "yahoo",
        "yahho": "yahoo",
        "web.d": "web.de",
        "we.de": "web.de",
    }

    # Disposable email domains
    DISPOSABLE_DOMAINS = {
        "tempmail.com",
        "throwaway.com",
        "10minutemail.com",
        "guerrillamail.com",
        "mailinator.com",
        "dispostable.com",
        "mailnesia.com",
        "tempail.com",
    }

    # Email regex pattern
    EMAIL_PATTERN = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )

    def __init__(self, timeout: int = 10):
        """
        Initialize email validator.

        Args:
            timeout: DNS lookup timeout in seconds
        """
        self.timeout = timeout
        self._cache: dict = {}

    def validate_syntax(self, email: str) -> bool:
        """
        Validate email syntax using regex.

        Args:
            email: Email address to validate

        Returns:
            True if syntax is valid
        """
        if not email:
            return False

        email = email.strip().lower()
        return bool(self.EMAIL_PATTERN.match(email))

    def get_domain(self, email: str) -> Optional[str]:
        """
        Extract domain from email.

        Args:
            email: Email address

        Returns:
            Domain or None
        """
        if not email or '@' not in email:
            return None

        return email.split('@')[-1].lower().strip()

    def correct_typos(self, email: str) -> str:
        """
        Correct common email typos.

        Args:
            email: Email address

        Returns:
            Corrected email
        """
        if not email:
            return email

        email = email.strip().lower()
        domain = self.get_domain(email)

        if domain:
            # Check for exact typo match first
            for typo, correct in self.COMMON_TYPOS.items():
                if domain == typo:
                    local = email.split('@')[0]
                    return f"{local}@{correct}"

            # Check if domain contains a typo as prefix (e.g., "gmial.com" -> "gmail.com")
            # Only apply if it looks like a typo in the domain name part (before TLD)
            if '.' in domain:
                domain_part, tld = domain.rsplit('.', 1)
                for typo, correct in self.COMMON_TYPOS.items():
                    if domain_part == typo:
                        return f"{email.split('@')[0]}@{correct}.{tld}"

        return email

    def is_disposable(self, email: str) -> bool:
        """
        Check if email domain is a disposable email provider.

        Args:
            email: Email address

        Returns:
            True if disposable
        """
        domain = self.get_domain(email)
        return domain in self.DISPOSABLE_DOMAINS if domain else False

    async def check_mx_record(self, domain: str) -> Tuple[bool, Optional[str]]:
        """
        Check if domain has valid MX records.

        Args:
            domain: Domain to check

        Returns:
            Tuple of (has_mx, error_message)
        """
        if not domain:
            return False, "No domain provided"

        # Check cache
        if domain in self._cache:
            return self._cache[domain]

        try:
            # Run DNS lookup in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._query_mx,
                domain
            )
            self._cache[domain] = (result, None)
            return result, None

        except dns.resolver.NoAnswer:
            error = "No MX record found"
            self._cache[domain] = (False, error)
            return False, error

        except dns.resolver.NXDOMAIN:
            error = "Domain does not exist"
            self._cache[domain] = (False, error)
            return False, error

        except dns.resolver.Timeout:
            error = "DNS timeout"
            self._cache[domain] = (False, error)
            return False, error

        except Exception as e:
            error = str(e)
            self._cache[domain] = (False, error)
            return False, error

    def _query_mx(self, domain: str) -> bool:
        """Query MX records synchronously."""
        try:
            answers = dns.resolver.resolve(domain, 'MX', lifetime=self.timeout)
            return len(answers) > 0
        except Exception:
            return False

    async def validate(
        self,
        email: str,
        check_mx: bool = True,
        correct_typos: bool = True
    ) -> EmailValidationResult:
        """
        Validate an email address comprehensively.

        Args:
            email: Email address to validate
            check_mx: Whether to check MX records
            correct_typos: Whether to correct common typos

        Returns:
            EmailValidationResult
        """
        if not email:
            return EmailValidationResult(
                email="",
                is_valid=False,
                syntax_valid=False,
                mx_valid=False,
                domain="",
                error="No email provided"
            )

        # Normalize
        email = email.strip().lower()

        # Correct typos
        if correct_typos:
            email = self.correct_typos(email)

        # Check syntax
        syntax_valid = self.validate_syntax(email)

        if not syntax_valid:
            return EmailValidationResult(
                email=email,
                is_valid=False,
                syntax_valid=False,
                mx_valid=False,
                domain=self.get_domain(email) or "",
                error="Invalid email syntax"
            )

        domain = self.get_domain(email)

        # Check if disposable
        if self.is_disposable(email):
            return EmailValidationResult(
                email=email,
                is_valid=False,
                syntax_valid=True,
                mx_valid=False,
                domain=domain,
                error="Disposable email domain"
            )

        # Check MX records
        mx_valid = True
        mx_error = None

        if check_mx and domain:
            mx_valid, mx_error = await self.check_mx_record(domain)

        return EmailValidationResult(
            email=email,
            is_valid=syntax_valid and mx_valid,
            syntax_valid=syntax_valid,
            mx_valid=mx_valid,
            domain=domain,
            error=mx_error if not mx_valid else None
        )

    async def validate_batch(
        self,
        emails: List[str],
        check_mx: bool = True
    ) -> List[EmailValidationResult]:
        """
        Validate multiple emails.

        Args:
            emails: List of emails to validate
            check_mx: Whether to check MX records

        Returns:
            List of validation results
        """
        tasks = [self.validate(email, check_mx) for email in emails]
        return await asyncio.gather(*tasks)


def extract_domain(email: str) -> Optional[str]:
    """Extract domain from email address."""
    if not email or '@' not in email:
        return None
    return email.split('@')[-1].lower().strip()


def is_business_email(email: str) -> bool:
    """
    Check if email is likely a business email (not free provider).

    Args:
        email: Email address

    Returns:
        True if likely business email
    """
    domain = extract_domain(email)
    if not domain:
        return False

    # Common free email providers
    free_providers = {
        'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
        'live.com', 'aol.com', 'icloud.com', 'mail.com',
        'gmx.de', 'gmx.net', 'web.de', 't-online.de',
        'freenet.de', 'yahoo.de', 'googlemail.com'
    }

    return domain not in free_providers