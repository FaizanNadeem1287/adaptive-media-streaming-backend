"""Centralised logging configuration for the HLS streaming application.

Call :func:`setup_logging` once at application startup (main.py, worker.py,
or at the top of a test script) to activate formatted console + optional
file logging across the entire ``app.*`` namespace.
"""

import logging
import os
import sys
from datetime import datetime, timezone


# ── ANSI colour codes (stripped automatically when not a TTY) ────────────
_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"

_LEVEL_COLOURS: dict[int, str] = {
    logging.DEBUG:    "\033[36m",     # cyan
    logging.INFO:     "\033[32m",     # green
    logging.WARNING:  "\033[33m",     # yellow
    logging.ERROR:    "\033[31m",     # red
    logging.CRITICAL: "\033[1;31m",   # bold red
}


class _ColourFormatter(logging.Formatter):
    """A log formatter that adds ANSI colours when writing to a terminal."""

    FMT = (
        "{dim}%(asctime)s{reset}  "
        "{level_colour}{bold}%(levelname)-8s{reset}  "
        "{dim}%(name)s{reset}  "
        "%(message)s"
    )
    DATE_FMT = "%Y-%m-%d %H:%M:%S"

    def __init__(self, *, use_colour: bool = True):
        self._use_colour = use_colour
        super().__init__(datefmt=self.DATE_FMT)

    def format(self, record: logging.LogRecord) -> str:
        if self._use_colour:
            level_colour = _LEVEL_COLOURS.get(record.levelno, "")
            fmt = self.FMT.format(
                dim=_DIM, bold=_BOLD, reset=_RESET, level_colour=level_colour,
            )
        else:
            fmt = "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"

        formatter = logging.Formatter(fmt, datefmt=self.DATE_FMT)
        return formatter.format(record)


def setup_logging(
    *,
    level: int | str = logging.INFO,
    log_dir: str | None = None,
) -> None:
    """Configure logging for the whole application.

    Parameters
    ----------
    level : int | str
        Minimum log level (``DEBUG``, ``INFO``, …).
        Can also be set via the ``LOG_LEVEL`` environment variable.
    log_dir : str | None
        If given, a rotating log file is written under this directory.
        Can also be set via the ``LOG_DIR`` environment variable.
    """
    # Allow env-var overrides
    env_level = os.getenv("LOG_LEVEL", "").upper()
    if env_level:
        level = getattr(logging, env_level, level)

    log_dir = log_dir or os.getenv("LOG_DIR")

    # ── Root "app" logger (captures all app.* children) ──────────────
    root_logger = logging.getLogger("app")
    root_logger.setLevel(level)

    # Avoid duplicate handlers if called more than once
    if root_logger.handlers:
        return

    # ── Console handler ──────────────────────────────────────────────
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(level)
    console.setFormatter(_ColourFormatter(use_colour=sys.stderr.isatty()))
    root_logger.addHandler(console)

    # ── File handler (optional) ──────────────────────────────────────
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        file_path = os.path.join(log_dir, f"hls-{today}.log")

        file_handler = logging.FileHandler(file_path, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(_ColourFormatter(use_colour=False))
        root_logger.addHandler(file_handler)

        root_logger.info("File logging enabled → %s", file_path)

    root_logger.debug("Logging initialised at %s level", logging.getLevelName(level))
