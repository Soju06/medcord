from datetime import datetime
from uuid import uuid4

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String

import env
from db import Base


class Image(Base):
    __tablename__ = env.DATABASE_TABLE_PREFIX + "images"

    id: int = Column(BigInteger, primary_key=True, autoincrement=True)
    """Image ID"""
    group_id: str = Column(
        String(255), ForeignKey(env.DATABASE_TABLE_PREFIX + "image_groups.id"), nullable=False
    )
    """Image group ID"""
    tag = Column(String(255), nullable=False)
    """Tag"""
    size: int = Column(BigInteger, nullable=False)
    """Size"""
    width: int = Column(BigInteger, nullable=False)
    """Width"""
    height: int = Column(BigInteger, nullable=False)
    """Height"""
    quality: int = Column(BigInteger, nullable=False)
    """Quality"""
    content_type: str = Column(String(255), nullable=False)
    """Content type"""

    def __init__(
        self,
        group_id: str,
        tag: str,
        size: int,
        width: int,
        height: int,
        quality: int,
        content_type: str,
    ):
        super().__init__(
            group_id=group_id,
            tag=tag,
            size=size,
            width=width,
            height=height,
            quality=quality,
            content_type=content_type,
        )


class ImageGroup(Base):
    __tablename__ = env.DATABASE_TABLE_PREFIX + "image_groups"

    id: str = Column(String(255), nullable=False, primary_key=True, default=lambda: uuid4().hex)
    """Image group ID"""
    filename: str = Column(String(255), nullable=False)
    """Original filename"""
    width: int = Column(BigInteger, nullable=False)
    """Original width"""
    height: int = Column(BigInteger, nullable=False)
    """Original height"""
    content_type: str = Column(String(255), nullable=False)
    """Original content type"""
    created_at: datetime = Column(DateTime, nullable=False, default=datetime.now)
    """Created at"""

    def __init__(self, filename: str, width: int, height: int, content_type: str):
        super().__init__(
            filename=filename,
            width=width,
            height=height,
            content_type=content_type,
        )
