from unittest.mock import Mock, patch

from app.scheduler import service


def setup_function() -> None:
    service._scheduler = None


def teardown_function() -> None:
    service._scheduler = None


def test_scheduler_does_not_start_when_disabled() -> None:
    settings = Mock(scheduler_enabled=False)

    with (
        patch("app.scheduler.service.settings", settings),
        patch("app.scheduler.service.BackgroundScheduler") as scheduler_class,
    ):
        result = service.start_scheduler()

    assert result is None
    scheduler_class.assert_not_called()


def test_scheduler_starts_and_registers_three_jobs_when_enabled() -> None:
    scheduler = Mock()
    settings = Mock(
        scheduler_enabled=True,
        timezone="America/New_York",
        morning_briefing_hour=8,
        morning_briefing_minute=30,
        evening_checkin_hour=22,
        evening_checkin_minute=30,
        weekly_review_day_of_week="sun",
        weekly_review_hour=20,
        weekly_review_minute=0,
    )

    with (
        patch("app.scheduler.service.settings", settings),
        patch("app.scheduler.service.BackgroundScheduler", return_value=scheduler) as scheduler_class,
    ):
        result = service.start_scheduler()

    assert result == scheduler
    scheduler_class.assert_called_once_with(timezone="America/New_York")
    assert scheduler.add_job.call_count == 3
    scheduler.start.assert_called_once_with()

    job_ids = [call.kwargs["id"] for call in scheduler.add_job.call_args_list]
    assert job_ids == ["morning_briefing", "evening_checkin", "weekly_review"]
    for call in scheduler.add_job.call_args_list:
        assert call.args[1] == "cron"
        assert call.kwargs["replace_existing"] is True


def test_morning_job_sends_titled_telegram_message() -> None:
    with (
        patch("app.scheduler.service.generate_morning_briefing", return_value="Plan today") as generator,
        patch("app.scheduler.service.send_telegram_message") as send,
    ):
        service.run_morning_briefing_job()

    generator.assert_called_once_with()
    send.assert_called_once_with("🌅 Morning Briefing\n\nPlan today")


def test_evening_job_sends_titled_telegram_message() -> None:
    with (
        patch("app.scheduler.service.generate_evening_checkin", return_value="Check in") as generator,
        patch("app.scheduler.service.send_telegram_message") as send,
    ):
        service.run_evening_checkin_job()

    generator.assert_called_once_with()
    send.assert_called_once_with("🌙 Evening Check-in\n\nCheck in")


def test_weekly_job_sends_titled_telegram_message() -> None:
    with (
        patch("app.scheduler.service.generate_weekly_review", return_value="Review week") as generator,
        patch("app.scheduler.service.send_telegram_message") as send,
    ):
        service.run_weekly_review_job()

    generator.assert_called_once_with(None, None)
    send.assert_called_once_with("📊 Weekly Review\n\nReview week")


def test_job_wrapper_logs_errors_without_reraising() -> None:
    with (
        patch("app.scheduler.service.generate_morning_briefing", side_effect=RuntimeError("boom")),
        patch("app.scheduler.service.send_telegram_message") as send,
        patch("app.scheduler.service.logger") as logger,
    ):
        service.run_morning_briefing_job()

    send.assert_not_called()
    logger.exception.assert_called_once()


def test_shutdown_scheduler_noops_when_not_started() -> None:
    service._scheduler = None

    service.shutdown_scheduler()

    assert service._scheduler is None


def test_shutdown_scheduler_stops_running_scheduler() -> None:
    scheduler = Mock()
    service._scheduler = scheduler

    service.shutdown_scheduler()

    scheduler.shutdown.assert_called_once_with(wait=False)
    assert service._scheduler is None
