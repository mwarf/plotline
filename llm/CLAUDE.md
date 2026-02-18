# CLAUDE.md — Instructions for the LLM Coder

You are building **Plotline**, an AI-assisted documentary editing toolkit. This file tells you how to work in this codebase.

## What Plotline Does

Plotline takes raw video interviews and produces editable DaVinci Resolve timelines through a six-stage pipeline: audio extraction → transcription → emotional delivery analysis → LLM theme extraction → narrative arc construction → timeline export. It serves documentary filmmakers and corporate brand producers.

## Reference Documents

Read these before starting any task:

| File | When to Read | What It Contains |
|------|-------------|-----------------|
| `ARCHITECTURE.md` | Before any coding task | System design, data flow, JSON schemas, module boundaries |
| `CONTRIBUTING.md` | Before your first commit | Code style, testing, branch strategy, PR conventions |
| `PROMPTS.md` | Before working on LLM passes (Phase 5) | How to write and test prompt templates |
| `RESOLVE.md` | Before working on export (Phase 6) | EDL format spec, FCPXML spec, timecode math |
| `docs/build-plan.md` | To find your current task | Full task list with acceptance criteria and PRD references |
| `docs/environment-setup.md` | For dependency questions | Python environment, external tools, verification |
| `docs/PRD_v1.3.docx` | For detailed requirements | Full product requirements document |

## How to Work on a Task

1. **Find the task** in `docs/build-plan.md`. Note its phase, dependencies, PRD references, and acceptance criteria.
2. **Read the relevant reference docs** listed under that task (especially ARCHITECTURE.md for schemas).
3. **Check dependencies are met** — verify the tasks listed under "Depends On" are complete.
4. **Write the code** following the conventions in CONTRIBUTING.md.
5. **Write tests** that match the acceptance criteria.
6. **Run the test suite** before committing: `pytest tests/`
7. **Run the linter**: `ruff check . && ruff format --check .`

## Code Conventions

### Python Style
- **Python 3.11+** — use modern syntax (type hints, match statements, f-strings, `|` union types)
- **Type hints on all function signatures** — no exceptions
- **Docstrings on all public functions** — one-line summary, then Args/Returns if non-obvious
- **100 character line length** (configured in pyproject.toml)
- **ruff** for linting and formatting — run before every commit

### Naming
- Modules: `snake_case.py`
- Classes: `PascalCase`
- Functions/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private: prefix with `_`

### Imports
```python
# Standard library
import json
from pathlib import Path

# Third party
import librosa
import numpy as np
from typer import Typer

# Local
from plotline.config import PlotlineConfig
from plotline.project import Project
```

### Error Handling
- Use custom exceptions defined in `plotline/exceptions.py`
- Never catch bare `except:`
- CLI commands should catch exceptions and print user-friendly messages via `rich.console`
- Pipeline stages should fail loudly and early — don't silently skip broken data

### File I/O
- Use `pathlib.Path` everywhere, never string concatenation for paths
- All JSON I/O through helper functions in `plotline/io.py` that handle encoding and pretty-printing
- Write files atomically (write to temp, then rename) to prevent corruption on interruption

## Project Structure

