import asyncio
import io
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from os import path

import aiofiles
import aiofiles.os
import PIL.Image
import pillow_avif  # DO NOT REMOVE
from PIL import ImageFile, ImageOps
from PIL.Image import Image as PILImage
from sqlalchemy import delete, select

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


def transform_image(image: PILImage, config: ImageConfig) -> PILImage:
    """Transform image"""

    match config.fit:
        case "cover":
            image = ImageOps.fit(
                image, (config.width, config.height), method=0, bleed=0.0, centering=(0.5, 0.5)
            )

        case "contain":
            image = image.copy()
            image.thumbnail((config.width, config.height))

        case "fill":
            image = ImageOps.fit(
                image, (config.width, config.height), method=0, bleed=0.0, centering=(0.5, 0.5)
            )

        case "inside":
            image = image.copy()
            image.thumbnail((config.width, config.height))

        case "outside":
            image = image.copy()
            image.thumbnail((config.width, config.height))

        case _:
            pass

    return image


def process_image(image: PILImage, config: ImageConfig) -> ProcessedImage:
    """Process image"""

    if config.content_type == "image/jpeg":
        image = image.convert("RGB")

    info = getattr(image, "info", {})
    n_frames = (
        getattr(image, "n_frames", 1)
        if config.content_type in ["image/gif", "image/webp", "image/avif"]
        else 1
    )
    frames: list[PILImage | Future[PILImage]] = []

    for frame in range(n_frames):
        image.seek(frame)
        frames.append(thread_pool.submit(transform_image, image.copy(), config))

    frames = [future.result() for future in frames]
    extension = config.content_type.split("/")[1]

    with io.BytesIO() as image_bytes:
        frames[0].save(
            image_bytes,
            format=extension,
            quality=config.quality,
            append_images=frames[1:],
            optimize=True,
            **(
                {
                    "save_all": True,
                    "duration": info.get("duration", 0),
                    "loop": info.get("loop", 0),
                }
                if n_frames > 1
                else {}
            ),
        )
        image_bytes = image_bytes.getvalue()

    return ProcessedImage(
        tag=config.tag,
        image=image_bytes,
        size=len(image_bytes),
        width=frames[0].width,
        height=frames[0].height,
        quality=config.quality,
        content_type=config.content_type,
        extension=extension,
    )


@dataclass
class ImageProcessingResult:
    id: str
    images: list[ProcessedImage]


async def save_image(
    image: PILImage | bytes | io.BytesIO,
    configs: list[ImageConfig],
    filename: str = "image.jpg",
    content_type: str = "image/jpeg",
) -> ImageProcessingResult:
    """Save image"""

    if len(configs) == 0:
        raise ValueError("No image configuration")

    loop = asyncio.get_event_loop()

    if not isinstance(image, PILImage):
        if isinstance(image, bytes):
            image = io.BytesIO(image)

        image = await loop.run_in_executor(thread_pool, PIL.Image.open, image)
        await loop.run_in_executor(thread_pool, image.load)

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
                    image_real_path(group_id, processed.tag),
                    "wb",
                ) as f:
                    await f.write(processed.image)

                session.add(
                    Image(
                        group_id=group_id,
                        tag=processed.tag,
                        size=processed.size,
                        width=processed.width,
                        height=processed.height,
                        quality=processed.quality,
                        content_type=processed.content_type,
                    )
                )
                images.append(processed)

        await session.commit()

        return ImageProcessingResult(
            id=group_id,
            images=images,
        )


def image_real_path(group_id: str, tag: str) -> str:
    """Get real path"""
    return path.join(env.IMAGE_PATH, f"{group_id}_{tag}")


async def remove_image(group_id: str) -> bool:
    """Remove image"""
    async with scope() as session:
        tags: list[str] = (
            (await session.execute(select(Image.tag).where(Image.group_id == group_id))).scalars().all()
        )

        if not tags:
            return False

        await session.execute(delete(ImageGroup).where(ImageGroup.id == group_id))
        await session.commit()

    for tag in tags:
        if await aiofiles.os.path.exists(image_real_path(group_id, tag)):
            await aiofiles.os.remove(image_real_path(group_id, tag))

    return True
