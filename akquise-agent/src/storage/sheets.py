"""
Google Sheets client for contact storage.
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import os

from loguru import logger

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False
    logger.warning("gspread not installed - Google Sheets features disabled")

from .models import Contact, FollowUp, ContactStatus


@dataclass
class SheetsConfig:
    """Google Sheets configuration."""
    spreadsheet_id: str
    credentials_file: str = "config/credentials.json"
    contacts_sheet: str = "Kontakte"
    followups_sheet: str = "Follow-Ups"

    @classmethod
    def from_env(cls) -> 'SheetsConfig':
        """Load configuration from environment."""
        return cls(
            spreadsheet_id=os.getenv('GOOGLE_SPREADSHEET_ID', ''),
            credentials_file=os.getenv('GOOGLE_CREDENTIALS_FILE', 'config/credentials.json')
        )


class GoogleSheetsClient:
    """
    Google Sheets client for contact and follow-up storage.

    Features:
    - Read/write contacts
    - Read/write follow-ups
    - Duplicate detection
    - Batch operations
    - Rate limiting
    """

    # Column headers for Kontakte sheet
    CONTACT_HEADERS = [
        'ID', 'Firma', 'Adresse', 'Telefon', 'E-Mail', 'Website',
        'Einheiten', 'Mitarbeiter', 'Quelle', 'Qualifikation', 'Score',
        'Status', 'E-Mail_Entwurf', 'Erstellt_am', 'Follow_Up_1',
        'Follow_Up_2', 'Notizen'
    ]

    # Column headers for Follow-Ups sheet
    FOLLOWUP_HEADERS = [
        'ID', 'Kontakt_ID', 'Typ', 'Geplant_am', 'Status', 'Erledigt_am', 'Notizen'
    ]

    def __init__(self, config: Optional[SheetsConfig] = None):
        """
        Initialize Google Sheets client.

        Args:
            config: Sheets configuration
        """
        self.config = config or SheetsConfig.from_env()
        self._client = None
        self._spreadsheet = None
        self._contacts_sheet = None
        self._followups_sheet = None

    @property
    def is_available(self) -> bool:
        """Check if Google Sheets is available."""
        return GSPREAD_AVAILABLE and bool(self.config.spreadsheet_id)

    def connect(self) -> bool:
        """
        Connect to Google Sheets.

        Returns:
            True if connection successful
        """
        if not GSPREAD_AVAILABLE:
            logger.warning("gspread not available")
            return False

        if not self.config.spreadsheet_id:
            logger.warning("No spreadsheet ID configured")
            return False

        try:
            # Load credentials
            scopes = ['https://www.googleapis.com/auth/spreadsheets']

            if os.path.exists(self.config.credentials_file):
                creds = Credentials.from_service_account_file(
                    self.config.credentials_file,
                    scopes=scopes
                )
                self._client = gspread.authorize(creds)
            else:
                # Try default credentials
                self._client = gspread.service_account()

            # Open spreadsheet
            self._spreadsheet = self._client.open_by_key(self.config.spreadsheet_id)

            # Get or create sheets
            try:
                self._contacts_sheet = self._spreadsheet.worksheet(self.config.contacts_sheet)
            except gspread.WorksheetNotFound:
                self._contacts_sheet = self._spreadsheet.add_worksheet(
                    title=self.config.contacts_sheet,
                    rows=1000,
                    cols=17
                )
                self._contacts_sheet.append_row(self.CONTACT_HEADERS)

            try:
                self._followups_sheet = self._spreadsheet.worksheet(self.config.followups_sheet)
            except gspread.WorksheetNotFound:
                self._followups_sheet = self._spreadsheet.add_worksheet(
                    title=self.config.followups_sheet,
                    rows=1000,
                    cols=7
                )
                self._followups_sheet.append_row(self.FOLLOWUP_HEADERS)

            logger.info(f"Connected to Google Sheets: {self.config.spreadsheet_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Google Sheets: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect from Google Sheets."""
        self._client = None
        self._spreadsheet = None
        self._contacts_sheet = None
        self._followups_sheet = None
        logger.info("Disconnected from Google Sheets")

    # Contact Operations

    def add_contact(self, contact: Contact) -> bool:
        """
        Add a new contact to the sheet.

        Args:
            contact: Contact to add

        Returns:
            True if successful
        """
        if not self._contacts_sheet:
            logger.warning("Not connected to Google Sheets")
            return False

        try:
            self._contacts_sheet.append_row(contact.to_row())
            logger.info(f"Added contact: {contact.company_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to add contact: {e}")
            return False

    def add_contacts_batch(self, contacts: List[Contact]) -> int:
        """
        Add multiple contacts in batch.

        Args:
            contacts: List of contacts to add

        Returns:
            Number of contacts added
        """
        if not self._contacts_sheet:
            logger.warning("Not connected to Google Sheets")
            return 0

        try:
            rows = [c.to_row() for c in contacts]
            self._contacts_sheet.append_rows(rows)
            logger.info(f"Added {len(contacts)} contacts")
            return len(contacts)
        except Exception as e:
            logger.error(f"Failed to add contacts batch: {e}")
            return 0

    def get_contact(self, contact_id: str) -> Optional[Contact]:
        """
        Get a contact by ID.

        Args:
            contact_id: Contact ID

        Returns:
            Contact or None if not found
        """
        if not self._contacts_sheet:
            return None

        try:
            # Find by ID (column A)
            cell = self._contacts_sheet.find(contact_id, in_column=1)
            if cell:
                row = self._contacts_sheet.row_values(cell.row)
                return Contact.from_row(row)
            return None
        except Exception as e:
            logger.error(f"Failed to get contact: {e}")
            return None

    def get_all_contacts(self) -> List[Contact]:
        """
        Get all contacts.

        Returns:
            List of all contacts
        """
        if not self._contacts_sheet:
            return []

        try:
            records = self._contacts_sheet.get_all_records()
            contacts = []
            for record in records:
                # Convert record to row format
                row = [
                    record.get('ID', ''),
                    record.get('Firma', ''),
                    record.get('Adresse', ''),
                    record.get('Telefon', ''),
                    record.get('E-Mail', ''),
                    record.get('Website', ''),
                    str(record.get('Einheiten', '')),
                    str(record.get('Mitarbeiter', '')),
                    record.get('Quelle', ''),
                    record.get('Qualifikation', ''),
                    str(record.get('Score', '')),
                    record.get('Status', ''),
                    record.get('E-Mail_Entwurf', ''),
                    record.get('Erstellt_am', ''),
                    record.get('Follow_Up_1', ''),
                    record.get('Follow_Up_2', ''),
                    record.get('Notizen', '')
                ]
                contacts.append(Contact.from_row(row))
            return contacts
        except Exception as e:
            logger.error(f"Failed to get contacts: {e}")
            return []

    def update_contact(self, contact: Contact) -> bool:
        """
        Update an existing contact.

        Args:
            contact: Contact to update

        Returns:
            True if successful
        """
        if not self._contacts_sheet:
            return False

        try:
            # Find by ID
            cell = self._contacts_sheet.find(contact.id, in_column=1)
            if cell:
                # Update row
                self._contacts_sheet.update(f"A{cell.row}:Q{cell.row}", [contact.to_row()])
                logger.info(f"Updated contact: {contact.company_name}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to update contact: {e}")
            return False

    def update_contact_status(self, contact_id: str, status: ContactStatus) -> bool:
        """
        Update contact status.

        Args:
            contact_id: Contact ID
            status: New status

        Returns:
            True if successful
        """
        if not self._contacts_sheet:
            return False

        try:
            cell = self._contacts_sheet.find(contact_id, in_column=1)
            if cell:
                # Status is column L (12)
                self._contacts_sheet.update_cell(cell.row, 12, status.value)
                logger.info(f"Updated contact {contact_id} status to {status.value}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to update status: {e}")
            return False

    def find_duplicate(self, contact: Contact) -> Optional[Contact]:
        """
        Check for duplicate contact.

        Args:
            contact: Contact to check

        Returns:
            Existing contact if duplicate found, None otherwise
        """
        contacts = self.get_all_contacts()

        for existing in contacts:
            # Match on company name
            if contact.company_name and existing.company_name:
                if contact.company_name.lower() == existing.company_name.lower():
                    return existing

            # Match on email
            if contact.email and existing.email:
                if contact.email.lower() == existing.email.lower():
                    return existing

            # Match on phone (normalized)
            if contact.phone and existing.phone:
                def normalize_phone(p: str) -> str:
                    return ''.join(c for c in p if c.isdigit())
                if normalize_phone(contact.phone) == normalize_phone(existing.phone):
                    return existing

        return None

    def get_contacts_by_status(self, status: ContactStatus) -> List[Contact]:
        """
        Get contacts by status.

        Args:
            status: Status to filter by

        Returns:
            List of contacts with the given status
        """
        contacts = self.get_all_contacts()
        return [c for c in contacts if c.status == status]

    def get_contacts_by_qualification(self, qualification: str) -> List[Contact]:
        """
        Get contacts by qualification class.

        Args:
            qualification: Qualification class (A, B, C)

        Returns:
            List of contacts with the given qualification
        """
        contacts = self.get_all_contacts()
        return [c for c in contacts if c.qualification.upper() == qualification.upper()]

    # Follow-up Operations

    def add_followup(self, followup: FollowUp) -> bool:
        """
        Add a follow-up to the sheet.

        Args:
            followup: Follow-up to add

        Returns:
            True if successful
        """
        if not self._followups_sheet:
            return False

        try:
            self._followups_sheet.append_row(followup.to_row())
            logger.info(f"Added follow-up for contact {followup.contact_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to add follow-up: {e}")
            return False

    def get_followups_by_contact(self, contact_id: str) -> List[FollowUp]:
        """
        Get follow-ups for a contact.

        Args:
            contact_id: Contact ID

        Returns:
            List of follow-ups
        """
        if not self._followups_sheet:
            return []

        try:
            records = self._followups_sheet.get_all_records()
            followups = []
            for record in records:
                if record.get('Kontakt_ID') == contact_id:
                    row = [
                        record.get('ID', ''),
                        record.get('Kontakt_ID', ''),
                        str(record.get('Typ', '1')),
                        record.get('Geplant_am', ''),
                        record.get('Status', ''),
                        record.get('Erledigt_am', ''),
                        record.get('Notizen', '')
                    ]
                    followups.append(FollowUp.from_row(row))
            return followups
        except Exception as e:
            logger.error(f"Failed to get follow-ups: {e}")
            return []

    def get_open_followups(self) -> List[FollowUp]:
        """
        Get all open follow-ups.

        Returns:
            List of open follow-ups
        """
        if not self._followups_sheet:
            return []

        try:
            records = self._followups_sheet.get_all_records()
            followups = []
            for record in records:
                if record.get('Status') == 'Offen':
                    row = [
                        record.get('ID', ''),
                        record.get('Kontakt_ID', ''),
                        str(record.get('Typ', '1')),
                        record.get('Geplant_am', ''),
                        record.get('Status', ''),
                        record.get('Erledigt_am', ''),
                        record.get('Notizen', '')
                    ]
                    followups.append(FollowUp.from_row(row))
            return followups
        except Exception as e:
            logger.error(f"Failed to get open follow-ups: {e}")
            return []

    def mark_followup_completed(self, followup_id: str) -> bool:
        """
        Mark a follow-up as completed.

        Args:
            followup_id: Follow-up ID

        Returns:
            True if successful
        """
        if not self._followups_sheet:
            return False

        try:
            cell = self._followups_sheet.find(followup_id, in_column=1)
            if cell:
                # Status is column E (5)
                self._followups_sheet.update_cell(cell.row, 5, "Erledigt")
                # Completed_at is column F (6)
                from datetime import datetime
                self._followups_sheet.update_cell(cell.row, 6, datetime.now().strftime('%Y-%m-%d %H:%M'))
                logger.info(f"Marked follow-up {followup_id} as completed")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to mark follow-up completed: {e}")
            return False

    def get_sheet_url(self) -> Optional[str]:
        """
        Get URL to the Google Sheet.

        Returns:
            URL or None if not connected
        """
        if self._spreadsheet:
            return f"https://docs.google.com/spreadsheets/d/{self.config.spreadsheet_id}"
        return None

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()