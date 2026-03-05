"""
Duplicate Store using SQLite for fast duplicate detection.

Provides persistent storage for company data to avoid re-processing
duplicates without hitting Google Sheets API.
"""

import sqlite3
import hashlib
from datetime import datetime
from typing import Optional, List, Set
from dataclasses import dataclass
from pathlib import Path

from loguru import logger


@dataclass
class CompanyRecord:
    """Record of a company in the duplicate store."""
    company_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    source: Optional[str] = None
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None

    def to_dict(self):
        return {
            'company_name': self.company_name,
            'email': self.email,
            'phone': self.phone,
            'source': self.source,
            'first_seen': self.first_seen.isoformat() if self.first_seen else None,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
        }


class DuplicateStore:
    """
    SQLite-based duplicate detection for companies.

    Features:
    - Fast lookup by company name, email, or phone
    - Persistent storage across sessions
    - No API calls needed for duplicate checks
    """

    def __init__(self, db_path: str = "data/akquise.db"):
        """
        Initialize duplicate store.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = None
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        conn = self._get_connection()

        conn.execute('''
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL,
                company_name_normalized TEXT NOT NULL,
                email TEXT,
                email_normalized TEXT,
                phone TEXT,
                phone_normalized TEXT,
                source TEXT,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(company_name_normalized)
            )
        ''')

        # Create indexes for fast lookups
        conn.execute('CREATE INDEX IF NOT EXISTS idx_company_name ON companies(company_name_normalized)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_email ON companies(email_normalized)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_phone ON companies(phone_normalized)')

        conn.commit()
        logger.info(f"Initialized duplicate store at {self.db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _normalize_name(self, name: str) -> str:
        """Normalize company name for comparison."""
        if not name:
            return ""
        # Lowercase, remove common suffixes, extra spaces
        name = name.lower().strip()
        for suffix in ['gmbh', 'gmbh & co. kg', 'gmbh & co kg', 'ag', 'kg', 'ug', 'ug (haftungsbeschränkt)']:
            name = name.replace(suffix, '')
        # Remove special chars and extra spaces
        name = ''.join(c for c in name if c.isalnum() or c.isspace())
        return ' '.join(name.split())

    def _normalize_email(self, email: str) -> str:
        """Normalize email for comparison."""
        if not email:
            return ""
        return email.lower().strip()

    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone for comparison (digits only)."""
        if not phone:
            return ""
        return ''.join(c for c in str(phone) if c.isdigit())

    def add_company(
        self,
        company_name: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        source: Optional[str] = None
    ) -> bool:
        """
        Add a company to the store.

        Args:
            company_name: Company name
            email: Email address
            phone: Phone number
            source: Data source

        Returns:
            True if added, False if duplicate
        """
        conn = self._get_connection()

        company_name_normalized = self._normalize_name(company_name)
        if not company_name_normalized:
            return False

        email_normalized = self._normalize_email(email) if email else None
        phone_normalized = self._normalize_phone(phone) if phone else None

        try:
            conn.execute('''
                INSERT INTO companies (
                    company_name, company_name_normalized,
                    email, email_normalized,
                    phone, phone_normalized,
                    source, first_seen, last_seen
                ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (
                company_name, company_name_normalized,
                email, email_normalized,
                phone, phone_normalized,
                source
            ))
            conn.commit()
            return True

        except sqlite3.IntegrityError:
            # Duplicate by company name
            # Update last_seen
            conn.execute('''
                UPDATE companies
                SET last_seen = CURRENT_TIMESTAMP,
                    email = COALESCE(?, email),
                    phone = COALESCE(?, phone),
                    source = COALESCE(?, source)
                WHERE company_name_normalized = ?
            ''', (email, phone, source, company_name_normalized))
            conn.commit()
            return False

    def is_duplicate(
        self,
        company_name: str,
        email: Optional[str] = None,
        phone: Optional[str] = None
    ) -> bool:
        """
        Check if a company is a duplicate.

        Args:
            company_name: Company name to check
            email: Email to check
            phone: Phone to check

        Returns:
            True if duplicate found
        """
        conn = self._get_connection()

        # Check by normalized company name
        company_name_normalized = self._normalize_name(company_name)
        if company_name_normalized:
            cursor = conn.execute(
                'SELECT id FROM companies WHERE company_name_normalized = ?',
                (company_name_normalized,)
            )
            if cursor.fetchone():
                return True

        # Check by normalized email
        if email:
            email_normalized = self._normalize_email(email)
            if email_normalized:
                cursor = conn.execute(
                    'SELECT id FROM companies WHERE email_normalized = ?',
                    (email_normalized,)
                )
                if cursor.fetchone():
                    return True

        # Check by normalized phone
        if phone:
            phone_normalized = self._normalize_phone(phone)
            if phone_normalized and len(phone_normalized) >= 6:  # Min 6 digits for meaningful match
                cursor = conn.execute(
                    'SELECT id FROM companies WHERE phone_normalized = ?',
                    (phone_normalized,)
                )
                if cursor.fetchone():
                    return True

        return False

    def get_all_companies(self) -> Set[str]:
        """
        Get all company names in the store.

        Returns:
            Set of company names (lowercase)
        """
        conn = self._get_connection()
        cursor = conn.execute('SELECT company_name_normalized FROM companies')
        return {row[0] for row in cursor.fetchall()}

    def get_company(self, company_name: str) -> Optional[CompanyRecord]:
        """
        Get a company record by name.

        Args:
            company_name: Company name

        Returns:
            CompanyRecord or None
        """
        conn = self._get_connection()
        company_name_normalized = self._normalize_name(company_name)

        cursor = conn.execute(
            '''SELECT company_name, email, phone, source, first_seen, last_seen
               FROM companies WHERE company_name_normalized = ?''',
            (company_name_normalized,)
        )
        row = cursor.fetchone()

        if row:
            return CompanyRecord(
                company_name=row[0],
                email=row[1],
                phone=row[2],
                source=row[3],
                first_seen=datetime.fromisoformat(row[4]) if row[4] else None,
                last_seen=datetime.fromisoformat(row[5]) if row[5] else None,
            )
        return None

    def count(self) -> int:
        """Get total number of companies in store."""
        conn = self._get_connection()
        cursor = conn.execute('SELECT COUNT(*) FROM companies')
        return cursor.fetchone()[0]

    def clear(self) -> None:
        """Clear all companies from the store."""
        conn = self._get_connection()
        conn.execute('DELETE FROM companies')
        conn.commit()
        logger.info("Cleared duplicate store")

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()