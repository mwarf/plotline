"""
plotline.logging - Centralized logging configuration.

Provides a simple logging setup with optional verbose mode for debugging.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("plotline")


def configure_logging(verbose: bool = False) -> None:
    """Configure logging for the plotline package.

    Args:
        verbose: If True, enable DEBUG level logging; otherwise WARNING level
    """
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
    )
