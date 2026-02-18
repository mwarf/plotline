"""Tests for plotline.utils module."""

from __future__ import annotations

from plotline.utils import format_duration, get_delivery_class


class TestFormatDuration:
    def test_seconds_only(self) -> None:
        assert format_duration(45.0) == "0:45"

    def test_minutes_and_seconds(self) -> None:
        assert format_duration(125.0) == "2:05"

    def test_hours_minutes_seconds(self) -> None:
        assert format_duration(3725.0) == "1:02:05"

    def test_exact_hour(self) -> None:
        assert format_duration(3600.0) == "1:00:00"

    def test_zero(self) -> None:
        assert format_duration(0.0) == "0:00"

    def test_large_duration(self) -> None:
        assert format_duration(7384.0) == "2:03:04"

    def test_float_seconds(self) -> None:
        assert format_duration(90.7) == "1:30"


class TestGetDeliveryClass:
    def test_high_score(self) -> None:
        assert get_delivery_class(0.85) == "filled"
        assert get_delivery_class(0.7) == "filled"
        assert get_delivery_class(1.0) == "filled"

    def test_medium_score(self) -> None:
        assert get_delivery_class(0.5) == "medium"
        assert get_delivery_class(0.4) == "medium"
        assert get_delivery_class(0.69) == "medium"

    def test_low_score(self) -> None:
        assert get_delivery_class(0.1) == "low"
        assert get_delivery_class(0.0) == "low"
        assert get_delivery_class(0.39) == "low"

    def test_boundary_at_07(self) -> None:
        assert get_delivery_class(0.7) == "filled"
        assert get_delivery_class(0.699) == "medium"

    def test_boundary_at_04(self) -> None:
        assert get_delivery_class(0.4) == "medium"
        assert get_delivery_class(0.399) == "low"