```
plotline/
├── plotline/
│   ├── __init__.py
│   ├── cli.py              # Typer app with all subcommands
│   ├── config.py            # YAML config loading, profile merging, validation
│   ├── project.py           # Project directory creation, manifest management
│   ├── brief.py             # Creative brief parsing + normalize_key_messages()
│   ├── compare.py           # Cross-interview best-take comparison logic
│   ├── io.py                # JSON read/write helpers, atomic file writes
│   ├── exceptions.py        # Custom exception classes
│   ├── extract/
│   │   ├── __init__.py
│   │   └── audio.py         # FFmpeg audio extraction
│   ├── transcribe/
│   │   ├── __init__.py
│   │   ├── engine.py        # Whisper transcription (mlx or fallback)
│   │   └── segments.py      # Segment boundary post-processing
│   ├── analyze/
│   │   ├── __init__.py
│   │   ├── delivery.py      # Per-segment audio feature extraction
│   │   ├── scoring.py       # Composite score + delivery labels
│   │   └── metrics.py       # Individual metric functions (energy, pitch, etc.)
│   ├── enrich/
│   │   ├── __init__.py
│   │   └── merge.py         # Merge transcript + delivery → unified manifest
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── client.py        # litellm wrapper with privacy checks
│   │   ├── templates.py     # Jinja2 prompt template loading + rendering
│   │   ├── themes.py        # Pass 1: theme extraction
│   │   ├── synthesis.py     # Pass 2: cross-interview synthesis
│   │   ├── arc.py           # Pass 3: narrative arc construction
│   │   ├── flags.py         # Pass 4: cultural content flagging
│   │   └── parsing.py       # LLM output JSON parsing with validation
│   ├── export/
│   │   ├── __init__.py
│   │   ├── edl.py           # CMX 3600 EDL generation
│   │   ├── fcpxml.py        # FCPXML 1.11 generation
│   │   └── timecode.py      # Timecode math utilities
│   ├── reports/
│   │   ├── __init__.py
│   │   ├── generator.py     # Report generation orchestration
│   │   ├── compare.py       # Cross-interview comparison report
│   │   ├── transcript.py    # Per-interview transcript report
│   │   ├── coverage.py      # Brief coverage matrix report
│   │   └── templates/       # Jinja2 HTML templates
│   │       ├── base.html
│   │       ├── dashboard.html
│   │       ├── transcript.html
│   │       ├── review.html
│   │       ├── summary.html
│   │       ├── compare.html
│   │       └── coverage.html
│   └── profiles/
│       ├── documentary.yaml
│       ├── brand.yaml
│       └── commercial-doc.yaml
├── prompts/                  # Default prompt templates (copied to projects)
│   ├── themes.txt
│   ├── themes_brand.txt
│   ├── synthesize.txt
│   ├── arc.txt
│   └── flags.txt
├── tests/
│   ├── conftest.py           # Shared fixtures
│   ├── test_cli.py
│   ├── test_config.py
│   ├── test_extract.py
│   ├── test_transcribe.py
│   ├── test_analyze.py
│   ├── test_enrich.py
│   ├── test_llm.py
│   ├── test_export.py
│   ├── test_compare.py       # Cross-interview comparison tests
│   ├── test_transcript_report.py  # Transcript report tests
│   ├── test_coverage_report.py    # Coverage matrix tests
│   ├── test_flags.py         # Cultural flags tests
│   ├── test_project.py
│   ├── test_validation.py
│   └── fixtures/             # Test data (small audio clips, sample JSONs)
├── docs/
│   └── index.html            # Marketing/landing page
├── CLAUDE.md                 # This file
├── ARCHITECTURE.md
├── CONTRIBUTING.md
├── PROMPTS.md
├── RESOLVE.md
├── CHANGELOG.md
├── ROADMAP.md
├── pyproject.toml
└── README.md
```

## When You Get Stuck

1. **Schema questions** → Read ARCHITECTURE.md for the JSON schema of the stage you're working on
2. **"How should this behave?"** → Check the acceptance criteria in build-plan.md, then the PRD section referenced
3. **Timecode/export issues** → Read RESOLVE.md thoroughly — timecode math is subtle
4. **LLM output parsing failures** → Read PROMPTS.md for output format conventions, then check parsing.py
5. **Dependency import errors** → Check environment-setup.md for the correct package names
6. **"Should I add a new dependency?"** → Probably not. Check if an existing dependency or stdlib covers it first. If you must, discuss it.

## Key Design Decisions to Respect

- **Every pipeline stage reads/writes JSON** — intermediate data is always inspectable and editable
- **Stages are independently re-runnable** — never assume upstream stages will re-run
- **Config is the single source of truth** — don't hardcode values that should come from plotline.yaml
- **Profiles change behavior, not code paths** — the pipeline is the same for documentary and brand; only config values differ
- **Privacy mode is enforced, not advisory** — if `privacy_mode: local`, cloud API calls must be blocked, not warned
- **Audio never leaves the machine** — even in hybrid mode, only text/metadata goes to cloud APIs
- **Fail loudly** — if a stage can't produce correct output, stop. Don't pass garbage downstream.
