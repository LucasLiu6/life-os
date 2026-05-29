from fastapi import FastAPI

from app.api.goals import router as goals_router
from app.api.health import router as health_router
from app.api.tasks import router as tasks_router
from app.config import settings


app = FastAPI(title=settings.app_name)

app.include_router(health_router)
app.include_router(goals_router)
app.include_router(tasks_router)
