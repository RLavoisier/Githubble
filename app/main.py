import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.models import init_db
from app.routers.githubble import router as githubble_router
from app.routers.user import router as user_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="GitHubble",
    description="Look at the dev sky and find awesome repo constellations.",
    version="1.0.0",
    lifespan=lifespan,
)

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s - %(asctime)s - %(name)s - %(message)s",
)

app.include_router(githubble_router)
app.include_router(user_router)
