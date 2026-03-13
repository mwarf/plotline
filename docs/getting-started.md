# Getting Started with Plotline

Get from raw interviews to an editable DaVinci Resolve timeline with minimal manual work.

> **Time expectations:** 5 minutes of user interaction (running commands, reviewing). Processing time varies: 10-15 minutes per hour of footage on Apple Silicon, longer on CPU.

---

## Prerequisites

Before you start, ensure you have:

- **Python 3.11+** — Check with `python --version`
- **FFmpeg** — Install with `brew install ffmpeg` (macOS), `sudo apt install ffmpeg` (Ubuntu/Debian), or `winget install ffmpeg` (Windows)
- **Ollama** — Download from [ollama.ai](https://ollama.ai), then `ollama pull llama3.1:70b`

> **Quality note:** Local models (Ollama) work well for drafts and privacy-sensitive projects. For best output quality, consider using Claude or GPT-4 with an API key. See [LLM Quality](../README.md#llm-quality--privacy-tradeoffs) for details.

Verify everything works:

```bash
plotline doctor
```

---

## Quickstart

### 1. Create a Project

```bash
plotline init my-documentary --profile documentary
cd my-documentary
```

This creates a project folder with default configuration.

### 2. Add Your Videos

```bash
plotline add ~/Videos/interview1.mov ~/Videos/interview2.mov
```

Plotline extracts metadata (frame rate, duration, timecode) and prepares for processing.

### 3. Run the Pipeline

```bash
plotline run
```

This runs all stages automatically:
- Extracts audio from videos
- Transcribes with Whisper
- Analyzes emotional delivery
- Extracts themes with LLM
- Builds a narrative arc
- Selects the best segments

**Time:** ~10-15 minutes per hour of footage (varies by hardware)

### Optional: Speaker Identification

If your interviews have multiple speakers, you can identify and filter them:

```bash
pip install -e ".[diarization]"
export HUGGINGFACE_TOKEN=hf_xxx  # See Diarization Setup guide
plotline diarize
```

See the [Diarization Setup Guide](diarization-setup.md) for HuggingFace configuration.

### 4. Review the Selections

```bash
plotline review --open
```

A browser window opens with the proposed timeline:
- Listen to each segment (Space to play)
- Approve (A) or Reject (X)
- Drag to reorder
- Add your notes

### 5. Export the Timeline

```bash
plotline export --format edl
```

This generates `export/my-documentary.edl` ready for import.

---

## What Just Happened?

1. **Audio Extraction** — FFmpeg extracted 16kHz audio for transcription
2. **Transcription** — Whisper converted speech to text with timestamps
3. **Delivery Analysis** — Librosa measured energy, pace, expressiveness
4. **Theme Extraction** — LLM identified recurring themes and topics
5. **Narrative Arc** — LLM selected segments and arranged them into a story
6. **Review** — You approved segments for export
7. **Export** — EDL generated with frame-accurate timecodes

---

## Import into DaVinci Resolve

1. Import your source videos into the Media Pool
2. Go to **File → Import Timeline → Import AAF/EDL/XML**
3. Select `export/my-documentary.edl`
4. Click OK

Your timeline appears with all approved clips in order, with handles for transitions.

---

## Next Steps

### Add a Creative Brief

Guide the LLM with your project goals:

```bash
plotline brief brief.md
plotline run --force  # Re-run with brief
```

The brief helps the LLM prioritize segments that align with your key messages.

### Try Different Profiles

- `documentary` — Emphasis on emotional authenticity
- `brand` — Emphasis on message clarity
- `commercial-doc` — Hybrid with cultural sensitivity flagging

### Explore the Reports

```bash
plotline report themes --open     # Explore by theme
plotline report coverage --open   # Check brief coverage
plotline compare --open           # Compare best takes
```

### Export Alternates

```bash
plotline export --alternates
```

Generates a secondary timeline with alternate takes for comparison.

---

## Common Issues

| Issue | Solution |
|-------|----------|
| FFmpeg not found | `brew install ffmpeg` (macOS) or see [FAQ](FAQ.md) |
| Ollama not running | `ollama serve && ollama pull llama3.1:70b` |
| No approved segments | Run `plotline review --open` and approve with `A` |

See the [FAQ](FAQ.md) for detailed troubleshooting.

---

## Full Documentation

- **[README](../README.md)** — Complete CLI reference
- **[Workflow Guide](workflow-guide.md)** — Detailed end-to-end tutorial
- **[Export Guide](export-guide.md)** — NLE export workflows
- **[Reports Guide](reports-guide.md)** — HTML reports reference
- **[FAQ](FAQ.md)** — Common questions
