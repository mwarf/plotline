"""Tests for plotline.llm themes, synthesis, and arc modules."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock


def _make_mock_client(response_data: dict[str, Any]) -> MagicMock:
    """Create a mock LLM client that returns the given response data."""
    client = MagicMock()
    client.model = "test-model"
    client.complete.return_value = json.dumps(response_data)
    client.get_token_usage.return_value = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }
    return client


def _make_mock_template_manager() -> MagicMock:
    """Create a mock PromptTemplateManager."""
    tm = MagicMock()
    tm.format_transcript_for_prompt.return_value = "formatted transcript"
    tm.format_theme_map_for_prompt.return_value = "formatted themes"
    tm.format_synthesis_for_prompt.return_value = "formatted synthesis"
    tm.format_brief_for_prompt.return_value = "formatted brief"
    tm.render.return_value = "rendered prompt"
    return tm


def _make_mock_config() -> MagicMock:
    """Create a mock PlotlineConfig."""
    config = MagicMock()
    config.llm_model = "test-model"
    config.target_duration_seconds = 600
    config.project_profile = "documentary"
    config.cultural_flags = False
    return config


class TestThemesExtraction:
    def test_extract_themes_for_interview_empty_segments(self) -> None:
        from plotline.llm.themes import extract_themes_for_interview

        client = _make_mock_client({"themes": []})
        tm = _make_mock_template_manager()

        segments_data = {
            "interview_id": "interview_001",
            "segments": [],
        }

        result = extract_themes_for_interview(
            segments=segments_data,
            client=client,
            template_manager=tm,
        )

        assert result["themes"] == []

    def test_extract_themes_for_interview_calls_client(self) -> None:
        from plotline.llm.themes import extract_themes_for_interview

        response_data = {
            "themes": [
                {
                    "name": "Connection to Nature",
                    "description": "Theme about nature",
                    "segment_ids": ["interview_001_seg_001"],
                    "emotional_character": "peaceful",
                    "strength": 0.8,
                }
            ]
        }
        client = _make_mock_client(response_data)
        tm = _make_mock_template_manager()

        segments_data = {
            "interview_id": "interview_001",
            "segments": [{"segment_id": "interview_001_seg_001", "text": "Test segment"}],
        }

        result = extract_themes_for_interview(
            segments=segments_data,
            client=client,
            template_manager=tm,
        )

        assert len(result["themes"]) == 1
        assert result["themes"][0]["name"] == "Connection to Nature"
        client.complete.assert_called_once()

    def test_extract_themes_all_interviews_skips_done(self, tmp_project: Path) -> None:
        from plotline.llm.themes import extract_themes_all_interviews

        client = _make_mock_client({"themes": []})
        tm = _make_mock_template_manager()
        config = _make_mock_config()

        manifest = {
            "interviews": [
                {"id": "interview_001", "stages": {"themes": True}},
            ]
        }

        result = extract_themes_all_interviews(
            project_path=tmp_project,
            manifest=manifest,
            client=client,
            template_manager=tm,
            config=config,
            force=False,
        )

        assert result["extracted"] == 0
        assert result["failed"] == 0

    def test_extract_themes_force_reruns(self, tmp_project: Path) -> None:
        from plotline.llm.themes import extract_themes_all_interviews

        client = _make_mock_client({"themes": []})
        tm = _make_mock_template_manager()
        config = _make_mock_config()

        seg_path = tmp_project / "data" / "segments" / "interview_001.json"
        seg_path.parent.mkdir(parents=True, exist_ok=True)
        seg_path.write_text(
            json.dumps(
                {
                    "interview_id": "interview_001",
                    "segments": [{"segment_id": "interview_001_seg_001"}],
                }
            )
        )

        theme_path = tmp_project / "data" / "themes" / "interview_001.json"
        theme_path.parent.mkdir(parents=True, exist_ok=True)

        manifest = {
            "interviews": [
                {"id": "interview_001", "stages": {"themes": True, "enriched": True}},
            ]
        }

        result = extract_themes_all_interviews(
            project_path=tmp_project,
            manifest=manifest,
            client=client,
            template_manager=tm,
            config=config,
            force=True,
        )

        assert result["extracted"] == 1


class TestSynthesis:
    def test_synthesize_themes_empty(self) -> None:
        from plotline.llm.synthesis import synthesize_themes

        client = _make_mock_client({"unified_themes": [], "best_takes": []})
        tm = _make_mock_template_manager()

        result = synthesize_themes(
            themes_data=[],
            client=client,
            template_manager=tm,
            interview_count=0,
        )

        assert result["unified_themes"] == []

    def test_synthesize_themes_with_brief(self) -> None:
        from plotline.llm.synthesis import synthesize_themes

        response_data = {
            "unified_themes": [
                {
                    "unified_theme_id": "utheme_001",
                    "name": "Test Theme",
                    "description": "A theme",
                    "source_themes": [],
                    "all_segment_ids": [],
                }
            ],
            "best_takes": [],
        }
        client = _make_mock_client(response_data)
        tm = _make_mock_template_manager()

        themes_data = [
            {
                "interview_id": "interview_001",
                "themes": [{"theme_id": "theme_001", "name": "Test Theme"}],
            }
        ]
        brief = {"key_messages": [{"id": "msg_001", "text": "Test message"}]}

        result = synthesize_themes(
            themes_data=themes_data,
            client=client,
            template_manager=tm,
            interview_count=1,
            brief=brief,
        )

        assert len(result["unified_themes"]) == 1
        tm.render.assert_called_once()


class TestArcConstruction:
    def test_build_narrative_arc_empty(self) -> None:
        from plotline.llm.arc import build_narrative_arc

        client = _make_mock_client({"arc": []})
        tm = _make_mock_template_manager()
        config = _make_mock_config()

        result = build_narrative_arc(
            synthesis={},
            all_segments=[],
            client=client,
            template_manager=tm,
            config=config,
        )

        assert result["arc"] == []

    def test_build_narrative_arc_selects_segments(self) -> None:
        from plotline.llm.arc import build_narrative_arc

        response_data = {
            "target_duration_seconds": 600,
            "estimated_duration_seconds": 120,
            "narrative_mode": "emergent",
            "arc": [
                {
                    "position": 1,
                    "segment_id": "interview_001_seg_001",
                    "interview_id": "interview_001",
                    "role": "opening",
                    "themes": ["utheme_001"],
                    "editorial_notes": "Great opener",
                    "pacing": "Let it breathe",
                }
            ],
        }
        client = _make_mock_client(response_data)
        tm = _make_mock_template_manager()
        config = _make_mock_config()

        synthesis = {
            "unified_themes": [
                {
                    "unified_theme_id": "utheme_001",
                    "name": "Test Theme",
                    "all_segment_ids": ["interview_001_seg_001"],
                }
            ]
        }
        all_segments = [
            {
                "segment_id": "interview_001_seg_001",
                "interview_id": "interview_001",
                "text": "Test segment",
                "start": 0.0,
                "end": 30.0,
                "delivery": {
                    "composite_score": 0.75,
                    "delivery_label": "High energy",
                },
            }
        ]

        result = build_narrative_arc(
            synthesis=synthesis,
            all_segments=all_segments,
            client=client,
            template_manager=tm,
            config=config,
        )

        assert len(result["arc"]) == 1
        assert result["arc"][0]["segment_id"] == "interview_001_seg_001"

    def test_create_selections_from_arc(self) -> None:
        from plotline.llm.arc import create_selections_from_arc

        arc_data = {
            "project_name": "test-project",
            "estimated_duration_seconds": 120,
            "arc": [
                {
                    "position": 1,
                    "segment_id": "interview_001_seg_001",
                    "interview_id": "interview_001",
                    "role": "opening",
                    "themes": ["utheme_001"],
                    "editorial_notes": "Great opener",
                    "pacing": "Let it breathe",
                }
            ],
        }
        all_segments = [
            {
                "segment_id": "interview_001_seg_001",
                "interview_id": "interview_001",
                "text": "Test segment",
                "start": 0.0,
                "end": 30.0,
                "delivery": {
                    "composite_score": 0.75,
                    "delivery_label": "High energy",
                },
            }
        ]

        result = create_selections_from_arc(
            arc=arc_data,
            all_segments=all_segments,
            project_name="test-project",
        )

        assert result["selection_count"] == 1
        assert len(result["segments"]) == 1
        assert result["segments"][0]["flagged"] is False


class TestFlagsPass:
    def test_run_flags_disabled_in_config(self, tmp_project: Path) -> None:
        from plotline.llm.flags import run_flags

        client = _make_mock_client({"flags": []})
        tm = _make_mock_template_manager()
        config = MagicMock()
        config.cultural_flags = False

        result = run_flags(
            project_path=tmp_project,
            manifest={},
            client=client,
            template_manager=tm,
            config=config,
            force=False,
        )

        assert result["skipped"] is True
        client.complete.assert_not_called()

    def test_run_flags_force_overrides_config(self, tmp_project: Path) -> None:
        from plotline.llm.flags import run_flags

        client = _make_mock_client({"flags": []})
        tm = _make_mock_template_manager()
        config = MagicMock()
        config.cultural_flags = False

        seg_path = tmp_project / "data" / "selections.json"
        seg_path.parent.mkdir(parents=True, exist_ok=True)
        seg_path.write_text(json.dumps({"segments": [{"segment_id": "seg_001"}]}))

        result = run_flags(
            project_path=tmp_project,
            manifest={},
            client=client,
            template_manager=tm,
            config=config,
            force=True,
        )

        assert result["skipped"] is False
        client.complete.assert_called_once()
