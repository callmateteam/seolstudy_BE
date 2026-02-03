from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings as app_settings
from app.core.deps import db
from app.routers import (
    analysis,
    auth,
    coaching,
    feedback,
    materials,
    mentor,
    onboarding,
    parent,
    planner,
    settings,
    submissions,
    tasks,
    uploads,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    yield
    await db.disconnect()


app = FastAPI(
    title="설스터디 API",
    description="수능 국영수 학습 코칭 플랫폼 백엔드",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth.router)
app.include_router(onboarding.router)
app.include_router(tasks.router)
app.include_router(submissions.router)
app.include_router(planner.router)
app.include_router(mentor.router)
app.include_router(parent.router)
app.include_router(uploads.router)
app.include_router(analysis.router)
app.include_router(materials.router)
app.include_router(coaching.router)
app.include_router(feedback.router)
app.include_router(settings.router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
