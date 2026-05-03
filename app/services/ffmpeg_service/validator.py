"""Validate that an input file is genuinely a video container using magic bytes."""

import logging
import os
from typing import NamedTuple

from .exceptions import FileNotFoundError, InvalidVideoFileError

logger = logging.getLogger(__name__)


class _MagicSignature(NamedTuple):
    """A magic-byte signature: offset into the file and the expected bytes."""
    offset: int
    magic: bytes
    label: str


# Signatures covering the most common video containers.
# Some formats (like MP4 / MOV) store their "ftyp" box at byte 4.
_SIGNATURES: list[_MagicSignature] = [
    # ISO base media (MP4 / M4V / MOV / 3GP)  — "ftyp" at offset 4
    _MagicSignature(offset=4, magic=b"ftyp", label="MP4/MOV/M4V"),
    # Matroska / WebM
    _MagicSignature(offset=0, magic=b"\x1a\x45\xdf\xa3", label="MKV/WebM"),
    # AVI  — "RIFF" header
    _MagicSignature(offset=0, magic=b"RIFF", label="AVI"),
    # FLV
    _MagicSignature(offset=0, magic=b"FLV", label="FLV"),
    # MPEG-TS (0x47 sync byte)
    _MagicSignature(offset=0, magic=b"\x47", label="MPEG-TS"),
    # MPEG-PS / MPEG-1/2
    _MagicSignature(offset=0, magic=b"\x00\x00\x01\xba", label="MPEG-PS"),
    _MagicSignature(offset=0, magic=b"\x00\x00\x01\xb3", label="MPEG-1/2"),
    # WMV / ASF
    _MagicSignature(
        offset=0,
        magic=b"\x30\x26\xb2\x75\x8e\x66\xcf\x11",
        label="WMV/ASF",
    ),
    # OGG (may contain Theora video)
    _MagicSignature(offset=0, magic=b"OggS", label="OGG"),
]

# We only need to read this many bytes from the head of the file.
_MAX_READ = max(s.offset + len(s.magic) for s in _SIGNATURES)


def validate_video_file(path: str) -> str:
    """Validate that *path* exists and is a recognised video container.

    Returns the detected format label (e.g. ``"MP4/MOV/M4V"``).

    Raises
    ------
    FileNotFoundError
        If the file does not exist or is not a regular file.
    InvalidVideoFileError
        If the magic bytes do not match any known video format.
    """
    logger.debug("Validating file: %s", path)

    if not os.path.isfile(path):
        logger.error("File not found: %s", path)
        raise FileNotFoundError(path)

    file_size = os.path.getsize(path)
    logger.debug("File size: %s bytes (%.2f MB)", file_size, file_size / (1024 * 1024))

    if file_size == 0:
        logger.error("File is empty: %s", path)
        raise InvalidVideoFileError(path, reason="file is empty (0 bytes)")

    with open(path, "rb") as fh:
        header = fh.read(_MAX_READ)

    if len(header) < _MAX_READ:
        logger.error("File too small to identify (%d bytes): %s", len(header), path)
        raise InvalidVideoFileError(
            path,
            reason=f"file too small ({len(header)} bytes) to identify format",
        )

    for sig in _SIGNATURES:
        start = sig.offset
        end = start + len(sig.magic)
        if header[start:end] == sig.magic:
            logger.info(
                "✔ Detected format: %s (matched at offset %d)",
                sig.label, sig.offset,
            )
            return sig.label

    logger.warning(
        "No known video signature matched for: %s (header bytes: %s)",
        path, header[:16].hex(),
    )
    raise InvalidVideoFileError(
        path,
        reason="magic bytes do not match any known video container format",
    )
