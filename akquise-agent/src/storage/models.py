"""
Data models for contacts and follow-ups.
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class ContactStatus(Enum):
    """Contact status values."""
    NEW = "Neu"
    CONTACTED = "Kontaktiert"
    REPLIED = "Antwort"
    MEETING = "Termin"
    REJECTED = "Abgelehnt"
    NO_RESPONSE = "Keine_Antwort"

    @classmethod
    def from_string(cls, value: str) -> 'ContactStatus':
        """Convert string to status."""
        mapping = {
            "neu": cls.NEW,
            "kontaktiert": cls.CONTACTED,
            "antwort": cls.REPLIED,
            "termin": cls.MEETING,
            "abgelehnt": cls.REJECTED,
            "keine_antwort": cls.NO_RESPONSE,
            "new": cls.NEW,
            "contacted": cls.CONTACTED,
            "replied": cls.REPLIED,
            "meeting": cls.MEETING,
            "rejected": cls.REJECTED,
            "no_response": cls.NO_RESPONSE,
        }
        return mapping.get(value.lower(), cls.NEW)


@dataclass
class Contact:
    """Contact model for Google Sheets storage."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    company_name: str = ""
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    units: Optional[int] = None
    employees: Optional[int] = None
    source: str = ""
    qualification: str = "C"  # A, B, C
    score: int = 0
    status: ContactStatus = ContactStatus.NEW
    email_draft: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    follow_up_1: Optional[datetime] = None
    follow_up_2: Optional[datetime] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'company_name': self.company_name,
            'address': self.address or "",
            'phone': self.phone or "",
            'email': self.email or "",
            'website': self.website or "",
            'units': self.units or "",
            'employees': self.employees or "",
            'source': self.source,
            'qualification': self.qualification,
            'score': self.score,
            'status': self.status.value,
            'email_draft': self.email_draft or "",
            'created_at': self.created_at.isoformat() if self.created_at else "",
            'follow_up_1': self.follow_up_1.isoformat() if self.follow_up_1 else "",
            'follow_up_2': self.follow_up_2.isoformat() if self.follow_up_2 else "",
            'notes': self.notes or ""
        }

    def to_row(self) -> List[str]:
        """Convert to row for Google Sheets."""
        return [
            self.id,
            self.company_name,
            self.address or "",
            self.phone or "",
            self.email or "",
            self.website or "",
            str(self.units) if self.units else "",
            str(self.employees) if self.employees else "",
            self.source,
            self.qualification,
            str(self.score),
            self.status.value,
            self.email_draft or "",
            self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else "",
            self.follow_up_1.strftime('%Y-%m-%d') if self.follow_up_1 else "",
            self.follow_up_2.strftime('%Y-%m-%d') if self.follow_up_2 else "",
            self.notes or ""
        ]

    @classmethod
    def from_row(cls, row: List[str]) -> 'Contact':
        """Create from Google Sheets row."""
        def parse_int(value: str) -> Optional[int]:
            if not value or not value.strip():
                return None
            try:
                return int(value.strip())
            except ValueError:
                return None

        def parse_datetime(value: str) -> Optional[datetime]:
            if not value or not value.strip():
                return None
            try:
                # Try ISO format first
                return datetime.fromisoformat(value.strip())
            except ValueError:
                try:
                    # Try %Y-%m-%d %H:%M format
                    return datetime.strptime(value.strip(), '%Y-%m-%d %H:%M')
                except ValueError:
                    return None

        def parse_date(value: str) -> Optional[datetime]:
            if not value or not value.strip():
                return None
            try:
                return datetime.strptime(value.strip(), '%Y-%m-%d')
            except ValueError:
                return None

        # Handle different row lengths
        row = row + [''] * 17  # Pad to expected length

        return cls(
            id=row[0] if row[0] else str(uuid.uuid4())[:8],
            company_name=row[1],
            address=row[2] or None,
            phone=row[3] or None,
            email=row[4] or None,
            website=row[5] or None,
            units=parse_int(row[6]),
            employees=parse_int(row[7]),
            source=row[8] or "",
            qualification=row[9] or "C",
            score=parse_int(row[10]) or 0,
            status=ContactStatus.from_string(row[11]) if row[11] else ContactStatus.NEW,
            email_draft=row[12] or None,
            created_at=parse_datetime(row[13]) or datetime.now(),
            follow_up_1=parse_date(row[14]),
            follow_up_2=parse_date(row[15]),
            notes=row[16] or None
        )

    @classmethod
    def from_scraper_result(cls, result: Any, score: int = 0, qualification: str = "C") -> 'Contact':
        """Create from ScraperResult."""
        return cls(
            company_name=result.company_name,
            address=result.address,
            phone=result.phone,
            email=result.email,
            website=result.website,
            units=result.units,
            employees=result.employees,
            source=result.source,
            qualification=qualification,
            score=score,
            created_at=datetime.now()
        )


@dataclass
class FollowUp:
    """Follow-up model for tracking."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    contact_id: str = ""
    followup_type: int = 1  # 1 or 2
    scheduled_date: Optional[datetime] = None
    status: str = "Offen"  # Offen, Erledigt
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'contact_id': self.contact_id,
            'followup_type': self.followup_type,
            'scheduled_date': self.scheduled_date.isoformat() if self.scheduled_date else "",
            'status': self.status,
            'completed_at': self.completed_at.isoformat() if self.completed_at else "",
            'notes': self.notes or ""
        }

    def to_row(self) -> List[str]:
        """Convert to row for Google Sheets."""
        return [
            self.id,
            self.contact_id,
            str(self.followup_type),
            self.scheduled_date.strftime('%Y-%m-%d') if self.scheduled_date else "",
            self.status,
            self.completed_at.strftime('%Y-%m-%d %H:%M') if self.completed_at else "",
            self.notes or ""
        ]

    @classmethod
    def from_row(cls, row: List[str]) -> 'FollowUp':
        """Create from Google Sheets row."""
        def parse_int(value: str) -> Optional[int]:
            if not value or not value.strip():
                return None
            try:
                return int(value.strip())
            except ValueError:
                return None

        def parse_date(value: str) -> Optional[datetime]:
            if not value or not value.strip():
                return None
            try:
                return datetime.strptime(value.strip(), '%Y-%m-%d')
            except ValueError:
                return None

        def parse_datetime(value: str) -> Optional[datetime]:
            if not value or not value.strip():
                return None
            try:
                return datetime.strptime(value.strip(), '%Y-%m-%d %H:%M')
            except ValueError:
                return None

        row = row + [''] * 7  # Pad to expected length

        return cls(
            id=row[0] if row[0] else str(uuid.uuid4())[:8],
            contact_id=row[1],
            followup_type=parse_int(row[2]) or 1,
            scheduled_date=parse_date(row[3]),
            status=row[4] or "Offen",
            completed_at=parse_datetime(row[5]),
            notes=row[6] or None
        )