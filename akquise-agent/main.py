#!/usr/bin/env python3
"""
Akquise Agent - Main Entry Point

B2B Acquisition tool for SE Handwerk
Automates research of property management companies and generates personalized emails.

Usage:
    python main.py --full              # Run complete workflow
    python main.py --scrape --source gelbe_seiten  # Scrape specific source
    python main.py --generate-emails   # Generate email drafts
    python main.py --export            # Export contacts to CSV
    python main.py --schedule          # Start follow-up scheduler
    python main.py --check-replies     # Check for email responses
    python main.py --status            # Show system status
"""

import argparse
import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from loguru import logger

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level:<7} | {message}")

# Import modules
from src.scrapers.base import ScraperResult
from src.scrapers.gelbe_seiten import GelbeSeitenScraper
from src.scrapers.immoscout import ImmoScoutScraper
from src.scrapers.hausverwaltung import HausverwaltungScraper
from src.scrapers.google_maps import GoogleMapsScraper
from src.enrichment.email_validator import EmailValidator
from src.enrichment.website_parser import WebsiteParser
from src.enrichment.deduplication import Deduplicator
from src.enrichment.quality_scorer import QualityScorer
from src.generators.email_generator import EmailGenerator
from src.followup.tracker import FollowUpTracker
from src.followup.generator import FollowUpGenerator
from src.notifications.telegram import TelegramNotifier, TelegramConfig
from src.notifications.scheduler import NotificationScheduler, ScheduleConfig
from src.state.manager import SearchStateManager
from src.state.duplicate_store import DuplicateStore
from src.storage.models import Contact, FollowUp, ContactStatus
from src.storage.sheets import GoogleSheetsClient, SheetsConfig
from src.storage.imap_drafts import IMAPDraftSaver, IMAPConfig
from src.storage.response_checker import ResponseChecker
from src.storage.sync import SyncManager
from src.export.csv_export import CSVExporter

console = Console()


