import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

import env
import router.image
from db import create_all


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    # Create database tables
    await create_all()

    # Create a media directory
    os.makedirs(env.IMAGE_PATH, exist_ok=True)

    yield


app = FastAPI(lifespan=app_lifespan, docs_url="/swagger" if env.DEBUG else None, redoc_url=None)

app.include_router(
    router.image.router,
    prefix="/images",
    tags=["images"],
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=3000)
