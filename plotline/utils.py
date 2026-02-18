"""
plotline.utils - Shared utility functions.

Contains common functions used across multiple modules to avoid duplication.
"""

from __future__ import annotations


def format_duration(seconds: float) -> str:
    """Format seconds as HH:MM:SS or MM:SS.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string (HH:MM:SS if >= 1 hour, otherwise MM:SS)
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def get_delivery_class(score: float) -> str:
    """Get CSS class for delivery score badge.

    Args:
        score: Delivery score (0.0 to 1.0)

    Returns:
        CSS class name: "filled" (high), "medium", or "low"
    """
    if score >= 0.7:
        return "filled"
    elif score >= 0.4:
        return "medium"
    return "low"
