"""
CSV export functionality for contacts and follow-ups.
"""

import csv
from typing import List, Optional
from datetime import datetime
from pathlib import Path

from loguru import logger

from src.storage.models import Contact, FollowUp


class CSVExporter:
    """
    Export contacts and follow-ups to CSV files.
    """

    # CSV headers for contacts
    CONTACT_HEADERS = [
        'ID', 'Firma', 'Adresse', 'Telefon', 'E-Mail', 'Website',
        'Einheiten', 'Mitarbeiter', 'Quelle', 'Qualifikation', 'Score',
        'Status', 'E-Mail_Entwurf', 'Erstellt_am', 'Follow_Up_1',
        'Follow_Up_2', 'Notizen'
    ]

    # CSV headers for follow-ups
    FOLLOWUP_HEADERS = [
        'ID', 'Kontakt_ID', 'Typ', 'Geplant_am', 'Status', 'Erledigt_am', 'Notizen'
    ]

    def export_contacts(
        self,
        contacts: List[Contact],
        output_path: str,
        include_email_draft: bool = False
    ) -> int:
        """
        Export contacts to CSV file.

        Args:
            contacts: List of contacts to export
            output_path: Path to output CSV file
            include_email_draft: Whether to include email draft text

        Returns:
            Number of contacts exported
        """
        if not contacts:
            logger.warning("No contacts to export")
            return 0

        try:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # Write header
                if include_email_draft:
                    writer.writerow(self.CONTACT_HEADERS)
                else:
                    # Skip email draft column
                    headers = [h for h in self.CONTACT_HEADERS if h != 'E-Mail_Entwurf']
                    writer.writerow(headers)

                # Write contacts
                for contact in contacts:
                    row = contact.to_row()
                    if not include_email_draft:
                        # Remove email draft (index 12)
                        row = row[:12] + row[13:]
                    writer.writerow(row)

            logger.info(f"Exported {len(contacts)} contacts to {output_path}")
            return len(contacts)

        except Exception as e:
            logger.error(f"Failed to export contacts: {e}")
            return 0

    def export_followups(
        self,
        followups: List[FollowUp],
        output_path: str
    ) -> int:
        """
        Export follow-ups to CSV file.

        Args:
            followups: List of follow-ups to export
            output_path: Path to output CSV file

        Returns:
            Number of follow-ups exported
        """
        if not followups:
            logger.warning("No follow-ups to export")
            return 0

        try:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # Write header
                writer.writerow(self.FOLLOWUP_HEADERS)

                # Write follow-ups
                for followup in followups:
                    writer.writerow(followup.to_row())

            logger.info(f"Exported {len(followups)} follow-ups to {output_path}")
            return len(followups)

        except Exception as e:
            logger.error(f"Failed to export follow-ups: {e}")
            return 0

    def export_summary(
        self,
        contacts: List[Contact],
        output_path: str
    ) -> int:
        """
        Export contacts summary to CSV file (for A-class leads).

        Args:
            contacts: List of contacts to export
            output_path: Path to output CSV file

        Returns:
            Number of contacts exported
        """
        if not contacts:
            logger.warning("No contacts to export")
            return 0

        summary_headers = [
            'Firma', 'Adresse', 'Telefon', 'E-Mail', 'Einheiten',
            'Qualifikation', 'Score', 'Status', 'Erstellt_am'
        ]

        try:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # Write header
                writer.writerow(summary_headers)

                # Write contacts
                for contact in contacts:
                    row = [
                        contact.company_name,
                        contact.address or "",
                        contact.phone or "",
                        contact.email or "",
                        str(contact.units) if contact.units else "",
                        contact.qualification,
                        str(contact.score),
                        contact.status.value,
                        contact.created_at.strftime('%Y-%m-%d') if contact.created_at else ""
                    ]
                    writer.writerow(row)

            logger.info(f"Exported {len(contacts)} contacts summary to {output_path}")
            return len(contacts)

        except Exception as e:
            logger.error(f"Failed to export summary: {e}")
            return 0

    def export_for_mail_merge(
        self,
        contacts: List[Contact],
        output_path: str
    ) -> int:
        """
        Export contacts in format suitable for mail merge.

        Args:
            contacts: List of contacts to export
            output_path: Path to output CSV file

        Returns:
            Number of contacts exported
        """
        if not contacts:
            logger.warning("No contacts to export")
            return 0

        # Mail merge format
        mail_headers = [
            'Anrede', 'Firma', 'Strasse', 'PLZ', 'Ort',
            'Telefon', 'E-Mail', 'Anrede_Brief'
        ]

        try:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # Write header
                writer.writerow(mail_headers)

                # Write contacts
                for contact in contacts:
                    # Parse address
                    street, plz, ort = self._parse_address(contact.address or "")

                    row = [
                        "Sehr geehrte Damen und Herren",  # Anrede
                        contact.company_name,
                        street,
                        plz,
                        ort,
                        contact.phone or "",
                        contact.email or "",
                        "Sehr geehrte Damen und Herren,"  # Anrede_Brief
                    ]
                    writer.writerow(row)

            logger.info(f"Exported {len(contacts)} contacts for mail merge to {output_path}")
            return len(contacts)

        except Exception as e:
            logger.error(f"Failed to export for mail merge: {e}")
            return 0

    def _parse_address(self, address: str) -> tuple:
        """Parse German address into components."""
        import re

        # Pattern: "Street 123, 12345 City"
        match = re.search(r'^(.*?),?\s*(\d{5})\s+(.+)$', address)
        if match:
            street = match.group(1).strip().rstrip(',')
            plz = match.group(2)
            ort = match.group(3).strip()
            return street, plz, ort

        # Try to extract PLZ and city
        match = re.search(r'(\d{5})\s+([A-Za-zäöüÄÖÜß]+)', address)
        if match:
            plz = match.group(1)
            ort = match.group(2)
            street = address[:match.start()].strip().rstrip(',')
            return street, plz, ort

        # No match
        return address, "", ""