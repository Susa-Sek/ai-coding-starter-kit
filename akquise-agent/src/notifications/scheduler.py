"""
Notification scheduler for automated reminders and reports.
"""

from typing import Optional, Callable, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import asyncio

from loguru import logger

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    logger.warning("APScheduler not installed - scheduling features disabled")


@dataclass
class ScheduleConfig:
    """Configuration for notification scheduling."""
    daily_summary_time: str = "09:00"  # HH:MM format
    weekly_report_day: int = 0  # Monday = 0
    weekly_report_time: str = "08:00"
    followup_check_interval: int = 60  # minutes
    scraper_check_interval: int = 30  # minutes


@dataclass
class FollowUpTask:
    """A scheduled follow-up task."""
    contact_id: str
    company_name: str
    contact_date: datetime
    followup_number: int  # 1 or 2
    scheduled_date: datetime
    status: str = "pending"
    completed: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class NotificationScheduler:
    """
    Scheduler for automated notifications.

    Features:
    - Daily summary at configured time
    - Weekly report on configured day
    - Follow-up reminders (7 and 14 days after contact)
    - Scraper health checks
    """

    def __init__(self, config: Optional[ScheduleConfig] = None):
        """
        Initialize notification scheduler.

        Args:
            config: Schedule configuration
        """
        self.config = config or ScheduleConfig()
        self._scheduler: Optional[Any] = None
        self._followup_queue: List[FollowUpTask] = []
        self._running = False

        # Callbacks
        self._on_daily_summary: Optional[Callable] = None
        self._on_weekly_report: Optional[Callable] = None
        self._on_followup: Optional[Callable] = None
        self._on_scraper_check: Optional[Callable] = None

    @property
    def is_available(self) -> bool:
        """Check if scheduler is available."""
        return APSCHEDULER_AVAILABLE

    def set_callbacks(
        self,
        on_daily_summary: Optional[Callable] = None,
        on_weekly_report: Optional[Callable] = None,
        on_followup: Optional[Callable] = None,
        on_scraper_check: Optional[Callable] = None
    ) -> None:
        """
        Set callback functions for scheduled events.

        Args:
            on_daily_summary: Callback for daily summary
            on_weekly_report: Callback for weekly report
            on_followup: Callback for follow-up reminder
            on_scraper_check: Callback for scraper health check
        """
        self._on_daily_summary = on_daily_summary
        self._on_weekly_report = on_weekly_report
        self._on_followup = on_followup
        self._on_scraper_check = on_scraper_check

    def start(self) -> bool:
        """
        Start the scheduler.

        Returns:
            True if scheduler started successfully
        """
        if not self.is_available:
            logger.warning("Scheduler not available - APScheduler not installed")
            return False

        if self._running:
            logger.warning("Scheduler already running")
            return True

        try:
            self._scheduler = AsyncIOScheduler()

            # Daily summary job
            hour, minute = map(int, self.config.daily_summary_time.split(':'))
            self._scheduler.add_job(
                self._run_daily_summary,
                CronTrigger(hour=hour, minute=minute),
                id='daily_summary',
                name='Daily Summary'
            )

            # Weekly report job
            hour, minute = map(int, self.config.weekly_report_time.split(':'))
            self._scheduler.add_job(
                self._run_weekly_report,
                CronTrigger(
                    day_of_week=self.config.weekly_report_day,
                    hour=hour,
                    minute=minute
                ),
                id='weekly_report',
                name='Weekly Report'
            )

            # Follow-up check job
            self._scheduler.add_job(
                self._run_followup_check,
                IntervalTrigger(minutes=self.config.followup_check_interval),
                id='followup_check',
                name='Follow-up Check'
            )

            # Scraper health check job
            self._scheduler.add_job(
                self._run_scraper_check,
                IntervalTrigger(minutes=self.config.scraper_check_interval),
                id='scraper_check',
                name='Scraper Health Check'
            )

            self._scheduler.start()
            self._running = True
            logger.info("Notification scheduler started")
            return True

        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            return False

    def stop(self) -> None:
        """Stop the scheduler."""
        if self._scheduler and self._running:
            self._scheduler.shutdown()
            self._running = False
            logger.info("Notification scheduler stopped")

    def add_followup(
        self,
        contact_id: str,
        company_name: str,
        contact_date: datetime,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[FollowUpTask]:
        """
        Schedule follow-ups for a new contact.

        Args:
            contact_id: Contact identifier
            company_name: Company name
            contact_date: Date of initial contact
            metadata: Additional metadata

        Returns:
            List of scheduled follow-up tasks
        """
        tasks = []

        # First follow-up: 7 days
        followup_1_date = contact_date + timedelta(days=7)
        task_1 = FollowUpTask(
            contact_id=contact_id,
            company_name=company_name,
            contact_date=contact_date,
            followup_number=1,
            scheduled_date=followup_1_date,
            metadata=metadata or {}
        )
        tasks.append(task_1)

        # Second follow-up: 14 days
        followup_2_date = contact_date + timedelta(days=14)
        task_2 = FollowUpTask(
            contact_id=contact_id,
            company_name=company_name,
            contact_date=contact_date,
            followup_number=2,
            scheduled_date=followup_2_date,
            metadata=metadata or {}
        )
        tasks.append(task_2)

        self._followup_queue.extend(tasks)
        logger.info(
            f"Scheduled {len(tasks)} follow-ups for {company_name} "
            f"(days 7 and 14)"
        )

        return tasks

    def get_pending_followups(self) -> List[FollowUpTask]:
        """
        Get all pending follow-ups that are due.

        Returns:
            List of due follow-up tasks
        """
        now = datetime.now()
        pending = []

        for task in self._followup_queue:
            if not task.completed and task.scheduled_date <= now:
                pending.append(task)

        return pending

    def mark_followup_completed(self, contact_id: str, followup_number: int) -> bool:
        """
        Mark a follow-up as completed.

        Args:
            contact_id: Contact identifier
            followup_number: Follow-up number (1 or 2)

        Returns:
            True if task was found and marked
        """
        for task in self._followup_queue:
            if (task.contact_id == contact_id and
                task.followup_number == followup_number):
                task.completed = True
                task.status = "completed"
                logger.info(f"Follow-up #{followup_number} completed for {task.company_name}")
                return True
        return False

    async def _run_daily_summary(self) -> None:
        """Run daily summary callback."""
        if self._on_daily_summary:
            try:
                await self._on_daily_summary()
            except Exception as e:
                logger.error(f"Daily summary callback error: {e}")

    async def _run_weekly_report(self) -> None:
        """Run weekly report callback."""
        if self._on_weekly_report:
            try:
                await self._on_weekly_report()
            except Exception as e:
                logger.error(f"Weekly report callback error: {e}")

    async def _run_followup_check(self) -> None:
        """Check for due follow-ups."""
        pending = self.get_pending_followups()

        if pending and self._on_followup:
            for task in pending:
                try:
                    await self._on_followup(task)
                    task.status = "sent"
                except Exception as e:
                    logger.error(f"Follow-up callback error for {task.company_name}: {e}")

    async def _run_scraper_check(self) -> None:
        """Run scraper health check."""
        if self._on_scraper_check:
            try:
                await self._on_scraper_check()
            except Exception as e:
                logger.error(f"Scraper check callback error: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get scheduler statistics.

        Returns:
            Dictionary with scheduler stats
        """
        return {
            'running': self._running,
            'available': self.is_available,
            'total_followups': len(self._followup_queue),
            'pending_followups': len([t for t in self._followup_queue if not t.completed]),
            'completed_followups': len([t for t in self._followup_queue if t.completed]),
            'config': {
                'daily_summary_time': self.config.daily_summary_time,
                'weekly_report_day': self.config.weekly_report_day,
                'weekly_report_time': self.config.weekly_report_time,
                'followup_check_interval': self.config.followup_check_interval,
                'scraper_check_interval': self.config.scraper_check_interval
            }
        }

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()