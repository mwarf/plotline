"""Tests for plotline.llm.flags module — cultural sensitivity flagging."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from plotline.llm.flags import flag_segments, run_flags

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_client(flags_response: list[dict[str, Any]]) -> MagicMock:
    """Return a mock LLM client whose complete() returns a flags JSON blob."""
    client = MagicMock()
    client.model = "test-model"
    client.complete.return_value = json.dumps({"flags": flags_response})
    return client


def _make_mock_template_manager() -> MagicMock:
    """Return a mock PromptTemplateManager."""
    tm = MagicMock()
    tm.format_transcript_for_prompt.return_value = "formatted transcript text"
    tm.render.return_value = "rendered prompt text"
    return tm


def _make_segments(n: int = 3) -> list[dict[str, Any]]:
    """Create *n* minimal enriched segments."""
    return [
        {
            "segment_id": f"iv_001_seg_{i:03d}",
            "start": float(i * 10),
            "end": float(i * 10 + 8),
            "text": f"Segment {i} text content here.",
        }
        for i in range(1, n + 1)
    ]


def _make_config(cultural_flags: bool = True) -> MagicMock:
    cfg = MagicMock()
    cfg.cultural_flags = cultural_flags
    return cfg


def _write_selections(project: Path, segments: list[dict[str, Any]]) -> Path:
    """Write a selections.json under project/data/ and return path."""
    sel_path = project / "data" / "selections.json"
    sel_path.parent.mkdir(parents=True, exist_ok=True)
    with open(sel_path, "w") as f:
        json.dump({"segments": segments}, f)
    return sel_path


# ---------------------------------------------------------------------------
# flag_segments (unit)
# ---------------------------------------------------------------------------


class TestFlagSegments:
    def test_empty_segments_returns_empty(self) -> None:
        result = flag_segments([], MagicMock(), MagicMock())
        assert result == {"flags": []}

    def test_calls_client_with_rendered_prompt(self) -> None:
        segments = _make_segments(2)
        client = _make_mock_client([])
        tm = _make_mock_template_manager()

        flag_segments(segments, client, tm)

        tm.format_transcript_for_prompt.assert_called_once_with(segments)
        tm.render.assert_called_once_with("flags.txt", {"TRANSCRIPT": "formatted transcript text"})
        client.complete.assert_called_once()
        call_args = client.complete.call_args
        assert call_args[0][0] == "rendered prompt text"

    def test_returns_validated_flags(self) -> None:
        flags_data = [
            {
                "segment_id": "iv_001_seg_001",
                "reason": "References sacred ceremony",
                "review_type": "cultural_advisor",
                "severity": "review_recommended",
            }
        ]
        client = _make_mock_client(flags_data)
        tm = _make_mock_template_manager()

        result = flag_segments(_make_segments(1), client, tm)

        assert len(result["flags"]) == 1
        assert result["flags"][0]["segment_id"] == "iv_001_seg_001"
        assert result["flags"][0]["reason"] == "References sacred ceremony"

    def test_multiple_flags_returned(self) -> None:
        flags_data = [
            {"segment_id": "iv_001_seg_001", "reason": "Reason A"},
            {"segment_id": "iv_001_seg_002", "reason": "Reason B"},
        ]
        client = _make_mock_client(flags_data)
        tm = _make_mock_template_manager()

        result = flag_segments(_make_segments(2), client, tm)
        assert len(result["flags"]) == 2

    def test_console_output_when_provided(self) -> None:
        console = MagicMock()
        client = _make_mock_client([])
        tm = _make_mock_template_manager()

        flag_segments(_make_segments(1), client, tm, console=console)
        console.print.assert_called()


# ---------------------------------------------------------------------------
# run_flags (integration-like, with filesystem)
# ---------------------------------------------------------------------------


class TestRunFlags:
    def test_skips_when_config_disabled(self, tmp_project: Path) -> None:
        config = _make_config(cultural_flags=False)
        client = _make_mock_client([])
        tm = _make_mock_template_manager()

        result = run_flags(tmp_project, {}, client, tm, config)

        assert result["skipped"] is True
        assert result["flagged"] == 0
        assert "disabled" in result["reason"].lower()
        client.complete.assert_not_called()

    def test_force_overrides_disabled_config(self, tmp_project: Path) -> None:
        """force=True should run even when cultural_flags is False."""
        segments = _make_segments(2)
        _write_selections(tmp_project, segments)

        config = _make_config(cultural_flags=False)
        client = _make_mock_client([])
        tm = _make_mock_template_manager()

        result = run_flags(tmp_project, {}, client, tm, config, force=True)

        assert result["skipped"] is False
        client.complete.assert_called_once()

    def test_missing_selections_raises(self, tmp_project: Path) -> None:
        """Should raise FileNotFoundError if selections.json doesn't exist."""
        config = _make_config(cultural_flags=True)

        # Ensure file does NOT exist
        sel_path = tmp_project / "data" / "selections.json"
        if sel_path.exists():
            sel_path.unlink()

        with pytest.raises(FileNotFoundError, match="selections"):
            run_flags(tmp_project, {}, MagicMock(), MagicMock(), config)

    def test_empty_segments_no_llm_call(self, tmp_project: Path) -> None:
        """Empty segments list should short-circuit without calling LLM."""
        _write_selections(tmp_project, [])
        config = _make_config(cultural_flags=True)
        client = _make_mock_client([])
        tm = _make_mock_template_manager()

        result = run_flags(tmp_project, {}, client, tm, config)

        assert result["flagged"] == 0
        assert result["reason"] == "No segments to flag"
        client.complete.assert_not_called()

    def test_updates_selections_in_place(self, tmp_project: Path) -> None:
        """Flagged segments should have flagged=True and flag_reason set."""
        segments = _make_segments(3)
        sel_path = _write_selections(tmp_project, segments)

        flags_data = [
            {
                "segment_id": "iv_001_seg_002",
                "reason": "Sacred site reference",
                "review_type": "cultural_advisor",
                "severity": "review_recommended",
            }
        ]
        config = _make_config(cultural_flags=True)
        client = _make_mock_client(flags_data)
        tm = _make_mock_template_manager()

        result = run_flags(tmp_project, {}, client, tm, config)

        assert result["flagged"] == 1
        assert result["total_segments"] == 3

        # Re-read the file to verify in-place update
        with open(sel_path) as f:
            updated = json.load(f)

        segs = {s["segment_id"]: s for s in updated["segments"]}
        assert segs["iv_001_seg_001"]["flagged"] is False
        assert segs["iv_001_seg_001"]["flag_reason"] is None
        assert segs["iv_001_seg_002"]["flagged"] is True
        assert segs["iv_001_seg_002"]["flag_reason"] == "Sacred site reference"
        assert segs["iv_001_seg_003"]["flagged"] is False

        # Metadata stamps
        assert "flagged_at" in updated
        assert updated["flags_model"] == "test-model"

    def test_unknown_segment_ids_skipped(self, tmp_project: Path) -> None:
        """Flags referencing non-existent segment IDs are silently skipped."""
        segments = _make_segments(1)
        _write_selections(tmp_project, segments)

        flags_data = [
            {"segment_id": "iv_001_seg_001", "reason": "Valid flag"},
            {"segment_id": "nonexistent_seg_999", "reason": "Ghost segment"},
        ]
        config = _make_config(cultural_flags=True)
        client = _make_mock_client(flags_data)
        tm = _make_mock_template_manager()

        result = run_flags(tmp_project, {}, client, tm, config)

        # Only the valid flag should be counted
        assert result["flagged"] == 1

    def test_clean_slate_on_rerun(self, tmp_project: Path) -> None:
        """Re-running flags should reset all segments before re-flagging."""
        segments = _make_segments(2)
        # Pre-set a flag on segment 1
        segments[0]["flagged"] = True
        segments[0]["flag_reason"] = "Old reason"
        _write_selections(tmp_project, segments)

        # New run flags only segment 2
        flags_data = [
            {"segment_id": "iv_001_seg_002", "reason": "New flag"},
        ]
        config = _make_config(cultural_flags=True)
        client = _make_mock_client(flags_data)
        tm = _make_mock_template_manager()

        run_flags(tmp_project, {}, client, tm, config)

        with open(tmp_project / "data" / "selections.json") as f:
            updated = json.load(f)

        segs = {s["segment_id"]: s for s in updated["segments"]}
        # Segment 1 should have been reset
        assert segs["iv_001_seg_001"]["flagged"] is False
        assert segs["iv_001_seg_001"]["flag_reason"] is None
        # Segment 2 got the new flag
        assert segs["iv_001_seg_002"]["flagged"] is True
        assert segs["iv_001_seg_002"]["flag_reason"] == "New flag"

    def test_console_warnings_for_unknown_segments(self, tmp_project: Path) -> None:
        """Console should print a warning for unknown segment IDs."""
        segments = _make_segments(1)
        _write_selections(tmp_project, segments)

        flags_data = [
            {"segment_id": "nonexistent_seg_999", "reason": "Ghost"},
        ]
        config = _make_config(cultural_flags=True)
        client = _make_mock_client(flags_data)
        tm = _make_mock_template_manager()
        console = MagicMock()

        run_flags(tmp_project, {}, client, tm, config, console=console)

        # Should have printed a warning mentioning the unknown segment
        warning_calls = [
            str(c) for c in console.print.call_args_list if "nonexistent_seg_999" in str(c)
        ]
        assert len(warning_calls) >= 1

    def test_all_segments_flagged(self, tmp_project: Path) -> None:
        """All segments can be flagged at once."""
        segments = _make_segments(3)
        _write_selections(tmp_project, segments)

        flags_data = [
            {"segment_id": f"iv_001_seg_{i:03d}", "reason": f"Reason {i}"} for i in range(1, 4)
        ]
        config = _make_config(cultural_flags=True)
        client = _make_mock_client(flags_data)
        tm = _make_mock_template_manager()

        result = run_flags(tmp_project, {}, client, tm, config)

        assert result["flagged"] == 3
        assert result["total_segments"] == 3

    def test_no_flags_returned(self, tmp_project: Path) -> None:
        """When LLM returns no flags, all segments remain unflagged."""
        segments = _make_segments(2)
        _write_selections(tmp_project, segments)

        config = _make_config(cultural_flags=True)
        client = _make_mock_client([])
        tm = _make_mock_template_manager()

        result = run_flags(tmp_project, {}, client, tm, config)

        assert result["flagged"] == 0
        assert result["total_segments"] == 2

        with open(tmp_project / "data" / "selections.json") as f:
            updated = json.load(f)

        for seg in updated["segments"]:
            assert seg["flagged"] is False
            assert seg["flag_reason"] is None
