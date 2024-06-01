import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Form, Path, Request, Response, UploadFile
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.responses import JSONResponse

import env
from core.image import get_content_type, real_path, save_image
from db import create_all
from models.dto.image import (
    ImageUploadRequest,
    ImageUploadResponse,
    ProcessedImage,
    ProcessedImageGroup,
)
from utils.responses import file_response


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    # Create database tables
    await create_all()

    # Create a media directory
    os.makedirs(env.IMAGE_PATH, exist_ok=True)

    yield


app = FastAPI(lifespan=app_lifespan, docs_url="/swagger" if env.DEBUG else None, redoc_url=None)

auth_scheme = HTTPBearer()


@app.post(
    "/images",
    description="Upload images",
    responses={
        200: {"model": ImageUploadResponse, "description": "Image upload response"},
        401: {
            "description": "Unauthorized",
            "content": {
                "application/json": {
                    "example": {"detail": "Unauthorized"},
                }
            },
        },
        400: {
            "description": "Number of images and configurations must be the same",
            "content": {
                "application/json": {
                    "example": {"detail": "Number of images and configurations must be the same"},
                }
            },
        },
    },
)
async def post_image(
    data: ImageUploadRequest = Form(..., description="Image upload request"),
    images: list[UploadFile] = File(..., description="Image files"),
    token: HTTPAuthorizationCredentials = Depends(auth_scheme),
):
    """Upload images"""

    if env.PASSWORD and token.credentials != env.PASSWORD:
        return JSONResponse(
            status_code=401,
            content={"detail": "Unauthorized"},
        )

    if data.mode == "single" and len(images) != len(data.configs):
        return JSONResponse(
            status_code=400,
            content={"detail": "Number of images and configurations must be the same"},
        )

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


@app.get("/images/{group_id}/{tag}")
async def get_image(
    request: Request,
    group_id: str = Path(..., description="Group ID"),
    tag: str = Path(..., description="Tag"),
):
    """Get image"""
    if not (content_type := await get_content_type(group_id, tag)):
        return Response(status_code=404)

    return file_response(
        real_path(group_id, tag),
        range=request.headers.get("range"),
        media_type=content_type,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=3000)
