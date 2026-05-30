from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.agent import router as agent_router
from app.api.daily_checkins import router as daily_checkins_router
from app.api.goals import router as goals_router
from app.api.health import router as health_router
from app.api.tasks import router as tasks_router
from app.api.telegram import router as telegram_router
from app.config import settings
from app.scheduler.service import shutdown_scheduler, start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    try:
        yield
    finally:
        shutdown_scheduler()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.include_router(health_router)
app.include_router(goals_router)
app.include_router(tasks_router)
app.include_router(daily_checkins_router)
app.include_router(agent_router)
app.include_router(telegram_router)
