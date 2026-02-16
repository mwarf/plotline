# Plotline

AI-assisted documentary editing toolkit that transforms raw video interviews into editable DaVinci Resolve timelines.

## Overview

Plotline analyzes interview footage to identify the most compelling moments and assembles them into a coherent narrative. It combines:

- **Whisper** for transcription
- **Librosa** for emotional delivery analysis
- **LLM** for theme extraction and narrative construction
- **EDL/FCPXML** export for professional NLEs

```
Video Interview → Audio → Transcript → Delivery Analysis → LLM Themes → Narrative Arc → EDL/FCPXML
```

## Installation

```bash
# Clone and install
git clone https://github.com/your-org/plotline.git
cd plotline
pip install -e .
```

### Requirements

- **Python 3.11+**
- **FFmpeg** — Audio extraction

  ```bash
  # macOS
  brew install ffmpeg

  # Ubuntu/Debian
  sudo apt install ffmpeg
  ```

- **Ollama** (for local LLM) — [Install Ollama](https://ollama.ai)
  ```bash
  # Pull a model
  ollama pull llama3.1:8b
  ```

### Verify Installation

```bash
plotline doctor
```

## Quick Start

```bash
# 1. Create a project
plotline init my-doc --profile documentary
cd my-doc

# 2. Add video files
plotline add ~/Videos/interview1.mov ~/Videos/interview2.mov

# 3. Run the full pipeline
plotline run

# 4. Review selections
plotline review

# 5. Export timeline
plotline export --format edl
```

## CLI Reference

### Project Management

| Command                    | Description                |
| -------------------------- | -------------------------- |
| `plotline init <name>`     | Create a new project       |
| `plotline add <videos...>` | Add video files to project |
| `plotline status`          | Show pipeline progress     |
| `plotline doctor`          | Check dependencies         |
| `plotline validate`        | Validate project data      |

### Pipeline Stages

| Command               | Description                            |
| --------------------- | -------------------------------------- |
| `plotline extract`    | Extract audio from videos              |
| `plotline transcribe` | Transcribe using Whisper               |
| `plotline analyze`    | Analyze emotional delivery             |
| `plotline enrich`     | Merge transcript + delivery            |
| `plotline themes`     | Extract themes (LLM Pass 1)            |
| `plotline synthesize` | Cross-interview synthesis (LLM Pass 2) |
| `plotline arc`        | Build narrative arc (LLM Pass 3)       |
| `plotline run`        | Run full pipeline                      |

### Reports

| Command                     | Description                |
| --------------------------- | -------------------------- |
| `plotline report dashboard` | Pipeline status dashboard  |
| `plotline report review`    | Selection review interface |
| `plotline report summary`   | Project summary            |

### Export

| Command                           | Description                            |
| --------------------------------- | -------------------------------------- |
| `plotline export --format edl`    | Export CMX 3600 EDL                    |
| `plotline export --format fcpxml` | Export FCPXML 1.11                     |
| `plotline export --all`           | Export all segments (ignore approvals) |
| `plotline export --handle 24`     | Custom handle padding (frames)         |

### Other

| Command                 | Description                           |
| ----------------------- | ------------------------------------- |
| `plotline brief <file>` | Attach creative brief (Markdown/YAML) |
| `plotline compare`      | Compare best takes (multi-interview)  |

## Pipeline Stages

### 1. Audio Extraction

Extracts 16kHz mono WAV for transcription and full-rate WAV for delivery analysis.

```bash
plotline extract
```

### 2. Transcription

Transcribes audio using mlx-whisper (Apple Silicon) or faster-whisper.

```bash
plotline transcribe --model medium --language en
```

### 3. Delivery Analysis

Analyzes speaker delivery using librosa:

- **RMS energy** — Volume/intensity
- **Pitch variation** — Vocal expressiveness
- **Speech rate** — Words per minute
- **Pause patterns** — Timing and pacing
- **Spectral features** — Voice quality

```bash
plotline analyze
```

### 4. Enrichment

Merges transcript and delivery data into unified segments.

```bash
plotline enrich
```

### 5. LLM Analysis

Three-pass LLM analysis:

| Pass | Command               | Purpose                              |
| ---- | --------------------- | ------------------------------------ |
| 1    | `plotline themes`     | Extract themes per interview         |
| 2    | `plotline synthesize` | Cross-interview theme synthesis      |
| 3    | `plotline arc`        | Build narrative arc, select segments |

### 6. Export

Generate timeline files for NLEs:

- **EDL** — CMX 3600 format for DaVinci Resolve, Premiere Pro
- **FCPXML** — Final Cut Pro XML with markers, keywords, metadata

## Configuration

Configuration is stored in `plotline.yaml`:

```yaml
project_name: my-documentary
project_profile: documentary

# LLM settings
llm_backend: ollama
llm_model: llama3.1:8b
privacy_mode: local

# Whisper settings
whisper_backend: mlx
whisper_model: medium

# Output settings
target_duration_seconds: 600
handle_padding_frames: 12

# Delivery weights (for scoring)
delivery_weights:
  energy: 0.15
  pitch_variation: 0.15
  speech_rate: 0.25
  pause_weight: 0.30
  spectral_brightness: 0.10
  voice_texture: 0.05
```

### LLM Backends

| Backend    | Description                         |
| ---------- | ----------------------------------- |
| `ollama`   | Local inference via Ollama          |
| `lmstudio` | Local inference via LM Studio       |
| `claude`   | Anthropic Claude (requires API key) |
| `openai`   | OpenAI GPT-4 (requires API key)     |

For cloud backends, set `privacy_mode: hybrid` and export API keys:

```bash
export ANTHROPIC_API_KEY=sk-...
export OPENAI_API_KEY=sk-...
```

## Profiles

Profiles customize delivery scoring and narrative style:

### Documentary

```yaml
project_profile: documentary
```

- Emphasis on emotional authenticity
- Higher weight on pauses and speech rate
- Emergent narrative structure
- Best for: Documentary films, interviews

### Brand

```yaml
project_profile: brand
```

- Emphasis on message clarity and energy
- Higher weight on energy and confidence
- Message-aligned structure
- Best for: Corporate videos, brand content

### Commercial Documentary

```yaml
project_profile: commercial-doc
```

- Hybrid of documentary and brand
- Balanced scoring
- Best for: Branded documentaries

## Creative Briefs

Attach a creative brief to guide LLM analysis:

```bash
# Markdown brief
plotline brief brief.md

# YAML brief
plotline brief brief.yaml --show
```

Brief format (Markdown):

```markdown
# Key Messages

- Innovation drives our success
- Customer satisfaction is our priority

# Audience

Decision-makers in enterprise technology

# Tone

Professional, confident, inspiring

# Target Duration

3-5 minutes

# Must Include

- Product demo footage
- Customer testimonials

# Avoid

- Technical jargon
- Competitor comparisons
```

## Reports

### Dashboard

```bash
plotline status --open
```

Shows pipeline progress, interview cards, stage completion.

### Review

```bash
plotline review
```

Interactive selection review with:

- Approve/reject buttons
- Keyboard shortcuts (A, X, F, Space, arrows)
- Audio playback
- Theme tags

### Summary

```bash
plotline report summary
```

Executive summary with:

- Interview contributions
- Theme map
- Narrative arc overview
- Delivery highlights

## Project Structure

```
my-project/
├── plotline.yaml          # Configuration
├── interviews.json        # Manifest + stage status
├── brief.json             # Parsed creative brief (optional)
├── approvals.json         # Review approvals (optional)
├── source/                # Extracted audio
│   └── interview_001/
│       ├── audio_16k.wav
│       └── audio_full.wav
├── data/
│   ├── transcripts/       # Whisper output
│   ├── delivery/          # Librosa analysis
│   ├── segments/          # Enriched segments
│   ├── themes/            # Per-interview themes
│   ├── synthesis.json     # Cross-interview synthesis
│   └── selections.json    # Arc selections
├── prompts/               # LLM prompt templates
├── reports/               # HTML reports
└── exports/               # EDL/FCPXML files
```

## Troubleshooting

### FFmpeg not found

```bash
# Install FFmpeg
brew install ffmpeg

# Verify
ffmpeg -version
```

### Ollama not running

```bash
# Start Ollama
ollama serve

# Pull model
ollama pull llama3.1:8b
```

### Model not pulled

```bash
plotline doctor
# Shows: Model 'llama3.1:8b' not pulled
# Fix:
ollama pull llama3.1:8b
```

### Insufficient disk space

Audio extraction requires ~2MB per minute of video. Check available space:

```bash
plotline validate
```

### No audio track

Videos without audio tracks will fail extraction:

```
Error: interview.mp4 has no audio track
```

### LLM timeout

For long interviews, increase timeout in config:

```yaml
# Not yet exposed, but LLM client supports it
```

Or use a faster/smaller model:

```yaml
llm_model: llama3.1:8b
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Lint
ruff check plotline/

# Type check
pyright plotline/
```

## License

MIT
