import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from os import path
from uuid import uuid4

from moviepy.editor import VideoClip, VideoFileClip
from moviepy.tools import find_extension

import env
from db import scope
from models.dto.video import VideoConfig
from models.video import Video, VideoGroup

thread_pool = ThreadPoolExecutor(max_workers=env.VIDEO_PROCESSING_THREAD)

extensions_dict: dict[str, str] = {
    "libx264": "mp4",
    "libmpeg4": "mp4",
    "aac": "mp4",
    "libtheora": "ogv",
    "libvpx": "webm",
}


@dataclass
class ProcessedVideo:
    tag: str
    size: int
    width: int
    height: int
    start: float
    end: float
    duration: float
    frame_rate: int
    codec: str
    bitrate: int | None
    mute: bool
    audio_sample_rate: int | None


def process_video(group_id: str, video: VideoClip, config: VideoConfig) -> ProcessedVideo:
    """Process video"""
    if config.start is not None or config.end is not None:
        video = video.subclip(config.start or 0, config.end)

    if config.frame_rate is not None:
        video = video.set_fps(config.frame_rate)

    if config.mute:
        video = video.without_audio()

    width, height = video.size

    match config.fit:
        case "cover":
            original_aspect = width / height
            target_aspect = config.width / config.height

            if original_aspect > target_aspect:
                new_height = height
                new_width = int(new_height * target_aspect)
            else:
                new_width = width
                new_height = int(new_width / target_aspect)

            video = video.crop(
                x1=(width - new_width) // 2,
                y1=(height - new_height) // 2,
                width=new_width,
                height=new_height,
            )
            video = video.resize((config.width, config.height))

        case "contain":
            original_aspect = width / height
            target_aspect = config.width / config.height

            if original_aspect > target_aspect:
                resize_width = config.width
                resize_height = int(config.width / original_aspect)
            else:
                resize_height = config.height
                resize_width = int(config.height * original_aspect)

            margin_left = (config.width - resize_width) // 2
            margin_top = (config.height - resize_height) // 2
            margin_right = config.width - resize_width - margin_left
            margin_bottom = config.height - resize_height - margin_top

            video = video.resize((resize_width, resize_height))

            if original_aspect != target_aspect:
                video = video.margin(
                    left=margin_left,
                    top=margin_top,
                    right=margin_right,
                    bottom=margin_bottom,
                )

        case "fill":
            video = video.resize((config.width, config.height))

        case "inside":
            original_aspect = width / height
            target_aspect = config.width / config.height

            if original_aspect > target_aspect:
                resize_width = config.width
                resize_height = int(config.width / original_aspect)
            else:
                resize_height = config.height
                resize_width = int(config.height * original_aspect)

            video = video.resize((resize_width, resize_height))

        case "outside":
            original_aspect = width / height
            target_aspect = config.width / config.height

            if original_aspect > target_aspect:
                resize_height = config.height
                resize_width = int(config.height * original_aspect)
            else:
                resize_width = config.width
                resize_height = int(config.width / original_aspect)

            video = video.resize((resize_width, resize_height))

        case _:
            pass

    width, height = video.size
    extension = extensions_dict[config.codec]
    video_file = video_real_path(group_id, config.tag)

    if extension in ["ogv", "webm"]:
        audio_codec = "libvorbis"
        audio_extension = "ogg"
    else:
        audio_codec = "libmp3lame"
        audio_extension = "mp3"

    temp_audio = path.join(env.TEMPORARY_PATH, f"{uuid4().hex}.{audio_extension}")

    video.write_videofile(
        f"{video_file}.{extension}",
        codec=config.codec,
        bitrate=f"{config.bitrate}k" if config.bitrate is not None and config.codec == "libx264" else None,
        audio_fps=config.audio_sample_rate or 44100,
        audio_codec=audio_codec,
        temp_audiofile=temp_audio,
    )

    if os.path.exists(temp_audio):
        os.remove(temp_audio)

    os.rename(f"{video_file}.{extension}", video_file)

    image = ProcessedVideo(
        tag=config.tag,
        size=path.getsize(video_file),
        width=width,
        height=height,
        start=(
            0 if config.start is None else config.start if config.start > 0 else video.duration + config.start
        ),
        end=(
            video.duration
            if config.end is None
            else config.end if config.end > 0 else video.duration + config.end
        ),
        duration=video.duration,
        frame_rate=video.fps,
        codec=config.codec,
        bitrate=config.bitrate if config.codec == "libx264" else None,
        mute=config.mute,
        audio_sample_rate=config.audio_sample_rate,
    )

    video.close()

    return image


@dataclass
class VideoProcessingResult:
    id: str
    videos: list[ProcessedVideo]


async def save_video(
    video: str | VideoClip,
    configs: list[VideoConfig],
    filename: str = "image.jpg",
) -> VideoProcessingResult:
    """Save video"""

    if len(configs) == 0:
        raise ValueError("No video configuration")

    loop = asyncio.get_event_loop()

    if not isinstance(video, VideoClip):
        video = await loop.run_in_executor(thread_pool, VideoFileClip, video)
        close = True
    else:
        close = False

    try:
        async with scope() as session:
            group = VideoGroup(
                filename=filename,
                width=video.w,
                height=video.h,
                duration=video.duration,
                frame_rate=video.fps,
                mute=video.audio is None,
            )

            session.add(group)
            await session.commit()
            await session.refresh(group, ["id"])

            group_id = group.id
            features = [
                loop.run_in_executor(thread_pool, process_video, group_id, video, config)
                for config in configs
            ]

            videos: list[ProcessedVideo] = []

            while features:
                done, features = await asyncio.wait(features, return_when=asyncio.FIRST_COMPLETED)

                for future in done:
                    processed: ProcessedVideo = future.result()

                    session.add(
                        Video(
                            group_id=group_id,
                            tag=processed.tag,
                            size=processed.size,
                            width=processed.width,
                            height=processed.height,
                            duration=processed.duration,
                            frame_rate=processed.frame_rate,
                            codec=processed.codec,
                            bitrate=processed.bitrate,
                            mute=processed.mute,
                            audio_sample_rate=processed.audio_sample_rate,
                        )
                    )
                    videos.append(processed)

            await session.commit()
    finally:
        if close:
            video.close()

    return VideoProcessingResult(
        id=group_id,
        videos=videos,
    )


def video_real_path(group_id: str, tag: str) -> str:
    """Get real path"""
    return path.join(env.VIDEO_PATH, f"{group_id}_{tag}")
