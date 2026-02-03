from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.deps import db
from app.routers import auth, mentor, onboarding, parent, planner, submissions, tasks


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
    allow_origins=settings.cors_origins_list,
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


@app.get("/health")
async def health_check():
    return {"status": "ok"}
