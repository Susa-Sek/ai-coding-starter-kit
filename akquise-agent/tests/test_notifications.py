"""
Tests for notification module.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.notifications.telegram import TelegramNotifier, TelegramConfig
from src.notifications.messages import MessageTemplates
from src.notifications.scheduler import NotificationScheduler, ScheduleConfig, FollowUpTask


class TestTelegramNotifier:
    """Tests for TelegramNotifier."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return TelegramConfig(
            bot_token="test_token",
            user_id="test_user_id"
        )

    @pytest.fixture
    def notifier(self, config):
        """Create notifier instance."""
        return TelegramNotifier(config)

    def test_is_configured(self, notifier):
        """Test configuration check."""
        assert notifier.is_configured is True

    def test_not_configured(self):
        """Test without configuration."""
        notifier = TelegramNotifier(TelegramConfig(bot_token="", user_id=""))
        assert notifier.is_configured is False

    def test_api_url(self, notifier):
        """Test API URL generation."""
        url = notifier._get_api_url("sendMessage")
        assert "test_token" in url
        assert "sendMessage" in url

    @pytest.mark.asyncio
    async def test_send_message_not_configured(self):
        """Test send without configuration."""
        notifier = TelegramNotifier(TelegramConfig(bot_token="", user_id=""))
        result = await notifier.send_message("Test")
        assert result is False

    @pytest.mark.asyncio
    async def test_send_lead_notification(self, notifier):
        """Test lead notification generation."""
        with patch.object(notifier, 'send_message', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True

            result = await notifier.send_lead_notification(
                company_name="Test GmbH",
                address="Hauptstraße 1, 74072 Heilbronn",
                phone="+49713112345",
                email="info@test.de",
                units=100,
                score=85,
                grade="A"
            )

            assert result is True
            mock_send.assert_called_once()
            call_args = mock_send.call_args[0][0]
            assert "Test GmbH" in call_args
            assert "A" in call_args
            assert "85/100" in call_args

    @pytest.mark.asyncio
    async def test_send_daily_summary(self, notifier):
        """Test daily summary generation."""
        with patch.object(notifier, 'send_message', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True

            result = await notifier.send_daily_summary(
                total_new=10,
                a_class=3,
                b_class=4,
                c_class=3,
                followups_due=5
            )

            assert result is True
            mock_send.assert_called_once()
            call_args = mock_send.call_args[0][0]
            assert "TÄGLICHE ZUSAMMENFASSUNG" in call_args
            assert "10" in call_args

    @pytest.mark.asyncio
    async def test_send_followup_reminder(self, notifier):
        """Test follow-up reminder generation."""
        with patch.object(notifier, 'send_message', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True

            result = await notifier.send_followup_reminder(
                company_name="Test GmbH",
                days_since_contact=7,
                status="contacted"
            )

            assert result is True
            mock_send.assert_called_once()
            call_args = mock_send.call_args[0][0]
            assert "FOLLOW-UP ERINNERUNG" in call_args
            assert "Test GmbH" in call_args

    @pytest.mark.asyncio
    async def test_send_error_notification(self, notifier):
        """Test error notification generation."""
        with patch.object(notifier, 'send_message', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True

            result = await notifier.send_error_notification(
                error_type="Scraper Error",
                error_message="Rate limit exceeded",
                suggested_action="Wait 60 seconds and retry"
            )

            assert result is True
            call_args = mock_send.call_args[0][0]
            assert "FEHLER" in call_args
            assert "Scraper Error" in call_args


class TestMessageTemplates:
    """Tests for MessageTemplates."""

    def test_new_lead_message(self):
        """Test new lead message generation."""
        msg = MessageTemplates.new_lead(
            company_name="Test GmbH",
            address="Heilbronn",
            phone="+49713112345",
            email="info@test.de",
            units=100,
            score=85,
            grade="A"
        )

        assert "NEUER LEAD" in msg
        assert "Test GmbH" in msg
        assert "Heilbronn" in msg
        assert "🟢 A" in msg
        assert "85/100" in msg

    def test_daily_summary_message(self):
        """Test daily summary message generation."""
        msg = MessageTemplates.daily_summary(
            new_leads=10,
            a_class=3,
            b_class=4,
            c_class=3,
            followups_due=5,
            emails_sent=8
        )

        assert "TÄGLICHE ZUSAMMENFASSUNG" in msg
        assert "10" in msg
        assert "A-Klasse: 3" in msg

    def test_followup_reminder_message(self):
        """Test follow-up reminder message generation."""
        msg = MessageTemplates.followup_reminder(
            company_name="Test GmbH",
            days_since_contact=7,
            status="contacted",
            followup_number=1
        )

        assert "FOLLOW-UP ERINNERUNG" in msg
        assert "Test GmbH" in msg
        assert "7" in msg

    def test_weekly_report_message(self):
        """Test weekly report message generation."""
        msg = MessageTemplates.weekly_report(
            week_number=10,
            total_leads=50,
            a_class=15,
            replies=10,
            meetings=3,
            conversion_rate=6.0,
            top_leads=[
                {"company_name": "Top 1", "score": 95},
                {"company_name": "Top 2", "score": 90}
            ]
        )

        assert "WÖCHENTLICHER BERICHT" in msg
        assert "Kalenderwoche 10" in msg
        assert "50" in msg
        assert "Top 1" in msg

    def test_error_alert_message(self):
        """Test error alert message generation."""
        msg = MessageTemplates.error_alert(
            error_type="Scraper Error",
            error_message="Rate limit exceeded"
        )

        assert "FEHLER ALERT" in msg
        assert "Scraper Error" in msg
        assert "Rate limit exceeded" in msg

    def test_scraper_status_message(self):
        """Test scraper status message generation."""
        msg = MessageTemplates.scraper_status(
            source="Gelbe Seiten",
            status="completed",
            leads_found=25,
            errors=0
        )

        assert "SCRAPER STATUS" in msg
        assert "Gelbe Seiten" in msg
        assert "completed" in msg
        assert "25" in msg


class TestNotificationScheduler:
    """Tests for NotificationScheduler."""

    @pytest.fixture
    def scheduler(self):
        """Create scheduler instance."""
        config = ScheduleConfig(
            daily_summary_time="09:00",
            weekly_report_day=0,
            weekly_report_time="08:00"
        )
        return NotificationScheduler(config)

    def test_config(self, scheduler):
        """Test scheduler configuration."""
        assert scheduler.config.daily_summary_time == "09:00"
        assert scheduler.config.weekly_report_day == 0

    def test_add_followup(self, scheduler):
        """Test adding follow-up task."""
        tasks = scheduler.add_followup(
            contact_id="test-1",
            company_name="Test GmbH",
            contact_date=datetime.now()
        )

        assert len(tasks) == 2
        assert tasks[0].followup_number == 1
        assert tasks[1].followup_number == 2

    def test_get_pending_followups(self, scheduler):
        """Test getting pending follow-ups."""
        from datetime import timedelta

        # Add follow-up with past due date
        past_date = datetime.now() - timedelta(days=10)
        scheduler.add_followup(
            contact_id="test-1",
            company_name="Test GmbH",
            contact_date=past_date
        )

        pending = scheduler.get_pending_followups()
        assert len(pending) >= 1

    def test_mark_followup_completed(self, scheduler):
        """Test marking follow-up as completed."""
        scheduler.add_followup(
            contact_id="test-1",
            company_name="Test GmbH",
            contact_date=datetime.now()
        )

        result = scheduler.mark_followup_completed("test-1", 1)
        assert result is True

        # Check that task is completed
        for task in scheduler._followup_queue:
            if task.contact_id == "test-1" and task.followup_number == 1:
                assert task.completed is True

    def test_get_stats(self, scheduler):
        """Test getting scheduler stats."""
        scheduler.add_followup(
            contact_id="test-1",
            company_name="Test GmbH",
            contact_date=datetime.now()
        )

        stats = scheduler.get_stats()
        assert 'total_followups' in stats
        assert stats['total_followups'] == 2  # 2 follow-ups per contact