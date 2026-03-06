"""
Email generator for personalized contact emails.
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

from jinja2 import Environment, FileSystemLoader, Template
from loguru import logger

from src.scrapers.base import ScraperResult
from src.enrichment.quality_scorer import LeadQuality


@dataclass
class EmailDraft:
    """Generated email draft."""
    contact_id: str
    company_name: str
    subject: str
    body: str
    recipient_email: str
    recipient_name: Optional[str] = None
    template_used: str = ""
    personalization_score: float = 0.0
    generated_at: datetime = None
    metadata: Dict[str, Any] = None
    html_body: Optional[str] = None  # HTML version of body

    def __post_init__(self):
        if self.generated_at is None:
            self.generated_at = datetime.now()
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'contact_id': self.contact_id,
            'company_name': self.company_name,
            'subject': self.subject,
            'body': self.body,
            'recipient_email': self.recipient_email,
            'recipient_name': self.recipient_name,
            'template_used': self.template_used,
            'personalization_score': self.personalization_score,
            'generated_at': self.generated_at.isoformat() if self.generated_at else None,
            'metadata': self.metadata,
            'html_body': self.html_body
        }


class EmailGenerator:
    """
    Generates personalized email drafts from contact data.

    Follows Master Prompt principles:
    - Professional but personal tone
    - Specific and concrete (no marketing fluff)
    - Clear call-to-action
    - Appropriate length (150-250 words)
    """

    # SE Handwerk company info
    COMPANY_INFO = {
        'name': 'SE Handwerk GbR',
        'services': [
            'Hausverwaltung',
            'Immobilienbewirtschaftung',
            'Technisches Gebäudemanagement',
            'Instandhaltung und Reparaturen'
        ],
        'region': 'Heilbronn und Umgebung',
        'contact': {
            'email': 'kontakt@se-handwerk.de',
            'phone': '+49 7131 XXXXXXX'
        }
    }

    # Target parameters for personalization
    TARGET_PARAMS = {
        'location': 'Heilbronn',
        'radius_km': 50,
        'min_units': 50,
        'max_units': 500,
        'max_employees': 100
    }

    def __init__(
        self,
        templates_dir: Optional[Path] = None,
        company_info: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize email generator.

        Args:
            templates_dir: Directory containing Jinja2 templates
            company_info: Override default company info
        """
        if templates_dir is None:
            templates_dir = Path(__file__).parent / 'templates'

        self.templates_dir = Path(templates_dir)
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=False
        )

        self.company_info = company_info or self.COMPANY_INFO

        # Load available templates
        self._templates = self._load_templates()

        logger.info(
            f"EmailGenerator initialized with {len(self._templates)} templates"
        )

    def _load_templates(self) -> Dict[str, Template]:
        """Load all available templates."""
        templates = {}

        if not self.templates_dir.exists():
            logger.warning(f"Templates directory not found: {self.templates_dir}")
            return templates

        for template_file in self.templates_dir.glob('*.j2'):
            template_name = template_file.stem
            try:
                # Read the file and split into subject and body
                content = template_file.read_text(encoding='utf-8')
                templates[template_name] = content
                logger.debug(f"Loaded template: {template_name}")
            except Exception as e:
                logger.error(f"Error loading template {template_name}: {e}")

        return templates

    def get_template_names(self) -> List[str]:
        """Get list of available template names."""
        return list(self._templates.keys())

    def generate(
        self,
        contact,
        template_name: str = 'initial_contact',
        custom_context: Optional[Dict[str, Any]] = None,
        format: str = 'text'
    ) -> Optional[EmailDraft]:
        """
        Generate personalized email draft for a contact.

        Args:
            contact: Contact data (ScraperResult or Contact object)
            template_name: Name of template to use
            custom_context: Additional context for template
            format: Output format - 'text' or 'html' (default: 'text')

        Returns:
            EmailDraft or None if generation fails
        """
        if template_name not in self._templates:
            logger.error(f"Template not found: {template_name}")
            return None

        # Get email from either ScraperResult or Contact object
        email = getattr(contact, 'email', None)
        if not email:
            logger.warning(f"Contact has no email: {getattr(contact, 'company_name', 'Unknown')}")
            return None

        # Build template context
        context = self._build_context(contact, custom_context)

        try:
            template_content = self._templates[template_name]

            # Split into subject and body using --- delimiter
            parts = template_content.split('---', 1)
            if len(parts) == 2:
                subject_template = parts[0].strip()
                body_template = parts[1].strip()
            else:
                # No delimiter - treat first line as subject
                lines = template_content.strip().split('\n', 1)
                subject_template = lines[0]
                body_template = lines[1] if len(lines) > 1 else ""

            # Render subject and body using Jinja2
            subject = Template(subject_template).render(**context)
            body = Template(body_template).render(**context)

            # Render HTML version if available and requested
            html_body = None
            html_template_key = f"{template_name}.html"
            has_html_template = html_template_key in self._templates

            if format == 'html' and has_html_template:
                html_template_content = self._templates[html_template_key]
                # HTML templates are full documents, render directly
                html_body = Template(html_template_content).render(**context)
                logger.debug(f"Rendered HTML template for {template_name}")

            # Calculate personalization score
            personalization_score = self._calculate_personalization(context)

            draft = EmailDraft(
                contact_id=str(id(contact)),
                company_name=contact.company_name,
                subject=subject.strip(),
                body=body.strip(),
                recipient_email=email,
                recipient_name=None,  # Could be extracted from contact
                template_used=template_name,
                personalization_score=personalization_score,
                html_body=html_body.strip() if html_body else None,
                metadata={
                    'units': getattr(contact, 'units', None),
                    'employees': getattr(contact, 'employees', None),
                    'address': getattr(contact, 'address', None),
                    'source': getattr(contact, 'source', None),
                    'format': format
                }
            )

            logger.info(
                f"Generated email draft for {contact.company_name} "
                f"(personalization: {personalization_score:.2f})"
            )

            return draft

        except Exception as e:
            logger.error(f"Error generating email for {contact.company_name}: {e}")
            return None

    def _build_context(
        self,
        contact: ScraperResult,
        custom_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build Jinja2 template context from contact data.

        Args:
            contact: Contact data
            custom_context: Additional context

        Returns:
            Dictionary with template variables
        """
        # Calculate years in business if founding year is available
        years_in_business = None
        founding_year = getattr(contact, 'founding_year', None)
        if founding_year:
            years_in_business = datetime.now().year - founding_year

        # Check if email is a business email
        is_business_email = False
        if contact.email:
            is_business_email = self._is_business_email(contact.email)

        # Get completeness score
        completeness_score = getattr(contact, 'completeness_score', 0)
        if hasattr(contact, 'calculate_completeness_score'):
            completeness_score = contact.calculate_completeness_score()

        # Get website description
        website_description = getattr(contact, 'website_description', None)

        # Get decision maker info (NEW)
        decision_maker_name = getattr(contact, 'decision_maker_name', None)
        decision_maker_title = getattr(contact, 'decision_maker_title', None)
        decision_maker_email = getattr(contact, 'decision_maker_email', None)
        decision_maker_phone = getattr(contact, 'decision_maker_phone', None)
        has_decision_maker = bool(decision_maker_name)

        # Determine company size category
        units = getattr(contact, 'units', None)
        company_size_category = 'klein'  # small
        if units:
            if units > 100:
                company_size_category = 'groß'  # large
            elif units > 50:
                company_size_category = 'mittel'  # medium

        context = {
            # Company info
            'company_name': contact.company_name,
            'company': {
                'name': contact.company_name,
                'address': getattr(contact, 'address', None),
                'phone': getattr(contact, 'phone', None),
                'email': getattr(contact, 'email', None),
                'website': getattr(contact, 'website', None),
                'units': units,
                'employees': getattr(contact, 'employees', None),
                'rating': getattr(contact, 'rating', None),
                'reviews': getattr(contact, 'reviews', None),
                'description': website_description,
                'founding_year': founding_year,
            },

            # SE Handwerk info
            'sender': self.company_info,
            'services': self.company_info['services'],
            'region': self.company_info['region'],

            # Location and targeting
            'location': self._extract_location(getattr(contact, 'address', None)),
            'is_target_location': self._is_target_location(getattr(contact, 'address', None)),
            'is_target_size': self._is_target_size(contact),

            # Formatting helpers
            'units': units,
            'employees': getattr(contact, 'employees', None),
            'units_text': self._format_units(units),
            'employees_text': self._format_employees(getattr(contact, 'employees', None)),
            'location_text': self._format_location(getattr(contact, 'address', None)),
            'greeting': self._get_greeting(contact),

            # Personalization variables
            'company_description': website_description,
            'founding_year': founding_year,
            'years_in_business': years_in_business,
            'is_business_email': is_business_email,
            'completeness_score': completeness_score,

            # Decision maker context (NEW)
            'decision_maker_name': decision_maker_name,
            'decision_maker_title': decision_maker_title,
            'decision_maker_email': decision_maker_email,
            'decision_maker_phone': decision_maker_phone,
            'has_decision_maker': has_decision_maker,
            'company_size_category': company_size_category,

            # Metadata
            'generated_date': datetime.now().strftime('%d.%m.%Y'),
            'source': contact.source
        }

        # Merge custom context
        if custom_context:
            context.update(custom_context)

        return context

    def _is_business_email(self, email: str) -> bool:
        """Check if email is a business email (not free provider)."""
        if not email or '@' not in email:
            return False

        free_providers = {
            'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
            'live.com', 'aol.com', 'icloud.com', 'mail.com',
            'gmx.de', 'gmx.net', 'web.de', 't-online.de',
            'freenet.de', 'yahoo.de', 'googlemail.com'
        }

        domain = email.split('@')[-1].lower()
        return domain not in free_providers

    def _extract_location(self, address: Optional[str]) -> Optional[str]:
        """Extract city from address."""
        if not address:
            return None

        # German city pattern
        import re
        # Pattern for German addresses: "Street 123, 12345 City"
        match = re.search(r'\d{5}\s+([A-Za-zäöüÄÖÜß]+)', address)
        if match:
            return match.group(1)

        # Pattern for just city name
        match = re.search(r'in\s+([A-Za-zäöüÄÖÜß]+)', address)
        if match:
            return match.group(1)

        return None

    def _is_target_location(self, address: Optional[str]) -> bool:
        """Check if address is in target location."""
        if not address:
            return False

        target_cities = [
            'heilbronn', 'heil', 'hn',
            'neckarsulm', 'lauffen', 'böckingen',
            'sontheim', 'klingenberg', 'biberach'
        ]

        address_lower = address.lower()
        return any(city in address_lower for city in target_cities)

    def _is_target_size(self, contact) -> bool:
        """Check if contact matches target size criteria."""
        params = self.TARGET_PARAMS

        units = getattr(contact, 'units', None)
        employees = getattr(contact, 'employees', None)

        if units:
            if params['min_units'] <= units <= params['max_units']:
                return True

        if employees:
            if employees <= params['max_employees']:
                return True

        return False

    def _format_units(self, units: Optional[int]) -> str:
        """Format units for German text."""
        if not units:
            return ""

        if units == 1:
            return "eine Einheit"
        elif units < 10:
            return f"{units} Einheiten"
        else:
            return f"über {units} Einheiten"

    def _format_employees(self, employees: Optional[int]) -> str:
        """Format employees for German text."""
        if not employees:
            return ""

        if employees == 1:
            return "einem Mitarbeiter"
        elif employees < 10:
            return f"{employees} Mitarbeitern"
        else:
            return f"einem Team von {employees} Mitarbeitern"

    def _format_location(self, address: Optional[str]) -> str:
        """Format location for email text."""
        location = self._extract_location(address)

        if not location:
            return "Ihrem Standort"

        if self._is_target_location(address):
            return f"{location} und Umgebung"
        else:
            return location

    def _get_greeting(self, contact: ScraperResult) -> str:
        """
        Get personalized German greeting using decision maker if available.

        Prioritizes personal greeting when decision maker name is known.
        Falls back to formal company greeting.
        """
        decision_maker_name = getattr(contact, 'decision_maker_name', None)
        decision_maker_title = getattr(contact, 'decision_maker_title', None)

        if decision_maker_name:
            # Clean the name (remove any remaining artifacts)
            name = decision_maker_name.strip()

            # Determine title and salutation
            if decision_maker_title:
                title = decision_maker_title.strip()
                # Map common German titles to appropriate salutations
                if any(t in title.lower() for t in ['geschäftsführer', 'inhaber', 'direktor', 'ceo']):
                    if 'frau' in name.lower() or name.endswith('a') or name.endswith('e'):
                        # Female
                        return f"Sehr geehrte Frau {name},"
                    else:
                        # Male
                        return f"Sehr geehrter Herr {name},"
                elif 'prokurist' in title.lower() or 'leiter' in title.lower():
                    if 'frau' in name.lower() or name.endswith('a') or name.endswith('e'):
                        return f"Sehr geehrte Frau {name},"
                    else:
                        return f"Sehr geehrter Herr {name},"

            # No title or unknown title - try to determine gender from name
            # German naming patterns for gender inference
            female_endings = ('a', 'e', 'i', 'y')
            female_patterns = ('maria', 'anna', 'sabine', 'monika', 'barbara', 'christine',
                              'ulrike', 'stephanie', 'nadia', 'julia', 'sandra')

            name_lower = name.lower()

            if name_lower in female_patterns or name.endswith(female_endings):
                return f"Sehr geehrte Frau {name},"
            else:
                # Default to male salutation (more common in German business)
                return f"Sehr geehrter Herr {name},"

        # Fallback to generic greeting
        return "Sehr geehrte Damen und Herren,"

    def _calculate_personalization(self, context: Dict[str, Any]) -> float:
        """
        Calculate personalization score (0-1).

        Higher score = more personalized email.
        Based on data quality and decision maker availability.
        """
        score = 0.0
        max_score = 1.0  # Total 100%

        # === DECISION MAKER (40%) - Most valuable for personalization ===
        # Decision maker name: 20%
        if context.get('decision_maker_name'):
            score += 0.20

        # Decision maker email (direct contact): 10%
        if context.get('decision_maker_email'):
            score += 0.10

        # Decision maker title: 5%
        if context.get('decision_maker_title'):
            score += 0.05

        # Has any decision maker info: 5%
        if context.get('has_decision_maker'):
            score += 0.05

        # === DATA QUALITY (40%) ===
        # Company name: always included, 5%
        if context.get('company_name'):
            score += 0.05

        # Location in target region: 10%
        if context.get('is_target_location'):
            score += 0.10

        # Target size match: 10%
        if context.get('is_target_size'):
            score += 0.10

        # Units info: 5%
        if context.get('company', {}).get('units'):
            score += 0.05

        # Employees info: 5%
        if context.get('company', {}).get('employees'):
            score += 0.05

        # Business email (not free provider): 5%
        if context.get('is_business_email'):
            score += 0.05

        # === RELEVANCE (20%) ===
        # Company description from website: 10%
        if context.get('company_description'):
            score += 0.10

        # Years in business (established company): 5%
        if context.get('years_in_business') and context.get('years_in_business') > 0:
            score += 0.05

        # Completeness score: 5%
        completeness = context.get('completeness_score', 0)
        if completeness > 0.7:
            score += 0.05
        elif completeness > 0.5:
            score += 0.03

        # Normalize to 0-1 range
        return min(score, 1.0)

    def generate_batch(
        self,
        contacts: List[ScraperResult],
        template_name: str = 'initial_contact',
        min_personalization: float = 0.5,
        filter_grade: Optional[LeadQuality] = LeadQuality.A,
        format: str = 'text'
    ) -> List[EmailDraft]:
        """
        Generate email drafts for multiple contacts.

        Args:
            contacts: List of contacts to generate emails for
            template_name: Name of template to use
            min_personalization: Minimum personalization score required
            filter_grade: Only generate for contacts of this grade or higher
            format: Output format - 'text' or 'html' (default: 'text')

        Returns:
            List of generated email drafts
        """
        drafts = []

        for contact in contacts:
            # Skip if no email
            if not contact.email:
                logger.debug(f"Skipping {contact.company_name}: no email")
                continue

            # Generate draft
            draft = self.generate(contact, template_name, format=format)

            if draft is None:
                continue

            # Check personalization threshold
            if draft.personalization_score < min_personalization:
                logger.debug(
                    f"Skipping {contact.company_name}: "
                    f"personalization {draft.personalization_score:.2f} < {min_personalization}"
                )
                continue

            drafts.append(draft)

        logger.info(
            f"Generated {len(drafts)} email drafts from {len(contacts)} contacts"
        )

        return drafts

    def preview(self, draft: EmailDraft, highlights: bool = True) -> str:
        """
        Generate preview of email draft.

        Args:
            draft: Email draft to preview
            highlights: Whether to highlight personalization

        Returns:
            Formatted preview string
        """
        lines = [
            "=" * 60,
            "EMAIL PREVIEW",
            "=" * 60,
            "",
            f"An: {draft.recipient_email}",
            f"Unternehmen: {draft.company_name}",
            "",
            f"Betreff: {draft.subject}",
            "",
            "-" * 60,
            draft.body,
            "-" * 60,
            "",
        ]

        if highlights:
            lines.extend([
                "PERSONALISIERUNG:",
                f"  Score: {draft.personalization_score:.2%}",
                f"  Template: {draft.template_used}",
            ])

            if draft.metadata:
                lines.append("  Metadata:")
                for key, value in draft.metadata.items():
                    if value:
                        lines.append(f"    - {key}: {value}")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)

    def validate_draft(self, draft: EmailDraft) -> List[str]:
        """
        Validate email draft for common issues.

        Args:
            draft: Email draft to validate

        Returns:
            List of validation issues (empty if valid)
        """
        issues = []

        # Check length (150-250 words ideal)
        word_count = len(draft.body.split())
        if word_count < 150:
            issues.append(f"Email too short: {word_count} words (min 150)")
        elif word_count > 300:
            issues.append(f"Email too long: {word_count} words (max 250 ideal)")

        # Check for placeholder text
        placeholders = ['[', ']', '{', '}', 'TODO', 'FIXME', 'XXX']
        for placeholder in placeholders:
            if placeholder in draft.body:
                issues.append(f"Placeholder found: {placeholder}")

        # Check subject
        if not draft.subject:
            issues.append("Missing subject line")

        if draft.subject and len(draft.subject) > 78:
            issues.append(f"Subject too long: {len(draft.subject)} chars (max 78)")

        # Check recipient
        if not draft.recipient_email:
            issues.append("Missing recipient email")

        # Check for required elements
        required_elements = [
            ('company_name', draft.company_name),
            ('sender', 'SE Handwerk' in draft.body or 'se-handwerk' in draft.body.lower()),
            ('greeting', 'geehrte' in draft.body.lower() or 'hallo' in draft.body.lower()),
            ('closing', 'mit freundlichen' in draft.body.lower() or 'grüße' in draft.body.lower())
        ]

        for name, present in required_elements:
            if not present:
                issues.append(f"Missing required element: {name}")

        return issues