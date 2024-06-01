import json
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class VideoConfig(BaseModel):
    """Video configuration"""

    tag: str = Field(..., min_length=1, max_length=255, pattern="^[a-zA-Z0-9_\-]+$", description="Video Tag")
    """Tag"""
    width: int = Field(..., ge=1, description="Video Width")
    """Video width"""
    height: int = Field(..., ge=1, description="Video Height")
    """Video height"""
    fit: Literal[
        "cover",
        "contain",
        "fill",
        "inside",
        "outside",
    ] = Field(
        "inside",
        min_length=1,
        max_length=255,
        description="Image Fit\n- cover: Resize the image to fill the specified dimensions, cropping the image if necessary.\n- contain: Resize the image to fit within the specified dimensions, maintaining the original aspect ratio.\n- fill: Resize the image to the specified dimensions, cropping the image if necessary.\n- inside: Resize the image to be as large as possible while ensuring its dimensions are less than or equal to the specified dimensions.\n- outside: Resize the image to be as small as possible while ensuring its dimensions are greater than or equal to the specified dimensions.",
    )
    """
    Fit
    
    - `cover`: Resize the image to fill the specified dimensions, cropping the image if necessary.
    - `contain`: Resize the image to fit within the specified dimensions, maintaining the original aspect ratio.
    - `fill`: Resize the image to the specified dimensions, cropping the image if necessary.
    - `inside`: Resize the image to be as large as possible while ensuring its dimensions are less than or equal to the specified dimensions.
    - `outside`: Resize the image to be as small as possible while ensuring its dimensions are greater than or equal to the specified dimensions.
    """
    start: float | None = Field(None, description="Start Time (seconds). supported negative values")
    """Start time"""
    end: float | None = Field(None, description="End Time (seconds). supported negative values")
    """End time"""
    frame_rate: int | None = Field(None, ge=1, description="Frame Rate")
    """Frame rate"""
    codec: Literal[
        "libx264",
        "libmpeg4",
        "aac",
        "libtheora",
        "libvpx",
    ] = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Codec\n- libx264 (H.264, .mp4)\n- libmpeg4 (MPEG-4, .mp4)\n- aac (AAC, .mp4)\n- libtheora (Theora, .ogv)\n- libvpx (VP8, .webm)",
    )
    """
    Codec

    - `libx264` (H.264, .mp4)
    - `libmpeg4` (MPEG-4, .mp4)
    - `aac` (AAC, .mp4)
    - `libtheora` (Theora, .ogv)
    - `libvpx` (VP8, .webm)
    """
    bitrate: int | None = Field(None, ge=1, description="Bitrate (kbps) supported for libx264 codec")
    """Bitrate (kbps) supported for libx264 codec"""
    mute: bool = Field(False, description="Mute")
    """Mute"""
    audio_sample_rate: int | None = Field(None, ge=1, description="Audio Sample Rate (Hz)")
    """Audio sample rate (Hz)"""


class VideoUploadRequest(BaseModel):
    """Video upload request"""

    configs: list[VideoConfig] = Field(..., min_items=1, description="Video configurations")
    """Video configurations"""

    mode: Literal["single", "batch"] = Field(
        "batch",
        description="""Config mode\n- single: Use a single configuration per video.\n- batch: Use multiple configurations per video.""",
    )
    """
    Config mode
    
    - `single`: Use a single configuration per video.
    - `batch`: Use multiple configurations per video.
    """

    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            value = cls(**json.loads(value))

        if isinstance(value, dict):
            if len(set(config["tag"] for config in value["configs"])) != len(value["configs"]):
                raise ValueError("Duplicate tags are not allowed")

        return value


class ProcessedVideo(BaseModel):
    """Processed image"""

    tag: str = Field(..., min_length=1, max_length=255, pattern="^[a-zA-Z0-9_\-]+$", description="Image Tag")
    """Tag"""
    size: int = Field(..., ge=0, description="Size")
    """Size"""
    width: int = Field(..., ge=1, description="Width")
    """Width"""
    height: int = Field(..., ge=1, description="Height")
    """Height"""
    start: float = Field(..., ge=0, description="Start Time (seconds)")
    """Start time"""
    end: float = Field(..., ge=0, description="End Time (seconds)")
    """End time"""
    duration: float = Field(..., ge=0, description="Duration")
    """Duration"""
    frame_rate: int = Field(..., ge=1, description="Frame Rate")
    """Frame rate"""
    codec: Literal[
        "libx264",
        "libmpeg4",
        "aac",
        "libtheora",
        "libvpx",
    ] = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Codec\n- libx264 (H.264, .mp4)\n- libmpeg4 (MPEG-4, .mp4)\n- aac (AAC, .mp4)\n- libtheora (Theora, .ogv)\n- libvpx (VP8, .webm)",
    )
    """
    Codec

    - `libx264` (H.264, .mp4)
    - `libmpeg4` (MPEG-4, .mp4)
    - `aac` (AAC, .mp4)
    - `libtheora` (Theora, .ogv)
    - `libvpx` (VP8, .webm)
    """
    bitrate: int | None = Field(None, ge=1, description="Bitrate (kbps) supported for libx264 codec")
    """Bitrate (kbps) supported for libx264 codec"""
    mute: bool = Field(False, description="Mute")
    """Mute"""
    audio_sample_rate: int | None = Field(None, ge=1, description="Audio Sample Rate (Hz)")
    """Audio sample rate (Hz)"""


class ProcessedVideoGroup(BaseModel):
    """Processed video group"""

    status: Literal["success", "error"] = Field("success", description="Status")
    """Status"""

    id: str = Field(..., min_length=1, max_length=255, pattern="^[a-zA-Z0-9_\-]+$", description="Group ID")
    """Group ID"""
    videos: list[ProcessedVideo] = Field(..., min_items=0, description="Processed videos")
    """Processed videos"""


class VideoUploadResponse(BaseModel):
    """Video upload response"""

    groups: list[ProcessedVideoGroup] = Field(..., min_items=1, description="Processed video groups")
    """Processed video groups"""
