import json
import logging
import os
import shutil
import subprocess
import uuid

logger = logging.getLogger(__name__)


# ──────────────────────── Custom Exceptions ────────────────────────
class VideoValidationError(Exception):
    """Raised when the input file is not a valid video."""
    pass


class FFmpegError(Exception):
    """Raised when FFmpeg exits with a non-zero return code."""
    pass


# ──────────────────── Magic-byte signatures ────────────────────────
# Each entry: (offset, magic_bytes, label)
# Reference: https://en.wikipedia.org/wiki/List_of_file_signatures
_VIDEO_SIGNATURES: list[tuple[int, bytes, str]] = [
    # ISO Base Media (MP4, M4V, MOV, 3GP, etc.) — ftyp box
    (4, b"ftyp", "ISO Base Media (mp4/mov/m4v/3gp)"),
    # Matroska / WebM
    (0, b"\x1a\x45\xdf\xa3", "Matroska/WebM (mkv/webm)"),
    # AVI (RIFF....AVI )
    (0, b"RIFF", "AVI"),
    # FLV
    (0, b"FLV", "Flash Video (flv)"),
    # MPEG Transport Stream
    (0, b"\x47", "MPEG-TS"),
    # MPEG Program Stream / MPEG-1/2
    (0, b"\x00\x00\x01\xba", "MPEG-PS"),
    (0, b"\x00\x00\x01\xb3", "MPEG-1/2 Video"),
    # WMV / ASF
    (0, b"\x30\x26\xb2\x75\x8e\x66\xcf\x11", "ASF/WMV"),
    # OGG (may contain Theora video)
    (0, b"OggS", "Ogg container"),
]


def _is_video_by_magic(path: str) -> tuple[bool, str]:
    """
    Read the first 12 bytes and compare against known video magic bytes.
    Returns (is_valid, description).
    """
    try:
        with open(path, "rb") as f:
            header = f.read(12)
    except OSError as exc:
        return False, f"Cannot read file: {exc}"

    if len(header) < 4:
        return False, "File too small to be a video"

    for offset, magic, label in _VIDEO_SIGNATURES:
        end = offset + len(magic)
        if end <= len(header) and header[offset:end] == magic:
            # Extra check: AVI needs "AVI " at offset 8
            if magic == b"RIFF":
                if len(header) >= 12 and header[8:12] == b"AVI ":
                    return True, label
                continue  # RIFF but not AVI — could be WAV, skip
            # Extra check: MPEG-TS single sync byte is weak — verify
            # a second sync byte at offset 188 if file is large enough
            if magic == b"\x47":
                try:
                    with open(path, "rb") as f:
                        f.seek(188)
                        second = f.read(1)
                    if second == b"\x47":
                        return True, label
                except OSError:
                    pass
                continue
            return True, label

    return False, "Unrecognised file signature"


def _probe_has_video_stream(path: str) -> tuple[bool, str]:
    """
    Use ffprobe as a secondary check to confirm the file contains
    at least one video stream. Catches edge cases magic bytes miss.
    """
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-select_streams", "v",
                "-show_entries", "stream=codec_type",
                "-of", "json",
                path,
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return False, f"ffprobe failed: {result.stderr.strip()}"
        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        if not streams:
            return False, "No video stream found by ffprobe"
        return True, f"{len(streams)} video stream(s) detected"
    except FileNotFoundError:
        return False, "ffprobe not installed"
    except subprocess.TimeoutExpired:
        return False, "ffprobe timed out"
    except (json.JSONDecodeError, KeyError) as exc:
        return False, f"ffprobe output parse error: {exc}"


