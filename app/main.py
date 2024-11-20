import logging

from fastapi import FastAPI
from app.routers.githubble import router as githubble_router


app = FastAPI(
    title="GitHubble",
    description="Look at the dev sky and find awesome repo constellations.",
    version="1.0.0",
)

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s - %(asctime)s - %(name)s - %(message)s",
)

app.include_router(githubble_router)
