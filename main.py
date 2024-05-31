import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, UploadFile

import env
from core.image import save_image
from db import create_all
from models.dto.image import (
    ImageUploadRequest,
    ImageUploadResponse,
    ProcessedImage,
    ProcessedImageGroup,
)


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    # Create database tables
    await create_all()

    # Create a media directory
    os.makedirs(env.IMAGE_PATH, exist_ok=True)

    yield


app = FastAPI(lifespan=app_lifespan, docs_url="/swagger" if env.DEBUG else None, redoc_url=None)


@app.post("/", description="Upload images", response_model=ImageUploadResponse)
async def root(
    data: ImageUploadRequest = Form(..., description="Image upload request"),
    images: list[UploadFile] = File(..., description="Image files"),
) -> ImageUploadResponse:
    """Upload images"""

    if data.mode == "single" and len(images) != len(data.configs):
        return {"detail": "Number of images and configurations must be the same"}, 400

    groups = (
        [(image, data.configs) for image in images]
        if data.mode == "single"
        else list(zip(images, [data.configs]))
    )

    processed = await asyncio.gather(
        *[
            save_image(
                image=await image.read(),
                configs=configs,
                filename=image.filename,
                content_type=image.content_type,
            )
            for image, configs in groups
        ]
    )

    return ImageUploadResponse(
        groups=[
            ProcessedImageGroup(
                id=group.id,
                images=[
                    ProcessedImage(
                        tag=image.tag,
                        size=image.size,
                        width=image.width,
                        height=image.height,
                        quality=image.quality,
                        content_type=image.content_type,
                    )
                    for image in group.images
                ],
            )
            for group in processed
        ]
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=3000)
