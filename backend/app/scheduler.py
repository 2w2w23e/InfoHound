from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.app.core.config import get_settings
from backend.app.db import session_scope
from backend.app.services.pipeline import crawl_all_sources


scheduler = BackgroundScheduler()


def scheduled_crawl() -> None:
    with session_scope() as session:
        crawl_all_sources(session)


def start_scheduler() -> None:
    settings = get_settings()
    if scheduler.running:
        return

    scheduler.add_job(
        scheduled_crawl,
        trigger=CronTrigger(
            hour=settings.daily_crawl_hour,
            minute=settings.daily_crawl_minute,
            timezone=settings.scheduler_timezone,
        ),
        id="daily_crawl",
        replace_existing=True,
    )
    scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)

