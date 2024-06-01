import asyncio
from os import path
from uuid import uuid4

import aiofiles
import aiofiles.os
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

import env
from core.auth import upload_role
from core.video import VideoProcessingResult, save_video, video_real_path
from models.dto.video import (
    ProcessedVideo,
    ProcessedVideoGroup,
    VideoUploadRequest,
    VideoUploadResponse,
)
from utils.content_type import get_content_type
from utils.responses import file_response

router = APIRouter()

auth_scheme = HTTPBearer()


@router.post(
    "/",
    description="Upload videos",
    dependencies=[Depends(upload_role)],
    responses={
        200: {"model": VideoUploadResponse, "description": "Video upload response"},
        401: {
            "description": "Unauthorized",
            "content": {
                "application/json": {
                    "example": {"detail": "Unauthorized"},
                }
            },
        },
        400: {
            "description": "Number of videos and configurations must be the same",
            "content": {
                "application/json": {
                    "example": {"detail": "Number of videos and configurations must be the same"},
                }
            },
        },
    },
)
async def post_video(
    data: VideoUploadRequest = Form(..., description="Video upload request"),
    videos: list[UploadFile] = File(..., description="Video files"),
):
    """Upload videos"""

    if data.mode == "single" and len(videos) != len(data.configs):
        raise HTTPException(
            status_code=400,
            detail="Number of videos and configurations must be the same",
        )

    video_files: list[str] = []

    try:
        for video in videos:
            video_files.append(file_path := path.join(env.TEMPORARY_PATH, uuid4().hex))

            async with aiofiles.open(file_path, "wb") as file:
                while content := await video.read(65536):
                    await file.write(content)

        processed = await asyncio.gather(
            *[
                save_video(
                    video=video_file,
                    configs=configs,
                    filename=video.filename,
                )
                for video_file, video, configs in zip(
                    video_files,
                    videos,
                    (
                        [[config] for config in data.configs]
                        if data.mode == "single"
                        else [data.configs] * len(videos)
                    ),
                )
            ],
            return_exceptions=True,
        )

        def processed_video_group(group: BaseException | VideoProcessingResult):
            if isinstance(group, BaseException):
                return ProcessedVideoGroup(status="error", id=uuid4().hex, videos=[])

            return ProcessedVideoGroup(
                id=group.id,
                videos=[
                    ProcessedVideo(
                        tag=video.tag,
                        size=video.size,
                        width=video.width,
                        height=video.height,
                        start=video.start,
                        end=video.end,
                        duration=video.duration,
                        frame_rate=video.frame_rate,
                        codec=video.codec,
                        bitrate=video.bitrate,
                        mute=video.mute,
                        audio_sample_rate=video.audio_sample_rate,
                    )
                    for video in group.videos
                ],
            )

        return VideoUploadResponse(groups=[processed_video_group(group) for group in processed])
    finally:
        for video_file in video_files:
            if await aiofiles.os.path.exists(video_file):
                await aiofiles.os.remove(video_file)


@router.get(
    "/{group_id}/{tag}",
    description="Get video",
    responses={
        200: {"content": {"video/*": {}}, "description": "video"},
        404: {"description": "Video not found"},
    },
)
async def get_video(
    request: Request,
    group_id: str = Path(..., description="Group ID"),
    tag: str = Path(..., description="Tag"),
):
    """Get video"""
    path = video_real_path(group_id, tag)

    if not (content_type := await get_content_type(path)):
        return Response(status_code=404)

    return file_response(
        path,
        range=request.headers.get("range"),
        media_type=content_type,
    )
