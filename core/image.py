import asyncio
import io
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from os import path

import aiofiles
import aiofiles.os
import PIL.Image
import pillow_avif  # DO NOT REMOVE
from PIL import ImageFile, ImageOps
from PIL.Image import Image as PILImage

import env
from db import scope
from models.dto.image import ImageConfig
from models.image import Image, ImageGroup

ImageFile.LOAD_TRUNCATED_IMAGES = True

thread_pool = ThreadPoolExecutor(max_workers=env.IMAGE_PROCESSING_THREAD)


@dataclass
class ProcessedImage:
    tag: str
    image: bytes
    size: int
    width: int
    height: int
    quality: int
    content_type: str
    extension: str


def process_image(image: PILImage, config: ImageConfig) -> ProcessedImage:
    """Process image"""
    extension = config.content_type.split("/")[1]

    if config.fit == "cover":
        image = ImageOps.fit(image, (config.width, config.height), method=0, bleed=0.0, centering=(0.5, 0.5))
    elif config.fit == "contain":
        image.thumbnail((config.width, config.height))
    elif config.fit == "fill":
        image = ImageOps.fit(image, (config.width, config.height), method=0, bleed=0.0, centering=(0.5, 0.5))
    elif config.fit == "inside":
        image.thumbnail((config.width, config.height))
    elif config.fit == "outside":
        image.thumbnail((config.width, config.height))

    image_bytes = io.BytesIO()

    image.save(image_bytes, format=extension, quality=config.quality)
    image_bytes = image_bytes.getvalue()

    return ProcessedImage(
        tag=config.tag,
        image=image_bytes,
        size=len(image_bytes),
        width=image.width,
        height=image.height,
        quality=config.quality,
        content_type=config.content_type,
        extension=extension,
    )


async def load_image(image: bytes | io.BytesIO) -> PILImage:
    """Load image"""

    if isinstance(image, bytes):
        image = io.BytesIO(image)

    image = await asyncio.get_event_loop().run_in_executor(thread_pool, PIL.Image.open, image)

    return image


@dataclass
class ProcessedResult:
    id: str
    images: list[ProcessedImage]


async def save_image(
    image: PILImage | bytes | io.BytesIO,
    configs: list[ImageConfig],
    filename: str = "image.jpg",
    content_type: str = "image/jpeg",
) -> ProcessedResult:
    """Save image"""

    if len(configs) == 0:
        raise ValueError("No image configuration")

    if not isinstance(image, PILImage):
        image = await load_image(image)

    loop = asyncio.get_event_loop()
    features = [loop.run_in_executor(thread_pool, process_image, image, config) for config in configs]

    async with scope() as session:
        group = ImageGroup(
            filename=filename,
            width=image.width,
            height=image.height,
            content_type=content_type,
        )

        session.add(group)
        await session.commit()
        await session.refresh(group, ["id"])

        group_id = group.id

        images = []

        while features:
            done, features = await asyncio.wait(features, return_when=asyncio.FIRST_COMPLETED)

            for future in done:
                processed: ProcessedImage = future.result()

                async with aiofiles.open(
                    path.join(env.IMAGE_PATH, f"{group_id}_{processed.tag}"),
                    "wb",
                ) as f:
                    await f.write(processed.image)

                image = Image(
                    group_id=group_id,
                    tag=processed.tag,
                    size=processed.size,
                    width=processed.width,
                    height=processed.height,
                    quality=processed.quality,
                    content_type=processed.content_type,
                )

                session.add(image)
                images.append(processed)

        await session.commit()

        return ProcessedResult(
            id=group_id,
            images=images,
        )