class AkquiseAgent:
    """
    Main Akquise Agent class that orchestrates all components.
    """

    def __init__(self, config_dir: str = "config"):
        """
        Initialize the Akquise Agent.

        Args:
            config_dir: Path to configuration directory
        """
        self.config_dir = Path(config_dir)

        # Initialize components
        self.sheets_client: Optional[GoogleSheetsClient] = None
        self.telegram: Optional[TelegramNotifier] = None
        self.email_validator = EmailValidator()
        self.website_parser = WebsiteParser()
        self.deduplication = Deduplicator()
        self.quality_scorer = QualityScorer()
        self.email_generator = EmailGenerator()
        self.followup_generator = FollowUpGenerator()
        self.followup_tracker = FollowUpTracker()
        self.sync_manager = SyncManager()
        self.csv_exporter = CSVExporter()

        # IMAP Draft saver - saves drafts directly to email account!
        self.imap_drafts = IMAPDraftSaver(IMAPConfig.from_env())

        # Response checker - checks for email replies
        self.response_checker = ResponseChecker()

        # State persistence for resume capability
        self.search_state = SearchStateManager(state_dir="data")
        self.duplicate_store = DuplicateStore(db_path="data/akquise.db")

        # Scrapers
        self.scrapers = {
            'gelbe_seiten': GelbeSeitenScraper,
            'immoscout': ImmoScoutScraper,
            'hausverwaltung': HausverwaltungScraper,
            'google_maps': GoogleMapsScraper,
        }

    def _load_sheets_config(self) -> Optional[SheetsConfig]:
        """Load Google Sheets configuration."""
        config_file = self.config_dir / "google_sheets.yaml"

        if config_file.exists():
            import yaml
            with open(config_file) as f:
                config = yaml.safe_load(f)
                return SheetsConfig(
                    spreadsheet_id=config.get('spreadsheet_id', ''),
                    credentials_file=config.get('credentials_file', 'config/credentials.json'),
                    contacts_sheet=config.get('contacts_sheet', 'Kontakte'),
                    followups_sheet=config.get('followups_sheet', 'Follow-Ups')
                )

        # Fallback to environment
        return SheetsConfig.from_env()

    def _load_telegram_config(self) -> TelegramConfig:
        """Load Telegram configuration."""
        config_file = self.config_dir / "google_sheets.yaml"

        if config_file.exists():
            import yaml
            with open(config_file) as f:
                config = yaml.safe_load(f)
                telegram = config.get('telegram', {})
                return TelegramConfig(
                    bot_token=telegram.get('bot_token', ''),
                    user_id=telegram.get('user_id', '')
                )

        # Fallback to environment
        return TelegramConfig.from_env()

    def connect_sheets(self) -> bool:
        """Connect to Google Sheets."""
        config = self._load_sheets_config()

        if not config.spreadsheet_id or config.spreadsheet_id == "YOUR_SPREADSHEET_ID":
            console.print("[yellow]Google Sheets not configured. Set GOOGLE_SPREADSHEET_ID or config/google_sheets.yaml[/yellow]")
            return False

        self.sheets_client = GoogleSheetsClient(config)
        if self.sheets_client.connect():
            self.sync_manager.sheets = self.sheets_client
            console.print(f"[green]Connected to Google Sheets[/green]")
            return True
        return False

    def connect_telegram(self) -> bool:
        """Connect to Telegram."""
        config = self._load_telegram_config()
        self.telegram = TelegramNotifier(config)

        if self.telegram.is_configured:
            console.print("[green]Telegram notifications enabled[/green]")
            return True
        else:
            console.print("[yellow]Telegram not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_USER_ID.[/yellow]")
            return False

    def scrape(self, sources: List[str] = None, query: str = "Hausverwaltung",
               location: str = "Heilbronn", max_results: int = 50,
               existing_companies: set = None, resume: bool = False) -> List[ScraperResult]:
        """
        Run scraping from specified sources.

        Args:
            sources: List of sources to scrape (default: all)
            query: Search query
            location: Location to search
            max_results: Maximum results per source
            existing_companies: Set of existing company names to skip (for duplicate pre-check)
            resume: Whether to resume from previous session

        Returns:
            List of scraper results
        """
        sources = sources or list(self.scrapers.keys())
        results = []
        existing_companies = existing_companies or set()

        # Add duplicates from SQLite store
        db_companies = self.duplicate_store.get_all_companies()
        existing_companies.update(db_companies)

        # Create or resume search state
        state = None
        if resume:
            for source in sources:
                state = self.search_state.load_or_create(
                    source=source,
                    location=location,
                    query=query,
                    resume=True
                )
                if state:
                    console.print(f"[cyan]Resuming session {state.session_id}[/cyan]")
                    existing_companies.update(state.get_processed_companies())
                    break

        console.print(f"\n[bold]Starting scraping...[/bold]")
        console.print(f"  Sources: {', '.join(sources)}")
        console.print(f"  Query: {query}")
        console.print(f"  Location: {location}")
        console.print(f"  Max results per source: {max_results}")
        console.print(f"  Duplicate store: {len(db_companies)} known companies")
        if existing_companies:
            console.print(f"  Total to skip: {len(existing_companies)}\n")
        else:
            console.print("")

        async def run_scrapers():
            all_results = []
            skipped_duplicates = 0

            for source_name in sources:
                if source_name not in self.scrapers:
                    console.print(f"[yellow]Unknown source: {source_name}[/yellow]")
                    continue

                # Create new state for each source if not resuming
                if not resume or not state:
                    source_state = self.search_state.create_session(
                        source=source_name,
                        location=location,
                        query=query
                    )
                else:
                    source_state = state

                console.print(f"[cyan]Scraping {source_name}...[/cyan]")

                try:
                    scraper_class = self.scrapers[source_name]
                    scraper = scraper_class()

                    # Run async scraping
                    source_results = []
                    async for result in scraper.scrape(
                        query=query,
                        location=location,
                        max_results=max_results
                    ):
                        # Check for duplicates against existing contacts
                        company_key = result.company_name.lower().strip() if result.company_name else ""

                        # Check SQLite duplicate store
                        if self.duplicate_store.is_duplicate(
                            company_name=result.company_name,
                            email=result.email,
                            phone=result.phone
                        ):
                            skipped_duplicates += 1
                            logger.debug(f"Skipping duplicate (DB): {result.company_name}")
                            continue

                        # Check in-memory set
                        if company_key and company_key in existing_companies:
                            skipped_duplicates += 1
                            logger.debug(f"Skipping duplicate (memory): {result.company_name}")
                            continue

                        source_results.append(result)

                        # Add to duplicate store
                        self.duplicate_store.add_company(
                            company_name=result.company_name,
                            email=result.email,
                            phone=result.phone,
                            source=result.source
                        )

                        # Track in search state (use manager methods)
                        self.search_state.add_processed(result.company_name)

                    all_results.extend(source_results)
                    console.print(f"  [green]Found {len(source_results)} results[/green]")

                    # Save state after each source (use manager methods)
                    self.search_state.update_progress(total=len(all_results))
                    self.search_state.save()

                except Exception as e:
                    logger.error(f"Scraping {source_name} failed: {e}")
                    console.print(f"  [red]Error: {e}[/red]")

            if skipped_duplicates > 0:
                console.print(f"  [yellow]Skipped {skipped_duplicates} duplicates from existing contacts[/yellow]")

            return all_results

        # Run async scrapers
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        results = loop.run_until_complete(run_scrapers())

        console.print(f"\n[bold green]Total: {len(results)} results from {len(sources)} sources[/bold green]")
        return results

    def enrich(self, results: List[ScraperResult]) -> List[Contact]:
        """
        Enrich scraper results with email validation and scoring.
        Only returns contacts that meet minimum requirements (email OR phone + address).

        Args:
            results: Scraper results to enrich

        Returns:
            List of enriched contacts that meet minimum requirements
        """
        console.print(f"\n[bold]Enriching {len(results)} results...[/bold]")

        contacts = []
        seen_companies = set()
        filtered_out = 0

        # Minimum requirements - set to 0 temporarily for testing pipeline
        # TODO: Increase to 35 after fixing scrapers to extract contact data
        MIN_COMPLETENESS_SCORE = 0  # Minimum score to be saved

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Processing...", total=len(results))

            for result in results:
                progress.update(task, description=f"Processing {result.company_name[:30]}...")

                # Skip duplicates within batch
                company_key = result.company_name.lower().strip()
                if company_key in seen_companies:
                    continue
                seen_companies.add(company_key)

                # Get or create event loop for async operations
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                # Validate email (async)
                validated_email = None
                email_valid = False
                if result.email:
                    try:
                        validation_result = loop.run_until_complete(
                            self.email_validator.validate(result.email)
                        )
                        if validation_result and validation_result.is_valid:
                            validated_email = result.email
                            email_valid = True
                    except Exception as e:
                        logger.debug(f"Email validation failed: {e}")

                # Parse website for additional info (async)
                units = result.units
                employees = None
                website_description = None
                founding_year = None
                decision_maker = None

                if result.website:
                    try:
                        site_info = loop.run_until_complete(
                            self.website_parser.parse(result.website)
                        )
                        if not units and site_info.units_managed:
                            units = site_info.units_managed
                        employees = site_info.employee_count
                        website_description = site_info.description
                        founding_year = site_info.founding_year

                        # Extract decision maker
                        if site_info.decision_makers:
                            dm = site_info.decision_makers[0]  # Get first/best match
                            decision_maker = {
                                'name': dm.name,
                                'title': dm.title,
                                'email': dm.email,
                                'phone': dm.phone
                            }
                            logger.info(f"Found decision maker for {result.company_name}: {dm.name} ({dm.title})")

                        # Try to get email from website if not available
                        if not validated_email and site_info.impressum_email:
                            try:
                                validation_result = loop.run_until_complete(
                                    self.email_validator.validate(site_info.impressum_email)
                                )
                                if validation_result and validation_result.is_valid:
                                    validated_email = site_info.impressum_email
                                    email_valid = True
                            except Exception:
                                pass

                    except Exception as e:
                        logger.debug(f"Website parsing failed for {result.website}: {e}")

                # Calculate completeness score
                completeness_score = self._calculate_completeness(
                    email=validated_email,
                    phone=result.phone,
                    address=result.address,
                    website=result.website,
                    units=units,
                    employees=employees,
                    rating=result.rating,
                    website_description=website_description
                )

                # Check minimum requirements
                # TODO: Restore stricter requirements after fixing scrapers
                # For now, save all contacts with company names (minimum for testing)
                # Original requirements: has_contact AND has_address AND completeness >= 35
                if not result.company_name:
                    logger.debug(f"Filtering out: no company name")
                    filtered_out += 1
                    progress.advance(task)
                    continue

                # Score quality
                assessment = self.quality_scorer.assess(result)

                # Create contact with all enrichment data
                contact = Contact(
                    company_name=result.company_name,
                    address=result.address,
                    phone=result.phone,
                    email=validated_email,
                    website=result.website,
                    units=units,
                    employees=employees,
                    source=result.source,
                    score=assessment.score,
                    qualification=assessment.grade.value,
                    website_description=website_description,
                    founding_year=founding_year,
                    email_valid=email_valid,
                    completeness_score=completeness_score,
                    # Decision maker
                    decision_maker_name=decision_maker['name'] if decision_maker else None,
                    decision_maker_title=decision_maker['title'] if decision_maker else None,
                    decision_maker_email=decision_maker['email'] if decision_maker else None,
                    decision_maker_phone=decision_maker['phone'] if decision_maker else None,
                )

                contacts.append(contact)
                progress.advance(task)

        console.print(
            f"[green]Enriched {len(contacts)} contacts[/green] "
            f"[dim]({filtered_out} filtered out)[/dim]"
        )
        return contacts

    def _calculate_completeness(
        self,
        email: Optional[str],
        phone: Optional[str],
        address: Optional[str],
        website: Optional[str],
        units: Optional[int],
        employees: Optional[int],
        rating: Optional[float],
        website_description: Optional[str]
    ) -> int:
        """
        Calculate completeness score (0-100).
        Higher weight on contact data.
        """
        score = 0

        # Essential contact info (45 points)
        if email:
            score += 25
        if phone:
            score += 20

        # Address for personalization (15 points)
        if address:
            score += 15

        # Business info (25 points)
        if website:
            score += 10
        if units:
            score += 10
        if employees:
            score += 5

        # Quality indicators (15 points)
        if rating and rating >= 3.5:
            score += 5
        if website_description:
            score += 10

        return score

    def generate_emails(self, contacts: List[Contact]) -> List[Contact]:
        """
        Generate email drafts for contacts and save to IMAP Drafts folder.

        WICHTIG: E-Mails werden NICHT automatisch versendet!
        Entwürfe werden im E-Mail-Konto im "Entwürfe"-Ordner gespeichert.
        Du kannst sie direkt in Outlook/Thunderbird öffnen und senden.

        Args:
            contacts: Contacts to generate emails for

        Returns:
            Contacts with email drafts
        """
        console.print(f"\n[bold]Generating email drafts for {len(contacts)} contacts...[/bold]")
        console.print("[dim]Entwürfe werden im E-Mail-Konto gespeichert (IMAP Drafts)[/dim]\n")

        generated = 0
        saved_to_imap = 0
        failed_imap = 0

        # Check IMAP configuration
        if not self.imap_drafts.is_configured:
            console.print("[yellow]IMAP not configured. Set SMTP_USER and SMTP_PASSWORD in .env[/yellow]")
            console.print("[yellow]Drafts will only be saved to Google Sheets, not to email account.[/yellow]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Generating...", total=len(contacts))

            for contact in contacts:
                progress.update(task, description=f"Email for {contact.company_name[:30]}...")

                # Skip contacts without email
                if not contact.email:
                    contact.email_draft = None
                    progress.advance(task)
                    continue

                try:
                    # Generate initial contact email
                    draft = self.email_generator.generate(contact, template_name='initial_contact')
                    if draft:
                        contact.email_draft = draft.body
                        generated += 1

                        # Save draft to IMAP (email account Drafts folder)
                        if self.imap_drafts.is_configured:
                            try:
                                loop = asyncio.get_event_loop()
                            except RuntimeError:
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)

                            async def save_imap():
                                return await self.imap_drafts.save_draft(
                                    to=contact.email,
                                    subject=draft.subject,
                                    body_html=draft.body
                                )

                            try:
                                saved = loop.run_until_complete(save_imap())
                                if saved:
                                    saved_to_imap += 1
                                else:
                                    failed_imap += 1
                            except Exception as e:
                                logger.error(f"Failed to save IMAP draft for {contact.company_name}: {e}")
                                failed_imap += 1

                        # Small delay to avoid rate limiting
                        import time
                        time.sleep(0.5)

                except Exception as e:
                    logger.warning(f"Failed to generate email for {contact.company_name}: {e}")
                    contact.email_draft = None

                progress.advance(task)

        console.print(f"\n[green]Generated {generated} email drafts[/green]")
        if saved_to_imap > 0:
            console.print(f"[green]Saved {saved_to_imap} drafts to IMAP (Entwürfe-Ordner)[/green]")
        if failed_imap > 0:
            console.print(f"[yellow]Failed to save {failed_imap} drafts to IMAP[/yellow]")

        console.print("\n[cyan]→ Öffne dein E-Mail-Programm (Outlook/Thunderbird)[/cyan]")
        console.print("[cyan]→ Gehe zu 'Entwürfe' oder 'Drafts'[/cyan]")
        console.print("[cyan]→ Öffne die E-Mails, prüfe sie und sende sie manuell[/cyan]")

        return contacts

    def save_to_sheets(self, contacts: List[Contact]) -> int:
        """
        Save contacts to Google Sheets.

        Args:
            contacts: Contacts to save

        Returns:
            Number of contacts saved
        """
        if not self.sheets_client:
            console.print("[yellow]Google Sheets not connected[/yellow]")
            return 0

        console.print(f"\n[bold]Saving {len(contacts)} contacts to Google Sheets...[/bold]")

        saved = 0
        duplicates = 0

        for contact in contacts:
            # Check for duplicates
            existing = self.sheets_client.find_duplicate(contact)
            if existing:
                duplicates += 1
                logger.info(f"Skipping duplicate: {contact.company_name}")
                continue

            # Add contact
            if self.sheets_client.add_contact(contact):
                saved += 1

        console.print(f"[green]Saved {saved} contacts ({duplicates} duplicates skipped)[/green]")
        return saved

    def notify_new_leads(self, contacts: List[Contact]) -> None:
        """Send Telegram notifications for A-class leads."""
        if not self.telegram:
            return

        a_class = [c for c in contacts if c.qualification == 'A']

        if not a_class:
            console.print("[dim]No A-class leads to notify[/dim]")
            return

        console.print(f"\n[bold]Notifying about {len(a_class)} A-class leads...[/bold]")

        async def send_notifications():
            sheets_url = self.sheets_client.get_sheet_url() if self.sheets_client else None

            for contact in a_class:
                await self.telegram.send_lead_notification(
                    company_name=contact.company_name,
                    address=contact.address,
                    phone=contact.phone,
                    email=contact.email,
                    units=contact.units,
                    score=contact.score,
                    grade=contact.qualification,
                    sheets_url=sheets_url
                )

        try:
            asyncio.get_event_loop().run_until_complete(send_notifications())
        except RuntimeError:
            asyncio.run(send_notifications())

    def export_csv(self, output_dir: str = "data/exports") -> int:
        """
        Export contacts to CSV files.

        Args:
            output_dir: Output directory

        Returns:
            Number of contacts exported
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        if not self.sheets_client:
            console.print("[yellow]Google Sheets not connected[/yellow]")
            return 0

        contacts = self.sheets_client.get_all_contacts()

        if not contacts:
            console.print("[yellow]No contacts to export[/yellow]")
            return 0

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Export all contacts
        all_file = output_path / f"contacts_{timestamp}.csv"
        self.csv_exporter.export_contacts(contacts, str(all_file))

        # Export A-class leads
        a_class = [c for c in contacts if c.qualification == 'A']
        if a_class:
            a_file = output_path / f"a_class_leads_{timestamp}.csv"
            self.csv_exporter.export_contacts(a_class, str(a_file))

        # Export for mail merge
        mail_file = output_path / f"mail_merge_{timestamp}.csv"
        self.csv_exporter.export_for_mail_merge(contacts, str(mail_file))

        console.print(f"[green]Exported {len(contacts)} contacts to {output_path}[/green]")
        return len(contacts)

    def show_status(self) -> None:
        """Show system status."""
        console.print("\n[bold blue]Akquise Agent Status[/bold blue]\n")

        # Connection status table
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Component", style="white")
        table.add_column("Status", style="white")
        table.add_column("Details", style="dim")

        # Google Sheets
        if self.sheets_client and self.sheets_client.is_available:
            sheets_status = "[green]Connected[/green]"
            sheets_details = self.sheets_client.config.spreadsheet_id[:20] + "..."
        else:
            sheets_status = "[yellow]Not configured[/yellow]"
            sheets_details = "Set GOOGLE_SPREADSHEET_ID"

        table.add_row("Google Sheets", sheets_status, sheets_details)

        # Telegram
        if self.telegram and self.telegram.is_configured:
            telegram_status = "[green]Configured[/green]"
            telegram_details = f"User ID: {self.telegram.config.user_id}"
        else:
            telegram_status = "[yellow]Not configured[/yellow]"
            telegram_details = "Set TELEGRAM_BOT_TOKEN and TELEGRAM_USER_ID"

        table.add_row("Telegram", telegram_status, telegram_details)

        # Scrapers
        table.add_row(
            "Scrapers",
            "[green]Ready[/green]",
            f"{len(self.scrapers)} sources available"
        )

        console.print(table)

        # Statistics
        if self.sheets_client and self.sheets_client.is_available:
            console.print("\n[bold]Statistics[/bold]")

            stats = self.sync_manager.get_statistics()

            stats_table = Table(show_header=True, header_style="bold cyan")
            stats_table.add_column("Metric", style="white")
            stats_table.add_column("Count", style="cyan")

            stats_table.add_row("Total Contacts", str(stats.get('total_contacts', 0)))
            stats_table.add_row("A-Class Leads", str(stats.get('a_class', 0)))
            stats_table.add_row("B-Class Leads", str(stats.get('b_class', 0)))
            stats_table.add_row("C-Class Leads", str(stats.get('c_class', 0)))
            stats_table.add_row("Open Follow-Ups", str(stats.get('open_followups', 0)))

            console.print(stats_table)

    def check_responses(self, days_back: int = 30) -> Dict[str, Any]:
        """
        Check for email responses and update contact status.

        Args:
            days_back: How many days back to check for replies

        Returns:
            Dict with response check results
        """
        console.print("\n[bold blue]Prüfe auf E-Mail-Antworten...[/bold blue]\n")

        if not self.response_checker.is_configured:
            console.print("[red]IMAP nicht konfiguriert![/red]")
            console.print("[dim]Setze SMTP_USER und SMTP_PASSWORD in .env[/dim]")
            return {'error': 'IMAP not configured'}

        # Get contacts with sent emails
        if not self.sheets_client:
            console.print("[red]Google Sheets nicht verbunden![/red]")
            return {'error': 'Google Sheets not connected'}

        contacts = self.sheets_client.get_all_contacts()
        sent_emails = [
            {'to': c.email, 'subject': c.email_draft.split('\n')[0] if c.email_draft else ''}
            for c in contacts
            if c.email and c.email_draft and c.status in ['Kontaktiert', 'CONTACTED']
        ]

        if not sent_emails:
            console.print("[yellow]Keine gesendeten E-Mails gefunden[/yellow]")
            return {'checked': 0, 'responses': 0}

        console.print(f"[cyan]Prüfe {len(sent_emails)} gesendete E-Mails auf Antworten...[/cyan]")

        async def _check():
            if not await self.response_checker.connect():
                return {}

            try:
                return await self.response_checker.get_replies(sent_emails, days_back=days_back)
            finally:
                await self.response_checker.disconnect()

        # Run async check
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        responses = loop.run_until_complete(_check())

        # Display results
        if responses:
            console.print(f"\n[green]✓ {len(responses)} Antworten gefunden![/green]\n")

            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Von", style="white")
            table.add_column("Betreff", style="cyan")
            table.add_column("Datum", style="dim")

            for email, reply in responses.items():
                # Find contact by email
                contact = next((c for c in contacts if c.email and c.email.lower() == email.lower()), None)

                # Update contact status
                if contact:
                    contact.status = ContactStatus.REPLIED
                    self.sheets_client.update_contact(contact)

                table.add_row(
                    reply.sender_name[:30] if reply.sender_name else reply.sender[:30],
                    reply.subject[:40] if reply.subject else "-",
                    reply.date.strftime('%d.%m.%Y') if reply.date else "-"
                )

            console.print(table)

            # Update statistics
            stats = {
                'checked': len(sent_emails),
                'responses': len(responses),
                'response_rate': len(responses) / len(sent_emails) if sent_emails else 0
            }

            console.print(f"\n[bold]Antwortrate: {stats['response_rate']:.1%}[/bold]")

            return stats
        else:
            console.print("[yellow]Keine Antworten gefunden[/yellow]")
            return {'checked': len(sent_emails), 'responses': 0}

    def list_drafts(self) -> None:
        """List all saved email drafts (from IMAP if configured)."""
        console.print("\n[bold]E-Mail-Entwürfe[/bold]\n")

        if self.imap_drafts.is_configured:
            console.print("[cyan]IMAP konfiguriert - Entwürfe im E-Mail-Konto[/cyan]")
            console.print("[dim]Öffne dein E-Mail-Programm und gehe zu 'Entwürfe'/'Drafts'[/dim]")
        else:
            console.print("[yellow]IMAP nicht konfiguriert[/yellow]")
            console.print("[dim]Setze SMTP_USER und SMTP_PASSWORD in .env[/dim]")

        # Show contacts with email drafts from Google Sheets
        if self.sheets_client:
            contacts = self.sheets_client.get_all_contacts()
            with_drafts = [c for c in contacts if c.email and c.email_draft]

            if with_drafts:
                table = Table(show_header=True, header_style="bold cyan")
                table.add_column("#", style="dim", width=3)
                table.add_column("Firma", style="white")
                table.add_column("E-Mail", style="cyan")
                table.add_column("Entscheider", style="green")
                table.add_column("Qualifikation", style="yellow")

                for i, contact in enumerate(with_drafts[:30], 1):
                    dm_name = getattr(contact, 'decision_maker_name', '') or ''
                    dm_str = dm_name[:25] if dm_name else "-"

                    table.add_row(
                        str(i),
                        contact.company_name[:30] if len(contact.company_name) > 30 else contact.company_name,
                        contact.email,
                        dm_str,
                        contact.qualification
                    )

                console.print(table)
                console.print(f"\n[bold]Total: {len(with_drafts)} Kontakte mit E-Mail-Entwürfen[/bold]")
            else:
                console.print("[dim]Keine Entwürfe in Google Sheets[/dim]")

    def show_draft_stats(self) -> None:
        """Show draft statistics."""
        console.print("\n[bold]E-Mail-Entwurf Statistiken[/bold]\n")

        if self.sheets_client:
            contacts = self.sheets_client.get_all_contacts()
            with_drafts = len([c for c in contacts if c.email and c.email_draft])
            with_email = len([c for c in contacts if c.email])

            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Status", style="white")
            table.add_column("Anzahl", style="cyan")

            table.add_row("Kontakte mit E-Mail", str(with_email))
            table.add_row("E-Mail-Entwürfe generiert", str(with_drafts))
            table.add_row("Entwürfe im E-Mail-Konto", "[cyan]→ IMAP 'Entwürfe' Ordner[/cyan]")

            console.print(table)

        # Show IMAP status
        if self.imap_drafts.is_configured:
            console.print("\n[green]✓ IMAP verbunden: Entwürfe werden direkt ins E-Mail-Konto gespeichert[/green]")
        else:
            console.print("\n[yellow]⚠ IMAP nicht konfiguriert: Entwürfe nur in Google Sheets gespeichert[/yellow]")

    def run_full_workflow(
        self,
        sources: List[str] = None,
        query: str = "Hausverwaltung",
        location: str = "Heilbronn",
        max_results: int = 50,
        resume: bool = False
    ) -> List[Contact]:
        """
        Run the complete workflow: scrape -> enrich -> generate emails -> save -> notify.

        Args:
            sources: Sources to scrape
            query: Search query
            location: Location
            max_results: Max results per source
            resume: Whether to resume from previous session

        Returns:
            List of processed contacts
        """
        import time
        start_time = time.time()

        console.print(Panel.fit(
            "[bold blue]Akquise Agent - Full Workflow[/bold blue]\n"
            f"Query: {query} | Location: {location} | Max: {max_results} per source",
            border_style="blue"
        ))

        # Connect services
        self.connect_sheets()
        self.connect_telegram()

        # Pre-load existing contacts from Google Sheets to avoid duplicates
        existing_companies = set()
        if self.sheets_client:
            try:
                existing_contacts = self.sheets_client.get_all_contacts()
                for contact in existing_contacts:
                    if contact.company_name:
                        existing_companies.add(contact.company_name.lower().strip())
                console.print(f"[cyan]Loaded {len(existing_companies)} existing contacts from Google Sheets[/cyan]")
            except Exception as e:
                logger.warning(f"Could not load existing contacts: {e}")

        # Send execution start notification
        sources_to_scrape = sources or list(self.scrapers.keys())
        if self.telegram and self.telegram.is_configured:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            loop.run_until_complete(
                self.telegram.send_execution_start(
                    sources=sources_to_scrape,
                    max_results=max_results,
                    location=location
                )
            )

        # Step 1: Scrape (with duplicate pre-check and state persistence)
        results = self.scrape(
            sources=sources,
            query=query,
            location=location,
            max_results=max_results,
            existing_companies=existing_companies,
            resume=resume
        )

        if not results:
            console.print("[yellow]No results found[/yellow]")
            return []

        # Step 2: Enrich
        contacts = self.enrich(results)

        # Step 3: Generate emails
        contacts = self.generate_emails(contacts)

        # Step 4: Save to Sheets
        saved = self.save_to_sheets(contacts)

        # Step 5: Notify about A-class leads
        self.notify_new_leads(contacts)

        # Calculate statistics
        duration_seconds = int(time.time() - start_time)
        a_class = len([c for c in contacts if c.qualification == 'A'])
        b_class = len([c for c in contacts if c.qualification == 'B'])
        c_class = len([c for c in contacts if c.qualification == 'C'])
        emails_generated = len([c for c in contacts if c.email_draft])

        # Source statistics
        source_stats = {}
        for result in results:
            source = result.source
            source_stats[source] = source_stats.get(source, 0) + 1

        # Get top leads (A-class first, then B-class sorted by score)
        top_leads = []
        a_class_leads = sorted(
            [c for c in contacts if c.qualification == 'A'],
            key=lambda x: x.score or 0,
            reverse=True
        )
        b_class_leads = sorted(
            [c for c in contacts if c.qualification == 'B'],
            key=lambda x: x.score or 0,
            reverse=True
        )
        for c in a_class_leads[:5] + b_class_leads[:10]:
            top_leads.append({
                'company_name': c.company_name,
                'phone': c.phone,
                'email': c.email,
                'score': c.score,
                'qualification': c.qualification
            })

        # Send execution complete notification
        if self.telegram and self.telegram.is_configured:
            sheets_url = None
            if self.sheets_client:
                sheets_url = self.sheets_client.get_sheet_url()

            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            loop.run_until_complete(
                self.telegram.send_execution_complete(
                    total_scraped=len(results),
                    total_qualified=len(contacts),
                    a_class=a_class,
                    b_class=b_class,
                    c_class=c_class,
                    emails_generated=emails_generated,
                    saved_to_sheets=saved > 0,
                    duration_seconds=duration_seconds,
                    source_stats=source_stats,
                    sheets_url=sheets_url,
                    top_leads=top_leads
                )
            )

        # Summary
        console.print(Panel.fit(
            f"[bold green]Workflow Complete[/bold green]\n"
            f"Scraped: {len(results)} | Enriched: {len(contacts)} | Saved: {saved}\n"
            f"A-Class: {a_class} | "
            f"B-Class: {b_class} | "
            f"C-Class: {c_class}\n"
            f"Duration: {duration_seconds // 60}m {duration_seconds % 60}s",
            border_style="green"
        ))

        return contacts


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Akquise Agent - B2B Acquisition Tool for SE Handwerk",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --full                    # Run complete workflow
  python main.py --scrape --source gelbe_seiten  # Scrape specific source
  python main.py --generate-emails         # Generate email drafts
  python main.py --export                  # Export contacts to CSV
  python main.py --schedule                # Start follow-up scheduler
  python main.py --status                  # Show system status
        """
    )

    # Main commands
    parser.add_argument(
        "--full", "-f",
        action="store_true",
        help="Run complete workflow: scrape -> enrich -> generate emails -> save -> notify"
    )
    parser.add_argument(
        "--scrape", "-s",
        action="store_true",
        help="Run scraping from configured sources"
    )
    parser.add_argument(
        "--generate-emails", "-g",
        action="store_true",
        help="Generate email drafts for new contacts"
    )
    parser.add_argument(
        "--export", "-e",
        action="store_true",
        help="Export contacts to CSV"
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Start scheduler for automated follow-ups"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show system status and statistics"
    )
    parser.add_argument(
        "--check-replies",
        action="store_true",
        help="Check for email responses and update contact status"
    )
    parser.add_argument(
        "--days-back",
        type=int,
        default=30,
        help="Days to check back for replies (default: 30)"
    )

    # Options
    parser.add_argument(
        "--source",
        type=str,
        choices=["gelbe_seiten", "immoscout", "hausverwaltung", "google_maps", "all"],
        default="all",
        help="Specific source to scrape (default: all)"
    )
    parser.add_argument(
        "--query", "-q",
        type=str,
        default="Hausverwaltung",
        help="Search query (default: Hausverwaltung)"
    )
    parser.add_argument(
        "--location", "-l",
        type=str,
        default="Heilbronn",
        help="Location to search (default: Heilbronn)"
    )
    parser.add_argument(
        "--max-results", "-m",
        type=int,
        default=50,
        help="Maximum results per source (default: 50)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="data/exports",
        help="Output directory for exports (default: data/exports)"
    )
    parser.add_argument(
        "--config", "-c",
        type=str,
        default="config",
        help="Configuration directory (default: config)"
    )
    parser.add_argument(
        "--resume", "-r",
        action="store_true",
        help="Resume previous scraping session from saved state"
    )
    parser.add_argument(
        "--drafts",
        action="store_true",
        help="List saved email drafts"
    )
    parser.add_argument(
        "--draft-stats",
        action="store_true",
        help="Show draft statistics"
    )

    args = parser.parse_args()

    # Initialize agent
    agent = AkquiseAgent(config_dir=args.config)

    # Execute command
    if args.full:
        sources = None if args.source == "all" else [args.source]
        agent.run_full_workflow(
            sources=sources,
            query=args.query,
            location=args.location,
            max_results=args.max_results,
            resume=args.resume
        )

    elif args.scrape:
        agent.connect_sheets()
        agent.connect_telegram()
        sources = None if args.source == "all" else [args.source]
        results = agent.scrape(
            sources=sources,
            query=args.query,
            location=args.location,
            max_results=args.max_results
        )
        contacts = agent.enrich(results)
        contacts = agent.generate_emails(contacts)
        agent.save_to_sheets(contacts)
        agent.notify_new_leads(contacts)

    elif args.generate_emails:
        agent.connect_sheets()
        contacts = agent.sheets_client.get_all_contacts() if agent.sheets_client else []
        contacts_without_emails = [c for c in contacts if not c.email_draft and c.email]
        agent.generate_emails(contacts_without_emails)

        # Update contacts in sheets
        for contact in contacts_without_emails:
            if contact.email_draft:
                agent.sheets_client.update_contact(contact)

    elif args.export:
        agent.connect_sheets()
        agent.export_csv(output_dir=args.output)

    elif args.schedule:
        console.print("[bold]Starting follow-up scheduler...[/bold]")
        console.print("[dim]Press Ctrl+C to stop[/dim]\n")

        agent.connect_sheets()
        agent.connect_telegram()

        scheduler = NotificationScheduler()

        # Set up callbacks
        async def on_daily_summary():
            if agent.sheets_client and agent.telegram:
                contacts = agent.sheets_client.get_all_contacts()
                today = datetime.now().date()
                new_today = [c for c in contacts if c.created_at and c.created_at.date() == today]
                a_class = len([c for c in new_today if c.qualification == 'A'])
                b_class = len([c for c in new_today if c.qualification == 'B'])
                c_class = len([c for c in new_today if c.qualification == 'C'])
                followups = agent.sheets_client.get_open_followups()

                await agent.telegram.send_daily_summary(
                    total_new=len(new_today),
                    a_class=a_class,
                    b_class=b_class,
                    c_class=c_class,
                    followups_due=len(followups),
                    sheets_url=agent.sheets_client.get_sheet_url()
                )

        scheduler.set_callbacks(on_daily_summary=on_daily_summary)
        scheduler.start()

    elif args.status:
        agent.connect_sheets()
        agent.connect_telegram()
        agent.show_status()

    elif args.check_replies:
        agent.connect_sheets()
        agent.check_responses(days_back=args.days_back)

    elif args.drafts:
        agent.list_drafts()

    elif args.draft_stats:
        agent.show_draft_stats()

    else:
        # Show help
        parser.print_help()
        console.print("\n[dim]Use --help for available commands[/dim]")


if __name__ == "__main__":
    main()