"""Video files from frames: MP4 through the ffmpeg program, WebM through OpenCV.

MP4 (H.264) plays in every browser, slide tool and chat app, and needs ffmpeg on PATH;
it runs as a separate program with an argument list, never a shell string, and reads
frames from a pipe. WebM (VP9) needs only the OpenCV the painter already uses.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from types import TracebackType
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import numpy as np
    import numpy.typing as npt


class VideoError(RuntimeError):
    """A video that could not be written, with what to do about it."""


def ffmpeg() -> str | None:
    """The ffmpeg program on PATH, if there is one."""
    return shutil.which("ffmpeg")


class Mp4:
    """An H.264 MP4 written by ffmpeg; add BGR frames of one size in a `with` block."""

    def __init__(self, program: str, path: Path, width: int, height: int, fps: float) -> None:
        self.args = [
            program,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "bgr24",
            "-s",
            f"{width}x{height}",
            "-r",
            f"{fps:g}",
            "-i",
            "-",
            # H.264 in yuv420p needs even sides; pad an odd side by one pixel.
            "-vf",
            "pad=ceil(iw/2)*2:ceil(ih/2)*2",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "20",
            "-preset",
            "medium",
            "-movflags",
            "+faststart",
            str(path),
        ]
        self.path = path
        self.proc: subprocess.Popen[bytes] | None = None

    def __enter__(self) -> Mp4:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.proc = subprocess.Popen(  # noqa: S603  argv list, no shell; ffmpeg is the one on PATH
                self.args, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
            )
        except OSError as exc:
            raise VideoError(f"could not start ffmpeg: {exc.strerror}") from exc
        return self

    def add(self, frame: npt.NDArray[np.uint8]) -> None:
        if self.proc is None or self.proc.stdin is None:
            raise VideoError("add frames inside a with block")
        try:
            self.proc.stdin.write(frame.tobytes())
        except BrokenPipeError as exc:
            raise VideoError(f"ffmpeg stopped: {self._errors()}") from exc

    def __exit__(
        self,
        kind: type[BaseException] | None,
        exc: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        if self.proc is None:
            return
        if self.proc.stdin is not None:
            self.proc.stdin.close()
        code = self.proc.wait(timeout=600)
        if code != 0 and kind is None:
            raise VideoError(f"ffmpeg failed with code {code}: {self._errors()}")

    def _errors(self) -> str:
        if self.proc is None or self.proc.stderr is None:
            return ""
        return self.proc.stderr.read().decode("utf-8", "replace").strip()[-400:]


class Webm:
    """A VP9 WebM written by OpenCV; add BGR frames of one size in a `with` block."""

    def __init__(self, path: Path, width: int, height: int, fps: float) -> None:
        self.path = path
        self.size = (width, height)
        self.fps = fps
        self.writer: Any = None  # a cv2.VideoWriter; cv2 is imported only when writing

    def __enter__(self) -> Webm:
        import cv2  # imported here so text-only commands run without OpenCV installed

        self.path.parent.mkdir(parents=True, exist_ok=True)
        writer = cv2.VideoWriter(
            str(self.path), cv2.VideoWriter.fourcc(*"VP90"), self.fps, self.size
        )
        if not writer.isOpened():
            raise VideoError("this OpenCV build cannot write VP9 WebM; install ffmpeg for MP4")
        self.writer = writer
        return self

    def add(self, frame: npt.NDArray[np.uint8]) -> None:
        if self.writer is None:
            raise VideoError("add frames inside a with block")
        self.writer.write(frame)

    def __exit__(
        self,
        kind: type[BaseException] | None,
        exc: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        if self.writer is not None:
            self.writer.release()
            self.writer = None
