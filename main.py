import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

import env
import router.image
import router.video
from db import create_all


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    # Create a media directory
    os.makedirs(env.IMAGE_PATH, exist_ok=True)
    os.makedirs(env.VIDEO_PATH, exist_ok=True)
    os.makedirs(env.TEMPORARY_PATH, exist_ok=True)

    # Create database tables
    await create_all()

    yield


app = FastAPI(lifespan=app_lifespan, docs_url="/swagger" if env.DEBUG else None, redoc_url=None)

app.include_router(
    router.image.router,
    prefix="/images",
    tags=["Images"],
)

app.include_router(
    router.video.router,
    prefix="/videos",
    tags=["Videos"],
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=3000)