# ──────────────────────── Service ──────────────────────────────────
class FFmpegService:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir

    # ── public API ──────────────────────────────────────────────────
    def convert_to_hls(self, input_path: str) -> dict:
        """
        Validate the input video, then transcode into multi-bitrate HLS.

        Raises:
            FileNotFoundError       – input file does not exist
            VideoValidationError    – input is not a valid video
            FFmpegError             – FFmpeg returned a non-zero exit code
        """
        # 1. File existence
        if not os.path.isfile(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        # 2. Magic-byte validation
        valid, reason = _is_video_by_magic(input_path)
        if not valid:
            raise VideoValidationError(
                f"File failed magic-byte validation: {reason} — {input_path}"
            )
        logger.info("Magic-byte check passed (%s): %s", reason, input_path)

        # 3. ffprobe validation (confirms a real video stream exists)
        has_stream, probe_msg = _probe_has_video_stream(input_path)
        if not has_stream:
            raise VideoValidationError(
                f"File failed ffprobe validation: {probe_msg} — {input_path}"
            )
        logger.info("ffprobe check passed (%s): %s", probe_msg, input_path)

        # 4. Generate video ID & output dirs
        video_id = uuid.uuid4().hex[:16]
        base_dir = os.path.join(self.output_dir, video_id)

        renditions = [
            ("360p", "640:360", "800k"),
            ("720p", "1280:720", "2500k"),
            ("1080p", "1920:1080", "5000k"),
        ]

        # Create resolution folders before ffmpeg runs
        for name, _, _ in renditions:
            os.makedirs(os.path.join(base_dir, name), exist_ok=True)

        # 5. Build FFmpeg command
        cmd = self._build_ffmpeg_cmd(input_path, base_dir, renditions)

        # 6. Run FFmpeg
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                # Clean up partial output on failure
                self._cleanup(base_dir)
                raise FFmpegError(
                    f"FFmpeg exited with code {result.returncode}.\n"
                    f"stderr: {result.stderr[-2000:]}"  # last 2 kB of logs
                )
        except FileNotFoundError:
            self._cleanup(base_dir)
            raise FFmpegError(
                "FFmpeg binary not found. Make sure ffmpeg is installed and on PATH."
            )
        except subprocess.TimeoutExpired:
            self._cleanup(base_dir)
            raise FFmpegError("FFmpeg process timed out.")

        logger.info("HLS conversion complete: %s", video_id)

        return {
            "video_id": video_id,
            "master_playlist": f"{video_id}/master.m3u8",
        }

    # ── private helpers ─────────────────────────────────────────────
    @staticmethod
    def _build_ffmpeg_cmd(
        input_path: str,
        base_dir: str,
        renditions: list[tuple[str, str, str]],
    ) -> list[str]:
        num = len(renditions)

        # filter_complex
        split_labels = "".join(f"[v{i}]" for i in range(num))
        filter_parts = [f"[0:v]split={num}{split_labels}"]
        for i, (_, scale, _) in enumerate(renditions):
            filter_parts.append(f"[v{i}]scale={scale}[v{i}out]")
        filter_complex = ";".join(filter_parts)

        cmd = ["ffmpeg", "-y", "-i", input_path]
        cmd += ["-filter_complex", filter_complex]

        # Map each scaled video stream + a copy of the audio for each
        for i in range(num):
            cmd += ["-map", f"[v{i}out]"]
        for _ in range(num):
            cmd += ["-map", "0:a"]

        # Per-stream encoding settings
        for i, (_, _, bitrate) in enumerate(renditions):
            cmd += [f"-b:v:{i}", bitrate]

        cmd += [
            "-c:v", "libx264",
            "-preset", "fast",
            "-c:a", "aac",
            "-b:a", "128k",
            "-ar", "44100",
        ]

        # var_stream_map — gives each variant a human-readable name
        stream_map = " ".join(
            f"v:{i},a:{i},name:{name}"
            for i, (name, _, _) in enumerate(renditions)
        )

        cmd += [
            "-f", "hls",
            "-hls_time", "4",
            "-hls_playlist_type", "vod",
            "-hls_flags", "independent_segments",
            "-master_pl_name", "master.m3u8",
            "-var_stream_map", stream_map,
            "-hls_segment_filename", os.path.join(base_dir, "%v", "segment_%03d.ts"),
            os.path.join(base_dir, "%v", "prog_index.m3u8"),
        ]

        return cmd

    @staticmethod
    def _cleanup(base_dir: str) -> None:
        """Remove partially-written output directory on failure."""
        try:
            if os.path.isdir(base_dir):
                shutil.rmtree(base_dir)
                logger.warning("Cleaned up partial output: %s", base_dir)
        except OSError as exc:
            logger.error("Cleanup failed for %s: %s", base_dir, exc)