"""FFmpeg HLS conversion service package.

Public API
----------
- :class:`HLSConverter` — main entry point for converting videos to adaptive HLS.
- :func:`validate_video_file` — standalone magic-byte video validator.
- :class:`Rendition` — named tuple defining a quality tier.
- Exceptions: :class:`FFmpegServiceError`, :class:`InvalidVideoFileError`,
  :class:`FileNotFoundError`, :class:`FFmpegExecutionError`.
"""

from .command_builder import DEFAULT_RENDITIONS, Rendition
from .converter import HLSConverter
from .exceptions import (
    FFmpegExecutionError,
    FFmpegServiceError,
    FileNotFoundError,
    InvalidVideoFileError,
)
from .validator import validate_video_file

__all__ = [
    "HLSConverter",
    "validate_video_file",
    "Rendition",
    "DEFAULT_RENDITIONS",
    "FFmpegServiceError",
    "InvalidVideoFileError",
    "FileNotFoundError",
    "FFmpegExecutionError",
]
