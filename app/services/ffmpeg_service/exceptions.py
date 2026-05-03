"""Custom exceptions for the FFmpeg / HLS conversion pipeline."""


class FFmpegServiceError(Exception):
    """Base exception for all FFmpeg service errors."""


class InvalidVideoFileError(FFmpegServiceError):
    """Raised when the input file is not a valid video container."""

    def __init__(self, path: str, reason: str = ""):
        self.path = path
        self.reason = reason
        detail = f": {reason}" if reason else ""
        super().__init__(f"Invalid video file '{path}'{detail}")


class FileNotFoundError(FFmpegServiceError):
    """Raised when the input file does not exist on disk."""

    def __init__(self, path: str):
        self.path = path
        super().__init__(f"File not found: '{path}'")


class FFmpegExecutionError(FFmpegServiceError):
    """Raised when the ffmpeg subprocess exits with a non-zero code."""

    def __init__(self, returncode: int, stderr: str = ""):
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(
            f"FFmpeg exited with code {returncode}"
            + (f"\n{stderr}" if stderr else "")
        )
