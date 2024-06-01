import asyncio
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Path,
    Request,
    Response,
    UploadFile,
)
from fastapi.security import HTTPBearer

from core.auth import upload_role
from core.image import ImageProcessingResult, image_real_path, save_image
from models.dto.image import (
    ImageUploadRequest,
    ImageUploadResponse,
    ProcessedImage,
    ProcessedImageGroup,
)
from utils.content_type import get_content_type
from utils.responses import file_response

router = APIRouter()

auth_scheme = HTTPBearer()


@router.post(
    "/",
    description="Upload images",
    dependencies=[Depends(upload_role)],
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
):
    """Upload images"""

    if data.mode == "single" and len(images) != len(data.configs):
        raise HTTPException(
            status_code=400,
            detail="Number of images and configurations must be the same",
        )

    groups = (
        list(zip(images, [[config] for config in data.configs]))
        if data.mode == "single"
        else [(image, data.configs) for image in images]
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
        ],
        return_exceptions=True,
    )

    def processed_image_group(group: BaseException | ImageProcessingResult):
        if isinstance(group, BaseException):
            return ProcessedImageGroup(status="error", id=uuid4().hex, images=[])

        return ProcessedImageGroup(
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

    return ImageUploadResponse(groups=[processed_image_group(group) for group in processed])


@router.get(
    "/{group_id}/{tag}",
    description="Get image",
    responses={
        200: {"content": {"image/*": {}}, "description": "Image"},
        404: {"description": "Image not found"},
    },
)
async def get_image(
    request: Request,
    group_id: str = Path(..., regex="^[a-zA-Z0-9_\-]+$", description="Group ID"),
    tag: str = Path(..., regex="^[a-zA-Z0-9_\-]+$", description="Tag"),
):
    """Get image"""
    path = image_real_path(group_id, tag)

    if not (content_type := await get_content_type(path)):
        return Response(status_code=404)

    return file_response(
        path,
        range=request.headers.get("range"),
        media_type=content_type,
    )
