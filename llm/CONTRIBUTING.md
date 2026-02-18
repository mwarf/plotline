# CONTRIBUTING.md — Development Conventions

## Branch Strategy

```
main              ← stable, tested, working pipeline
  └── dev         ← integration branch, all features merge here first
       ├── phase/0-scaffolding
       ├── phase/1-extract
       ├── phase/2-transcribe
       ├── phase/3-analyze
       ├── phase/4-enrich
       ├── phase/5-llm
       ├── phase/6-export
       ├── phase/7-reports
       ├── phase/8-brief
       └── phase/9-integration
```

- **One branch per build plan phase** — keeps PRs reviewable
- **Merge to `dev`** when the phase passes its acceptance criteria
- **Merge `dev` to `main`** at milestones (after Phase 6 = working CLI, after Phase 9 = full V1)
- **Hotfix branches** (`fix/description`) branch from and merge to `dev`

## Commit Messages

```
[phase.task] Short description

phase/task maps to the build plan:
  [0.1] Repo setup and package structure
  [2.1] Whisper transcription engine
  [6.1] EDL generator

Examples:
  [0.2] Add config loading with profile merge logic
  [3.1] Implement per-segment librosa feature extraction
  [6.1] Fix drop-frame timecode calculation for 29.97fps
  [7.3] Add keyboard shortcuts to review report
```

Keep the first line under 72 characters. Add a body if the change is non-obvious.

## Testing

### Structure

```
tests/
├── conftest.py              # Shared fixtures (sample configs, project dirs, audio)
├── fixtures/
│   ├── sample_config.yaml
│   ├── sample_transcript.json
│   ├── sample_delivery.json
│   ├── sample_segments.json
│   ├── sample_themes.json
│   ├── sample_selections.json
│   └── test_audio_5s.wav    # 5-second speech clip for fast tests
├── test_config.py
├── test_project.py
├── test_extract.py
├── test_transcribe.py
├── test_analyze.py
├── test_enrich.py
├── test_llm.py
├── test_export.py
├── test_reports.py
└── test_cli.py              # End-to-end CLI integration tests
```

### What to Test

**Every task in the build plan has acceptance criteria — write tests that verify those criteria.**

For each pipeline stage module:
1. **Schema tests** — verify output JSON matches the schema in ARCHITECTURE.md
2. **Happy path** — valid input produces expected output
3. **Edge cases** — empty input, very short segments, very long segments, missing fields
4. **Round-trip** — write output, read it back, verify integrity

For the CLI:
1. **Command smoke tests** — each subcommand runs without error on valid input
2. **Flag handling** — `--model`, `--format`, `--profile` flags work correctly
3. **Error messages** — invalid input produces helpful errors, not tracebacks

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=plotline --cov-report=term-missing

# Run a specific phase's tests
pytest tests/test_export.py -v

# Run only fast tests (skip tests that need real audio or LLM)
pytest tests/ -m "not slow"
```

### Marking Slow Tests

Tests that need real audio processing or LLM calls should be marked:

```python
import pytest

@pytest.mark.slow
def test_transcribe_real_audio():
    """Requires actual Whisper inference — takes ~30 seconds."""
    ...
```

### Fixtures

Use `conftest.py` for shared fixtures:

```python
import pytest
from pathlib import Path

@pytest.fixture
def sample_project(tmp_path):
    """Create a minimal project directory for testing."""
    ...

@pytest.fixture
def sample_transcript():
    """Load sample transcript from fixtures."""
    ...

@pytest.fixture
def sample_config():
    """Return a resolved documentary profile config."""
    ...
```

Use `fixtures/` directory for static test data (JSON files, small audio clips). Keep test audio under 10 seconds for speed.

## Code Quality

### Before Every Commit

```bash
# Lint
ruff check .

# Format
ruff format .

# Type check
mypy plotline/

# Test
pytest tests/
```

### Ruff Configuration (in pyproject.toml)

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
# E: pycodestyle errors
# F: pyflakes
# I: isort (import sorting)
# N: pep8-naming
# W: pycodestyle warnings
# UP: pyupgrade (modern Python syntax)
```

### Type Hints

Type all function signatures. Use modern syntax:

```python
# Good
def load_transcript(path: Path) -> dict:
def process_segments(segments: list[dict], weights: dict[str, float]) -> list[dict]:
def get_config(key: str) -> str | None:

# Bad
def load_transcript(path):
def process_segments(segments, weights):
```

For complex types, define TypedDicts or dataclasses in the module:

```python
from typing import TypedDict

class Segment(TypedDict):
    segment_id: str
    start: float
    end: float
    text: str
    delivery: dict
```

## Adding Dependencies

1. **Check if stdlib or existing deps cover it first**
2. If genuinely needed, add to `pyproject.toml` under the appropriate group
3. Document why in the commit message
4. Update `docs/environment-setup.md` if it's a new install step

**Don't add:** heavy frameworks (Django, Flask), GUI toolkits (tkinter, Qt), JavaScript build tools (node, webpack), anything that requires compilation on the user's machine.

## File I/O Conventions

### JSON Files

Always use the helpers in `plotline/io.py`:

```python
from plotline.io import read_json, write_json

data = read_json(project.data_path / "transcripts" / "interview_001.json")
write_json(project.data_path / "segments" / "interview_001.json", enriched_data)
```

`write_json` should:
- Pretty-print with 2-space indent
- Ensure UTF-8 encoding
- Write atomically (temp file → rename)
- Create parent directories if needed

### Paths

Always use `pathlib.Path`. Never use string concatenation for paths:

```python
# Good
output_path = project.export_dir / f"plotline_selects.{format}"

# Bad
output_path = project.export_dir + "/plotline_selects." + format
```

## Documentation in Code

### Module Docstrings

Every module (`.py` file) has a docstring at the top explaining what it does and how it fits in the pipeline:

```python
"""
plotline.analyze.delivery — Per-segment audio feature extraction

Takes transcript segment boundaries and the full-rate audio WAV,
extracts delivery metrics (energy, pitch, speech rate, pauses) for
each segment using librosa.

Pipeline position: Stage 3 (after transcription, before enrichment)
Input: audio_full.wav + transcript.json
Output: delivery.json
Schema: See ARCHITECTURE.md → delivery.json
"""
```

### Function Docstrings

Public functions get docstrings. One-liner if obvious, detailed if not:

```python
def compute_rms_energy(audio: np.ndarray, sr: int, start: float, end: float) -> float:
    """Compute RMS energy for an audio segment.
    
    Args:
        audio: Full audio signal array
        sr: Sample rate
        start: Segment start time in seconds
        end: Segment end time in seconds
    
    Returns:
        RMS energy as a float (not normalized)
    """
```
