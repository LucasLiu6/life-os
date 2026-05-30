import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.services.evening_checkin import generate_evening_checkin
from app.services.morning_briefing import generate_morning_briefing
from app.services.weekly_review import generate_weekly_review
from app.telegram.client import send_telegram_message


logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> BackgroundScheduler | None:
    global _scheduler

    if not settings.scheduler_enabled:
        logger.info("Scheduler is disabled.")
        return None

    if _scheduler is not None:
        logger.info("Scheduler is already running.")
        return _scheduler

    scheduler = BackgroundScheduler(timezone=settings.timezone)
    _register_jobs(scheduler)
    scheduler.start()
    _scheduler = scheduler
    logger.info("Scheduler started.")
    return scheduler


def shutdown_scheduler() -> None:
    global _scheduler

    if _scheduler is None:
        return

    _scheduler.shutdown(wait=False)
    _scheduler = None
    logger.info("Scheduler shut down.")


def run_morning_briefing_job() -> None:
    try:
        briefing = generate_morning_briefing()
        send_telegram_message(f"🌅 Morning Briefing\n\n{briefing}")
    except Exception as error:
        logger.exception("Morning briefing scheduled job failed: %s", error)


def run_evening_checkin_job() -> None:
    try:
        message = generate_evening_checkin()
        send_telegram_message(f"🌙 Evening Check-in\n\n{message}")
    except Exception as error:
        logger.exception("Evening check-in scheduled job failed: %s", error)


def run_weekly_review_job() -> None:
    try:
        review = generate_weekly_review(None, None)
        send_telegram_message(f"📊 Weekly Review\n\n{review}")
    except Exception as error:
        logger.exception("Weekly review scheduled job failed: %s", error)


def _register_jobs(scheduler: BackgroundScheduler) -> None:
    scheduler.add_job(
        run_morning_briefing_job,
        "cron",
        id="morning_briefing",
        hour=settings.morning_briefing_hour,
        minute=settings.morning_briefing_minute,
        replace_existing=True,
    )
    scheduler.add_job(
        run_evening_checkin_job,
        "cron",
        id="evening_checkin",
        hour=settings.evening_checkin_hour,
        minute=settings.evening_checkin_minute,
        replace_existing=True,
    )
    scheduler.add_job(
        run_weekly_review_job,
        "cron",
        id="weekly_review",
        day_of_week=settings.weekly_review_day_of_week,
        hour=settings.weekly_review_hour,
        minute=settings.weekly_review_minute,
        replace_existing=True,
    )
