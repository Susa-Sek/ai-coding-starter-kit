"""
Search State Manager for tracking scraping progress and enabling resume functionality.
"""

import json
import uuid
from datetime import datetime
from typing import Optional, Set, Dict, Any, List
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum

from loguru import logger


class SearchStatus(Enum):
    """Status of a search session."""
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SearchState:
    """
    Tracks the state of a scraping session for resume functionality.

    Attributes:
        session_id: Unique identifier for this search session
        source: Data source (gelbe_seiten, google_maps, etc.)
        location: Search location
        query: Search query
        processed_companies: Set of company names already processed
        last_page: Last page number scraped
        last_offset: Last offset in results
        total_results: Total results found
        processed_count: Number of results processed
        started_at: When the search started
        updated_at: When the state was last updated
        status: Current status
        error: Last error message if any
    """
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    source: str = ""
    location: str = ""
    query: str = ""
    processed_companies: Set[str] = field(default_factory=set)
    last_page: int = 0
    last_offset: int = 0
    total_results: int = 0
    processed_count: int = 0
    started_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    status: str = SearchStatus.RUNNING.value
    error: Optional[str] = None

    def __post_init__(self):
        """Convert set to list for JSON serialization."""
        if isinstance(self.processed_companies, set):
            self._processed_list = list(self.processed_companies)
        else:
            self._processed_list = list(self.processed_companies) if self.processed_companies else []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'session_id': self.session_id,
            'source': self.source,
            'location': self.location,
            'query': self.query,
            'processed_companies': list(self.processed_companies),
            'last_page': self.last_page,
            'last_offset': self.last_offset,
            'total_results': self.total_results,
            'processed_count': self.processed_count,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'status': self.status,
            'error': self.error,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchState':
        """Create from dictionary."""
        return cls(
            session_id=data.get('session_id', str(uuid.uuid4())[:8]),
            source=data.get('source', ''),
            location=data.get('location', ''),
            query=data.get('query', ''),
            processed_companies=set(data.get('processed_companies', [])),
            last_page=data.get('last_page', 0),
            last_offset=data.get('last_offset', 0),
            total_results=data.get('total_results', 0),
            processed_count=data.get('processed_count', 0),
            started_at=datetime.fromisoformat(data['started_at']) if data.get('started_at') else datetime.now(),
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else datetime.now(),
            status=data.get('status', SearchStatus.RUNNING.value),
            error=data.get('error'),
        )


class SearchStateManager:
    """
    Manages search state persistence.

    Provides functionality to:
    - Save/Load search state to JSON file
    - Track processed companies
    - Resume interrupted searches
    """

    def __init__(self, state_dir: str = "data"):
        """
        Initialize state manager.

        Args:
            state_dir: Directory to store state files
        """
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.state_dir / "search_state.json"
        self._current_state: Optional[SearchState] = None

    def create_session(
        self,
        source: str,
        location: str = "Heilbronn",
        query: str = "Hausverwaltung"
    ) -> SearchState:
        """
        Create a new search session.

        Args:
            source: Data source name
            location: Search location
            query: Search query

        Returns:
            New SearchState instance
        """
        self._current_state = SearchState(
            source=source,
            location=location,
            query=query,
            started_at=datetime.now(),
            updated_at=datetime.now(),
            status=SearchStatus.RUNNING.value
        )
        self.save()
        logger.info(f"Created search session {self._current_state.session_id} for {source}")
        return self._current_state

    def load_or_create(
        self,
        source: str,
        location: str = "Heilbronn",
        query: str = "Hausverwaltung",
        resume: bool = False
    ) -> SearchState:
        """
        Load existing session or create new one.

        Args:
            source: Data source name
            location: Search location
            query: Search query
            resume: Whether to resume existing session

        Returns:
            SearchState instance
        """
        if resume and self.state_file.exists():
            try:
                state = self.load()
                if state and state.source == source and state.status == SearchStatus.PAUSED.value:
                    logger.info(f"Resuming session {state.session_id}")
                    self._current_state = state
                    self._current_state.status = SearchStatus.RUNNING.value
                    return self._current_state
            except Exception as e:
                logger.warning(f"Could not load state: {e}")

        return self.create_session(source, location, query)

    def load(self) -> Optional[SearchState]:
        """
        Load state from file.

        Returns:
            SearchState or None if not found
        """
        if not self.state_file.exists():
            return None

        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return SearchState.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            return None

    def save(self) -> bool:
        """
        Save current state to file.

        Returns:
            True if successful
        """
        if not self._current_state:
            return False

        try:
            self._current_state.updated_at = datetime.now()
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self._current_state.to_dict(), f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
            return False

    def add_processed(self, company_name: str) -> None:
        """
        Add a company to processed set.

        Args:
            company_name: Name of processed company
        """
        if self._current_state:
            self._current_state.processed_companies.add(company_name.lower().strip())
            self._current_state.processed_count += 1

    def is_processed(self, company_name: str) -> bool:
        """
        Check if company was already processed.

        Args:
            company_name: Company name to check

        Returns:
            True if already processed
        """
        if self._current_state:
            return company_name.lower().strip() in self._current_state.processed_companies
        return False

    def get_processed_companies(self) -> Set[str]:
        """
        Get set of processed company names.

        Returns:
            Set of processed company names (lowercase)
        """
        if self._current_state:
            return self._current_state.processed_companies
        return set()

    def update_progress(self, page: int = None, offset: int = None, total: int = None) -> None:
        """
        Update scraping progress.

        Args:
            page: Current page number
            offset: Current offset
            total: Total results found
        """
        if self._current_state:
            if page is not None:
                self._current_state.last_page = page
            if offset is not None:
                self._current_state.last_offset = offset
            if total is not None:
                self._current_state.total_results = total
            self.save()

    def pause(self) -> None:
        """Pause the current session."""
        if self._current_state:
            self._current_state.status = SearchStatus.PAUSED.value
            self.save()
            logger.info(f"Paused session {self._current_state.session_id}")

    def complete(self) -> None:
        """Mark session as completed."""
        if self._current_state:
            self._current_state.status = SearchStatus.COMPLETED.value
            self.save()
            logger.info(f"Completed session {self._current_state.session_id}")

    def fail(self, error: str) -> None:
        """Mark session as failed."""
        if self._current_state:
            self._current_state.status = SearchStatus.FAILED.value
            self._current_state.error = error
            self.save()
            logger.error(f"Session {self._current_state.session_id} failed: {error}")

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of current session.

        Returns:
            Dictionary with session summary
        """
        if not self._current_state:
            return {}

        return {
            'session_id': self._current_state.session_id,
            'source': self._current_state.source,
            'location': self._current_state.location,
            'query': self._current_state.query,
            'status': self._current_state.status,
            'processed': self._current_state.processed_count,
            'total': self._current_state.total_results,
            'started': self._current_state.started_at.isoformat() if self._current_state.started_at else None,
            'updated': self._current_state.updated_at.isoformat() if self._current_state.updated_at else None,
        }

    def clear(self) -> None:
        """Clear current session state."""
        self._current_state = None
        if self.state_file.exists():
            self.state_file.unlink()
            logger.info("Cleared search state")