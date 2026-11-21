from pathlib import Path
from typing import Iterator

from fastapi import HTTPException, Request, status
from fastapi.responses import StreamingResponse


def _file_chunk_iterator(file_path: Path, start: int, end: int, chunk_size: int = 65536) -> Iterator[bytes]:
    with file_path.open("rb") as f:
        f.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            chunk = f.read(min(chunk_size, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


def build_video_stream_response(
    file_path: Path,
    request: Request,
    download_filename: str,
    as_attachment: bool = False,
) -> StreamingResponse:
    file_size = file_path.stat().st_size
    disposition = "attachment" if as_attachment else "inline"
    base_headers = {
        "Accept-Ranges": "bytes",
        "Content-Disposition": f'{disposition}; filename="{download_filename}"',
        "Cache-Control": "public, max-age=3600",
    }

    range_header = request.headers.get("range")
    if not range_header:
        headers = {**base_headers, "Content-Length": str(file_size)}
        return StreamingResponse(
            _file_chunk_iterator(file_path, 0, file_size - 1),
            status_code=status.HTTP_200_OK,
            media_type="video/mp4",
            headers=headers,
        )

    if not range_header.startswith("bytes="):
        raise HTTPException(
            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            detail="Invalid Range header.",
        )

    range_spec = range_header.replace("bytes=", "", 1).split(",")[0].strip()
    start_str, _, end_str = range_spec.partition("-")
    try:
        start = int(start_str) if start_str else 0
        end = int(end_str) if end_str else file_size - 1
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            detail="Malformed Range header.",
        ) from exc

    if start < 0 or end >= file_size or start > end:
        raise HTTPException(
            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            detail="Requested byte range out of bounds.",
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    content_length = end - start + 1
    headers = {
        **base_headers,
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Content-Length": str(content_length),
    }
    return StreamingResponse(
        _file_chunk_iterator(file_path, start, end),
        status_code=status.HTTP_206_PARTIAL_CONTENT,
        media_type="video/mp4",
        headers=headers,
    )
