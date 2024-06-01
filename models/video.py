from datetime import datetime
from uuid import uuid4

from sqlalchemy import BigInteger, Column, DateTime, Double, ForeignKey, String

import env
from db import Base


class Video(Base):
    __tablename__ = env.DATABASE_TABLE_PREFIX + "videos"

    id: int = Column(BigInteger, primary_key=True, autoincrement=True)
    """Video ID"""
    group_id: str = Column(
        String(255),
        ForeignKey(env.DATABASE_TABLE_PREFIX + "video_groups.id", ondelete="CASCADE"),
        nullable=False,
    )
    """Video group ID"""
    tag = Column(String(255), nullable=False)
    """Tag"""
    size: int = Column(BigInteger, nullable=False)
    """Size"""
    width: int = Column(BigInteger, nullable=False)
    """Width"""
    height: int = Column(BigInteger, nullable=False)
    """Height"""
    duration: float = Column(Double, nullable=False)
    """Duration in seconds"""
    frame_rate: int = Column(BigInteger, nullable=False)
    """Frame rate"""
    codec: str = Column(String(255), nullable=False)
    """Codec"""
    bitrate: int | None = Column(BigInteger, nullable=True)
    """Bitrate"""
    mute: bool = Column(String(255), nullable=False)
    """Mute"""
    audio_sample_rate: int | None = Column(BigInteger, nullable=True)
    """Audio sample rate"""

    def __init__(
        self,
        group_id: str,
        tag: str,
        size: int,
        width: int,
        height: int,
        duration: float,
        frame_rate: int,
        codec: str,
        bitrate: int | None,
        mute: bool,
        audio_sample_rate: int | None,
    ):
        super().__init__(
            group_id=group_id,
            tag=tag,
            size=size,
            width=width,
            height=height,
            duration=duration,
            frame_rate=frame_rate,
            codec=codec,
            bitrate=bitrate,
            mute=mute,
            audio_sample_rate=audio_sample_rate,
        )


class VideoGroup(Base):
    __tablename__ = env.DATABASE_TABLE_PREFIX + "video_groups"

    id: str = Column(String(255), nullable=False, primary_key=True, default=lambda: uuid4().hex)
    """Video group ID"""
    filename: str = Column(String(255), nullable=False)
    """Original filename"""
    width: int = Column(BigInteger, nullable=False)
    """Original width"""
    height: int = Column(BigInteger, nullable=False)
    """Original height"""
    duration: float = Column(Double, nullable=False)
    """Duration in seconds"""
    frame_rate: int = Column(BigInteger, nullable=False)
    """Frame rate"""
    mute: bool = Column(String(255), nullable=False)
    """Mute"""
    created_at: datetime = Column(DateTime, nullable=False, default=datetime.now)
    """Created at"""

    def __init__(
        self,
        filename: str,
        width: int,
        height: int,
        duration: float,
        frame_rate: int,
        mute: bool,
    ):
        super().__init__(
            filename=filename,
            width=width,
            height=height,
            duration=duration,
            frame_rate=frame_rate,
            mute=mute,
        )
