import json
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ImageConfig(BaseModel):
    """Image configuration"""

    tag: str = Field(..., min_length=1, max_length=255, pattern="^[a-zA-Z0-9_\-]+$", description="Image Tag")
    """Tag"""
    width: int = Field(..., ge=1, description="Image Width")
    """Image width"""
    height: int = Field(..., ge=1, description="Image Height")
    """Image height"""
    quality: int = Field(100, ge=0, le=100, description="Image Quality")
    """Quality (0-100)"""
    content_type: Literal[
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/avif",
        "image/gif",
    ] = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Content Type\n- image/jpeg (JPEG)\n- image/png (PNG)\n- image/webp (WebP)\n- image/avif (AVIF)\n- image/gif (GIF)",
    )
    """
    Content type
    
    - `image/jpeg` (JPEG)
    - `image/png` (PNG)
    - `image/webp` (WebP)
    - `image/avif` (AVIF)
    - `image/gif` (GIF)
    """
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


class ImageUploadRequest(BaseModel):
    """Image upload request"""

    configs: list[ImageConfig] = Field(..., min_items=1, description="Image configurations")
    """Image configurations"""

    mode: Literal["single", "batch"] = Field(
        "batch",
        description="""Config mode\n- single: Use a single configuration per image.\n- batch: Use multiple configurations per image.""",
    )
    """
    Config mode
    
    - `single`: Use a single configuration per image.
    - `batch`: Use multiple configurations per image.
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


class ProcessedImage(BaseModel):
    """Processed image"""

    tag: str = Field(..., min_length=1, max_length=255, pattern="^[a-zA-Z0-9_\-]+$", description="Image Tag")
    """Tag"""
    size: int = Field(..., ge=0, description="Size")
    """Size"""
    width: int = Field(..., ge=1, description="Width")
    """Width"""
    height: int = Field(..., ge=1, description="Height")
    """Height"""
    quality: int = Field(..., ge=0, le=100, description="Quality")
    """Quality"""
    content_type: Literal[
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/avif",
        "image/gif",
    ] = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Content Type\n- image/jpeg (JPEG)\n- image/png (PNG)\n- image/webp (WebP)\n- image/avif (AVIF)\n- image/gif (GIF)",
    )
    """
    Content type
    
    - `image/jpeg` (JPEG)
    - `image/png` (PNG)
    - `image/webp` (WebP)
    - `image/avif` (AVIF)
    - `image/gif` (GIF)
    """


class ProcessedImageGroup(BaseModel):
    """Processed image group"""

    status: Literal["success", "error"] = Field("success", description="Status")
    """Status"""

    id: str = Field(..., min_length=1, max_length=255, pattern="^[a-zA-Z0-9_\-]+$", description="Group ID")
    """Group ID"""
    images: list[ProcessedImage] = Field(..., min_items=0, description="Processed images")
    """Processed images"""


class ImageUploadResponse(BaseModel):
    """Image upload response"""

    groups: list[ProcessedImageGroup] = Field(..., min_items=1, description="Processed image groups")
    """Processed image groups"""
