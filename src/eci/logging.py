"""Centralized logging for the ECI Framework.

Usage:
    from eci.logging import configure_logging, get_logger
    configure_logging(level="INFO")
    log = get_logger("eci.consciousness")
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

__all__ = ["configure_logging", "get_logger", "set_level"]

_FMT = "%(asctime)s | %(levelname)-7s | %(name)-28s | %(message)s"
_configured = False


def configure_logging(
    level: str | int = "INFO",
    log_file: Optional[Path | str] = None,
    log_dir: Optional[Path | str] = None,
    quiet_third_party: bool = True,
) -> None:
    """Configure the root ``eci`` logging namespace exactly once per process."""
    global _configured
    root = logging.getLogger("eci")
    if _configured and root.handlers:
        set_level(level)
        return

    resolved = logging.getLevelName(level) if isinstance(level, str) else level
    if not isinstance(resolved, int):
        resolved = logging.INFO

    handler: logging.Handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(_FMT))
    root.addHandler(handler)
    root.setLevel(resolved)
    root.propagate = False

    if log_dir is not None:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "eci_session.log"
    if log_file is not None:
        fh = logging.FileHandler(str(log_file), encoding="utf-8")
        fh.setFormatter(logging.Formatter(_FMT))
        root.addHandler(fh)

    if quiet_third_party:
        for noisy in ("matplotlib", "PIL", "urllib3"):
            logging.getLogger(noisy).setLevel(logging.WARNING)

    _configured = True


def set_level(level: str | int) -> None:
    root = logging.getLogger("eci")
    resolved = logging.getLevelName(level) if isinstance(level, str) else level
    if isinstance(resolved, int):
        root.setLevel(resolved)


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger; auto-configures with defaults if needed."""
    if not name.startswith("eci"):
        name = f"eci.{name}"
    if not _configured and not logging.getLogger("eci").handlers:
        configure_logging()
    return logging.getLogger(name)
