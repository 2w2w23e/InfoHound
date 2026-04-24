from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.app.api.routes import router
from backend.app.core.config import get_settings
from backend.app.db import init_db, session_scope
from backend.app.scheduler import start_scheduler, stop_scheduler
from backend.app.services.source_loader import sync_sources


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with session_scope() as session:
        sync_sources(session)
    start_scheduler()
    yield
    stop_scheduler()


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(router)

