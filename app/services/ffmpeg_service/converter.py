"""High-level HLS converter — orchestrates validation, command building, and execution."""

import logging
import os
import subprocess
import time
import uuid

from .command_builder import DEFAULT_RENDITIONS, Rendition, build_hls_command
from .exceptions import FFmpegExecutionError, FFmpegServiceError
from .validator import validate_video_file

logger = logging.getLogger(__name__)


class HLSConverter:
    """Validates a source video and converts it to adaptive multi-bitrate HLS.

    Parameters
    ----------
    output_dir : str
        Root directory under which ``<video_id>/`` folders will be created.
    renditions : list[Rendition] | None
        Custom quality tiers.  Defaults to 360p / 720p / 1080p.
    """

    def __init__(
        self,
        output_dir: str,
        renditions: list[Rendition] | None = None,
    ):
        self.output_dir = output_dir
        self.renditions = renditions or DEFAULT_RENDITIONS
        logger.debug(
            "HLSConverter initialised — output_dir=%s, renditions=%s",
            output_dir,
            [r.name for r in self.renditions],
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def convert(self, input_path: str) -> dict:
        """Run the full pipeline: validate → transcode → return metadata.

        Returns
        -------
        dict
            ``{"video_id": ..., "format": ..., "master_playlist": ...}``

        Raises
        ------
        FileNotFoundError
            Input file missing.
        InvalidVideoFileError
            Input file is not a recognised video container.
        FFmpegExecutionError
            FFmpeg process returned a non-zero exit code.
        FFmpegServiceError
            Any other unexpected error during conversion.
        """
        pipeline_start = time.monotonic()
        logger.info("━━━ Starting HLS conversion for: %s ━━━", input_path)

        # 1. Validate input ------------------------------------------------
        logger.info("[1/3] Validating input file …")
        detected_format = validate_video_file(input_path)

        # 2. Prepare output dirs -------------------------------------------
        logger.info("[2/3] Preparing output directories …")
        video_id = uuid.uuid4().hex[:16]
        base_dir = os.path.join(self.output_dir, video_id)
        os.makedirs(base_dir, exist_ok=True)

        for r in self.renditions:
            rendition_dir = os.path.join(base_dir, r.name)
            os.makedirs(rendition_dir, exist_ok=True)
            logger.debug("  Created: %s", rendition_dir)

        # 3. Build & run FFmpeg command ------------------------------------
        logger.info("[3/3] Transcoding %d renditions …", len(self.renditions))
        cmd = build_hls_command(
            input_path=input_path,
            output_dir=base_dir,
            renditions=self.renditions,
        )
        logger.debug("FFmpeg command:\n  %s", " \\\n    ".join(cmd))

        transcode_start = time.monotonic()

        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )
            transcode_elapsed = time.monotonic() - transcode_start
            logger.info(
                "FFmpeg finished in %.1fs", transcode_elapsed,
            )
            logger.debug("FFmpeg stderr:\n%s", result.stderr[-2000:] if result.stderr else "(empty)")

        except subprocess.CalledProcessError as exc:
            transcode_elapsed = time.monotonic() - transcode_start
            logger.error(
                "FFmpeg failed after %.1fs (exit code %d)",
                transcode_elapsed,
                exc.returncode,
            )
            logger.error("FFmpeg stderr:\n%s", exc.stderr[-3000:] if exc.stderr else "(empty)")
            raise FFmpegExecutionError(
                returncode=exc.returncode,
                stderr=exc.stderr or "",
            ) from exc

        except OSError as exc:
            logger.critical("Could not launch ffmpeg binary: %s", exc)
            raise FFmpegServiceError(
                f"Could not launch ffmpeg: {exc}"
            ) from exc

        # 4. Log summary & return metadata ---------------------------------
        total_elapsed = time.monotonic() - pipeline_start
        segment_count = sum(
            1 for r in self.renditions
            for f in os.listdir(os.path.join(base_dir, r.name))
            if f.endswith(".ts")
        )
        logger.info(
            "✔ Conversion complete — video_id=%s, format=%s, "
            "segments=%d, duration=%.1fs",
            video_id, detected_format, segment_count, total_elapsed,
        )

        return {
            "video_id": video_id,
            "format": detected_format,
            "master_playlist": f"{video_id}/master.m3u8",
        }
