"""Build the FFmpeg command list for adaptive HLS transcoding."""

import os
from typing import NamedTuple


class Rendition(NamedTuple):
    """A single HLS rendition (quality tier)."""
    name: str       # e.g. "360p"
    scale: str      # e.g. "640:360"
    bitrate: str    # e.g. "800k"


# Default adaptive renditions — extend or override via the converter.
DEFAULT_RENDITIONS: list[Rendition] = [
    Rendition("360p",  "640:360",   "800k"),
    Rendition("720p",  "1280:720",  "2500k"),
    Rendition("1080p", "1920:1080", "5000k"),
]


def build_hls_command(
    input_path: str,
    output_dir: str,
    renditions: list[Rendition] | None = None,
    *,
    hls_time: int = 4,
    preset: str = "fast",
    audio_bitrate: str = "128k",
    audio_sample_rate: int = 44100,
) -> list[str]:
    """Return the full ``ffmpeg`` argument list for multi-bitrate HLS output.

    Parameters
    ----------
    input_path : str
        Path to the source video file.
    output_dir : str
        Directory where ``master.m3u8`` and per-rendition folders are written.
    renditions : list[Rendition] | None
        Quality tiers.  Falls back to :data:`DEFAULT_RENDITIONS`.
    hls_time : int
        Segment duration in seconds.
    preset : str
        libx264 encoding preset (ultrafast … veryslow).
    audio_bitrate : str
        AAC audio bitrate per variant.
    audio_sample_rate : int
        Audio sample rate in Hz.
    """
    if renditions is None:
        renditions = DEFAULT_RENDITIONS

    num = len(renditions)

    # --- filter_complex: split → scale per rendition ---
    split_labels = "".join(f"[v{i}]" for i in range(num))
    filter_parts = [f"[0:v]split={num}{split_labels}"]
    for i, r in enumerate(renditions):
        filter_parts.append(f"[v{i}]scale={r.scale}[v{i}out]")
    filter_complex = ";".join(filter_parts)

    cmd: list[str] = ["ffmpeg", "-y", "-i", input_path]
    cmd += ["-filter_complex", filter_complex]

    # --- Map each scaled video stream + a copy of audio for each ---
    for i in range(num):
        cmd += ["-map", f"[v{i}out]"]
    for _ in range(num):
        cmd += ["-map", "0:a"]

    # --- Per-stream encoding settings ---
    for i, r in enumerate(renditions):
        cmd += [f"-b:v:{i}", r.bitrate]

    cmd += [
        "-c:v", "libx264",
        "-preset", preset,
        "-c:a", "aac",
        "-b:a", audio_bitrate,
        "-ar", str(audio_sample_rate),
    ]

    # --- var_stream_map: name variants by resolution ---
    stream_map = " ".join(
        f"v:{i},a:{i},name:{r.name}" for i, r in enumerate(renditions)
    )

    cmd += [
        "-f", "hls",
        "-hls_time", str(hls_time),
        "-hls_playlist_type", "vod",
        "-hls_flags", "independent_segments",
        "-master_pl_name", "master.m3u8",
        "-var_stream_map", stream_map,
        "-hls_segment_filename", os.path.join(output_dir, "%v", "segment_%03d.ts"),
        os.path.join(output_dir, "%v", "prog_index.m3u8"),
    ]

    return cmd
