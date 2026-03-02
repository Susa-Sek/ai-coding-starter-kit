"""
Website parser for extracting additional company information.
"""

import asyncio
import re
from typing import Optional, Dict, Any
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

from loguru import logger
from src.scrapers.browser import BrowserManager
from src.scrapers.utils import (
    extract_email,
    extract_phone,
    extract_units_count,
    extract_employees,
    clean_text,
)


@dataclass
class WebsiteInfo:
    """Extracted information from a website."""
    url: str
    impressum_address: Optional[str] = None
    impressum_phone: Optional[str] = None
    impressum_email: Optional[str] = None
    employee_count: Optional[int] = None
    units_managed: Optional[int] = None
    founding_year: Optional[int] = None
    description: Optional[str] = None
    social_links: Dict[str, str] = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.social_links is None:
            self.social_links = {}


class WebsiteParser:
    """
    Parses company websites to extract additional information.

    Extracts:
    - Impressum contact info (required in Germany)
    - Employee count from About/Team pages
    - Units managed from portfolio pages
    - Social media links
    - Company description
    """

    # Patterns for Impressum detection
    IMPRESSUM_PATTERNS = [
        r'impressum',
        r'imprint',
        r'legal',
        r'rechtliches',
        r'kontakt',
        r'contact',
    ]

    # Patterns for About/Team pages
    ABOUT_PATTERNS = [
        r'über\s*uns',
        r'about',
        r'team',
        r'unternehmen',
        r'company',
        r'wir',
    ]

    # Patterns for portfolio/properties
    PORTFOLIO_PATTERNS = [
        r'portfolio',
        r'immobilien',
        r'objekte',
        r'liegenschaften',
        r'properties',
        r'referenzen',
        r'projekte',
    ]

    def __init__(self, headless: bool = True, timeout: int = 30000):
        """Initialize website parser."""
        self.headless = headless
        self.timeout = timeout
        self._browser_manager: Optional[BrowserManager] = None

    async def initialize(self) -> None:
        """Initialize browser manager."""
        self._browser_manager = BrowserManager(
            headless=self.headless,
            timeout=self.timeout
        )
        await self._browser_manager.initialize()
        logger.info("Website parser initialized")

    async def cleanup(self) -> None:
        """Cleanup browser manager."""
        if self._browser_manager:
            await self._browser_manager.close()
        logger.info("Website parser cleaned up")

    async def parse(self, url: str) -> WebsiteInfo:
        """
        Parse a website for additional information.

        Args:
            url: Website URL to parse

        Returns:
            WebsiteInfo with extracted data
        """
        if not self._browser_manager:
            await self.initialize()

        page = await self._browser_manager.new_page()

        try:
            # Normalize URL
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url

            logger.info(f"Parsing website: {url}")
            await self._browser_manager.goto(url, wait_until="domcontentloaded")

            # Get page content
            content = await page.content()

            # Parse with BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')

            info = WebsiteInfo(url=url)

            # Extract all information
            info.impressum_email = await self._find_impressum_email(page, soup, url)
            info.impressum_phone = await self._find_impressum_phone(page, soup, url)
            info.impressum_address = await self._find_impressum_address(page, soup, url)
            info.employee_count = await self._find_employee_count(page, soup, url)
            info.units_managed = await self._find_units_count(page, soup, url)
            info.description = self._extract_description(soup)
            info.social_links = self._extract_social_links(soup, url)
            info.founding_year = self._extract_founding_year(soup)

            return info

        except Exception as e:
            logger.error(f"Error parsing website {url}: {e}")
            return WebsiteInfo(url=url, error=str(e))

        finally:
            await page.close()

    async def _find_impressum_email(
        self,
        page,
        soup: BeautifulSoup,
        base_url: str
    ) -> Optional[str]:
        """Find email in Impressum section."""
        # First try to find Impressum link
        impressum_url = self._find_link(soup, self.IMPRESSUM_PATTERNS)

        if impressum_url:
            try:
                full_url = urljoin(base_url, impressum_url)
                await page.goto(full_url, wait_until="domcontentloaded")
                impressum_content = await page.content()
                impressum_soup = BeautifulSoup(impressum_content, 'html.parser')

                # Extract all emails from Impressum
                emails = self._extract_all_emails(impressum_soup)
                if emails:
                    # Prefer business emails
                    for email in emails:
                        if not any(x in email for x in ['gmail', 'yahoo', 'hotmail']):
                            return email
                    return emails[0]

                # Go back to main page
                await page.go_back()

            except Exception as e:
                logger.debug(f"Error parsing Impressum: {e}")

        # Check main page for Impressum section
        page_text = soup.get_text()
        emails = self._extract_all_emails(soup)
        if emails:
            return emails[0]

        return None

    async def _find_impressum_phone(
        self,
        page,
        soup: BeautifulSoup,
        base_url: str
    ) -> Optional[str]:
        """Find phone in Impressum section."""
        impressum_url = self._find_link(soup, self.IMPRESSUM_PATTERNS)

        if impressum_url:
            try:
                full_url = urljoin(base_url, impressum_url)
                await page.goto(full_url, wait_until="domcontentloaded")
                content = await page.content()
                impressum_soup = BeautifulSoup(content, 'html.parser')

                phones = self._extract_all_phones(impressum_soup)
                if phones:
                    return phones[0]

                await page.go_back()

            except Exception:
                pass

        # Check main page
        phones = self._extract_all_phones(soup)
        return phones[0] if phones else None

    async def _find_impressum_address(
        self,
        page,
        soup: BeautifulSoup,
        base_url: str
    ) -> Optional[str]:
        """Find address in Impressum section."""
        impressum_url = self._find_link(soup, self.IMPRESSUM_PATTERNS)

        if impressum_url:
            try:
                full_url = urljoin(base_url, impressum_url)
                await page.goto(full_url, wait_until="domcontentloaded")
                content = await page.content()
                impressum_soup = BeautifulSoup(content, 'html.parser')

                # Look for address patterns
                address = self._extract_address(impressum_soup)
                if address:
                    return address

                await page.go_back()

            except Exception:
                pass

        return self._extract_address(soup)

    async def _find_employee_count(
        self,
        page,
        soup: BeautifulSoup,
        base_url: str
    ) -> Optional[int]:
        """Find employee count from About/Team page."""
        about_url = self._find_link(soup, self.ABOUT_PATTERNS)

        if about_url:
            try:
                full_url = urljoin(base_url, about_url)
                await page.goto(full_url, wait_until="domcontentloaded")
                content = await page.content()
                about_soup = BeautifulSoup(content, 'html.parser')

                # Look for employee count
                text = about_soup.get_text()
                count = extract_employees(text)
                if count:
                    return count

                await page.go_back()

            except Exception:
                pass

        # Check main page
        text = soup.get_text()
        return extract_employees(text)

    async def _find_units_count(
        self,
        page,
        soup: BeautifulSoup,
        base_url: str
    ) -> Optional[int]:
        """Find units managed from Portfolio page."""
        portfolio_url = self._find_link(soup, self.PORTFOLIO_PATTERNS)

        if portfolio_url:
            try:
                full_url = urljoin(base_url, portfolio_url)
                await page.goto(full_url, wait_until="domcontentloaded")
                content = await page.content()
                portfolio_soup = BeautifulSoup(content, 'html.parser')

                # Count property entries or look for total count
                text = portfolio_soup.get_text()
                count = extract_units_count(text)
                if count:
                    return count

                # Try to count property cards
                property_cards = portfolio_soup.find_all(
                    ['div', 'article', 'li'],
                    class_=re.compile(r'property|objekt|immobilie', re.I)
                )
                if property_cards and len(property_cards) > 10:
                    return len(property_cards)

                await page.go_back()

            except Exception:
                pass

        # Check main page
        text = soup.get_text()
        return extract_units_count(text)

    def _find_link(self, soup: BeautifulSoup, patterns: list) -> Optional[str]:
        """Find a link matching patterns."""
        for pattern in patterns:
            # Check by href
            for link in soup.find_all('a', href=True):
                href = link['href'].lower()
                if re.search(pattern, href, re.I):
                    return link['href']

            # Check by text
            for link in soup.find_all('a'):
                text = link.get_text().lower()
                if re.search(pattern, text, re.I):
                    return link.get('href')

        return None

    def _extract_all_emails(self, soup: BeautifulSoup) -> list:
        """Extract all emails from page."""
        emails = []

        # From mailto links
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.startswith('mailto:'):
                email = href.replace('mailto:', '').split('?')[0].strip()
                emails.append(email.lower())

        # From text
        text = soup.get_text()
        text_emails = extract_email(text)
        if text_emails:
            emails.append(text_emails)

        # Remove duplicates and invalid
        seen = set()
        valid_emails = []
        for email in emails:
            email = email.strip().lower()
            if email and '@' in email and email not in seen:
                seen.add(email)
                valid_emails.append(email)

        return valid_emails

    def _extract_all_phones(self, soup: BeautifulSoup) -> list:
        """Extract all phone numbers from page."""
        phones = []

        # From tel: links
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.startswith('tel:'):
                phone = href.replace('tel:', '').strip()
                phones.append(extract_phone(phone) or phone)

        # From text
        text = soup.get_text()
        text_phones = extract_phone(text)
        if text_phones:
            phones.append(text_phones)

        return phones

    def _extract_address(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract address from page."""
        # Look for address tag
        address_tag = soup.find('address')
        if address_tag:
            return clean_text(address_tag.get_text())

        # Look for common address patterns
        text = soup.get_text()

        # German ZIP pattern
        match = re.search(
            r'(\d{5})\s+([A-Za-zäöüÄÖÜß\s]+),?\s*(\d{5})?\s*([A-Za-zäöüÄÖÜß\s]+)?',
            text
        )
        if match:
            return clean_text(match.group(0))

        return None

    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract company description."""
        # Meta description
        meta = soup.find('meta', attrs={'name': 'description'})
        if meta and meta.get('content'):
            return clean_text(meta['content'])[:500]

        # First paragraph
        first_p = soup.find('p')
        if first_p:
            text = clean_text(first_p.get_text())
            if text and len(text) > 50:
                return text[:500]

        return None

    def _extract_social_links(self, soup: BeautifulSoup, base_url: str) -> Dict[str, str]:
        """Extract social media links."""
        social_links = {}

        social_patterns = {
            'linkedin': r'linkedin\.com',
            'facebook': r'facebook\.com',
            'instagram': r'instagram\.com',
            'twitter': r'twitter\.com|x\.com',
            'xing': r'xing\.com',
        }

        for link in soup.find_all('a', href=True):
            href = link['href']

            for social, pattern in social_patterns.items():
                if re.search(pattern, href, re.I):
                    social_links[social] = href
                    break

        return social_links

    def _extract_founding_year(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract founding year from page."""
        text = soup.get_text()

        # Patterns for founding year
        patterns = [
            r'gegründet\s*(\d{4})',
            r'gegr.\s*(\d{4})',
            r'seit\s*(\d{4})',
            r'founded\s*(\d{4})',
            r'since\s*(\d{4})',
            r'(\d{4})\s*gegründet',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match:
                try:
                    year = int(match.group(1))
                    if 1900 <= year <= 2100:
                        return year
                except ValueError:
                    continue

        return None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()