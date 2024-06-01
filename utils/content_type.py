import aiofiles


async def get_content_type(file_path: str) -> str | None:
    """Get content type"""

    try:
        async with aiofiles.open(file_path, "rb") as file:
            header = await file.read(12)
    except FileNotFoundError:
        return None

    if header[:3] == b"\xFF\xD8\xFF":
        return "image/jpeg"
    elif header[:8] == b"\x89\x50\x4E\x47\x0D\x0A\x1A\x0A":
        return "image/png"
    elif header[:4] == b"\x52\x49\x46\x46" and header[8:12] == b"\x57\x45\x42\x50":
        return "image/webp"
    elif header[4:12] == b"ftypavif" or header[4:12] == b"ftypavis":
        return "image/avif"
    elif header[:5] == b"GIF87" or header[:5] == b"GIF89":
        return "image/gif"
    elif header[4:12] == b"ftypisom" or header[4:12] == b"ftypmp42":
        return "video/mp4"
    elif header[:4] == b"\x1A\x45\xDF\xA3":
        return "video/webm"
    elif header[:4] == b"OggS":
        return "video/ogg"

    return "application/octet-stream"
