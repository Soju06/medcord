import os
import re
import stat
import typing as t
from urllib.parse import quote

import aiofiles
from aiofiles.os import stat as aio_stat
from fastapi.responses import FileResponse
from starlette.datastructures import Headers
from starlette.exceptions import HTTPException
from starlette.responses import Response, guess_type
from starlette.staticfiles import StaticFiles
from starlette.types import Receive, Scope, Send

RANGE_REGEX = re.compile(r"^bytes=(?P<start>\d+)-(?P<end>\d*)$")


PathLike = t.Union[str, "os.PathLike[str]"]


class OpenRange(t.NamedTuple):
    start: int
    end: t.Optional[int] = None

    def clamp(self, start: int, end: int) -> "ClosedRange":
        begin = max(self.start, start)
        end = min((x for x in (self.end, end) if x))

        begin = min(begin, end)
        end = max(begin, end)

        return ClosedRange(begin, end)


class ClosedRange(t.NamedTuple):
    start: int
    end: int

    def __len__(self) -> int:
        return self.end - self.start + 1

    def __bool__(self) -> bool:
        return len(self) > 0


class RangedFileResponse(Response):
    chunk_size = 65536

    def __init__(
        self,
        path: PathLike,
        range: OpenRange,
        headers: t.Optional[t.Dict[str, str]] = None,
        media_type: t.Optional[str] = None,
        filename: t.Optional[str] = None,
        stat_result: t.Optional[os.stat_result] = None,
        method: t.Optional[str] = None,
    ) -> None:
        assert aiofiles is not None, "'aiofiles' must be installed to use FileResponse"
        self.path = path
        self.range = range
        self.filename = filename
        self.send_header_only = method is not None and method.upper() == "HEAD"
        if media_type is None:
            media_type = guess_type(filename or path)[0] or "text/plain"
        self.media_type = media_type
        self.init_headers(headers or {})
        if self.filename is not None:
            content_disposition_filename = quote(self.filename)
            if content_disposition_filename != self.filename:
                content_disposition = f"attachment; filename*=utf-8''{content_disposition_filename}"
            else:
                content_disposition = f'attachment; filename="{self.filename}"'
            self.headers.setdefault("content-disposition", content_disposition)
        self.stat_result = stat_result

    def set_range_headers(self, range: ClosedRange) -> None:
        assert self.stat_result
        total_length = self.stat_result.st_size
        content_length = len(range)
        self.headers["content-range"] = f"bytes {range.start}-{range.end}/{total_length}"
        self.headers["content-length"] = str(content_length)
        pass

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if self.stat_result is None:
            try:
                stat_result = await aio_stat(self.path)
                self.stat_result = stat_result
            except FileNotFoundError:
                raise RuntimeError(f"File at path {self.path} does not exist.")
            else:
                mode = stat_result.st_mode
                if not stat.S_ISREG(mode):
                    raise RuntimeError(f"File at path {self.path} is not a file.")

        byte_range = self.range.clamp(0, self.stat_result.st_size)
        self.set_range_headers(byte_range)

        async with aiofiles.open(self.path, mode="rb") as file:
            await file.seek(byte_range.start)
            await send(
                {
                    "type": "http.response.start",
                    "status": 206,
                    "headers": self.raw_headers,
                }
            )
            if self.send_header_only:
                await send({"type": "http.response.body", "body": b"", "more_body": False})
            else:
                remaining_bytes = len(byte_range)

                if not byte_range:
                    await send({"type": "http.response.body", "body": b"", "more_body": False})
                    return

                while remaining_bytes > 0:
                    chunk_size = min(self.chunk_size, remaining_bytes)
                    chunk = await file.read(chunk_size)
                    remaining_bytes -= len(chunk)
                    await send(
                        {
                            "type": "http.response.body",
                            "body": chunk,
                            "more_body": remaining_bytes > 0,
                        }
                    )


def file_response(
    path: PathLike,
    range: str | None = None,
    media_type: str | None = None,
    filename: str | None = None,
) -> Response:
    if range is not None:
        match = RANGE_REGEX.match(range)

        if match is None:
            raise HTTPException(416, "Invalid range")

        end = match.group("end")

        return RangedFileResponse(
            path,
            OpenRange(int(match.group("start")), int(end) if end else None),
            media_type=media_type,
            filename=filename,
        )

    return FileResponse(
        path,
        media_type=media_type,
        filename=filename,
    )
