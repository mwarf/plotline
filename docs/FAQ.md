# Frequently Asked Questions

---

## Installation

### How do I install FFmpeg?

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt install ffmpeg
```

**Windows:**
```powershell
winget install ffmpeg
```
Or with Chocolatey: `choco install ffmpeg`

After installing, **restart your terminal** so FFmpeg is found in PATH.

Verify: `ffmpeg -version`

### How do I install Ollama?

1. Download from [ollama.ai](https://ollama.ai)
2. Install the application
3. Pull a model: `ollama pull llama3.1:8b`
4. Verify: `ollama list`

### How do I verify my installation?

```bash
plotline doctor
```

This checks all dependencies and reports any issues.

---

## Pipeline

### How long does transcription take?

**Rough estimates per hour of footage:**

| Hardware | Backend | Time |
|----------|---------|------|
| Apple Silicon (M1/M2/M3) | mlx-whisper | 5-10 min |
| NVIDIA GPU (RTX 3080+) | faster-whisper (CUDA) | 8-15 min |
| CPU only | faster-whisper | 30-60 min |

Delivery analysis and LLM passes add another 5-10 minutes per hour.

**On Windows/Linux**, Plotline uses `faster-whisper` automatically. To enable GPU acceleration install the CUDA version of PyTorch before running:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

### Can I resume an interrupted pipeline?

Yes. Plotline tracks completed stages and only runs pending ones:

```bash
plotline run
# If interrupted, just run again:
plotline run
```

To re-run from a specific stage:
```bash
plotline run --from transcribe
```

### How do I process non-English footage?

Just run the pipeline — language is auto-detected:

```bash
plotline run
```

Whisper detects the spoken language, and LLM outputs in that language automatically. No configuration needed.

### Can I specify the language manually?

```bash
plotline transcribe --language es
```

Useful if auto-detection fails or for mixed-language content.

### What's the difference between profiles?

| Profile | Focus | Best For |
|---------|-------|----------|
| `documentary` | Emotional authenticity, emergent narrative | Documentary films, interviews |
| `brand` | Message clarity, energy | Corporate videos, marketing |
| `commercial-doc` | Hybrid approach, cultural sensitivity | Branded documentaries |

---

## Export

### Why is my EDL empty?

**Cause:** No segments have been approved.

**Solution:**
```bash
plotline review --open
# Approve segments with A key
plotline export --format edl
```

Or export all segments regardless of approval:
```bash
plotline export --format edl --all
```

### Why are handles cutting off dialogue?

**Cause:** Default handles (12 frames) may be too large for tight edits.

**Solutions:**
1. Smart handles automatically reduce for tight pauses — try the default first
2. Reduce handle size: `plotline export --handle 6`
3. Disable handles: `plotline export --handle 0`

### Timecodes don't match my NLE

**Possible causes:**

1. **Frame rate mismatch** — Ensure your NLE project matches source frame rate
2. **Drop-frame vs non-drop-frame** — Check if 29.97 should be DF or NDF
3. **Source timecode offset** — Verify `start_timecode` in `interviews.json`

### Which format should I use?

| NLE | Format |
|-----|--------|
| DaVinci Resolve | EDL |
| Adobe Premiere Pro | EDL |
| Final Cut Pro | FCPXML |
| Avid Media Composer | EDL |

FCPXML includes chapter markers and keywords; EDL is more universal.

### How do I compare alternate takes?

```bash
plotline export --alternates
```

This generates `{project}_alternates.edl` with all alternate candidates. Import it as a second timeline in your NLE to compare and swap takes.

---

## Review

### How do I reorder segments?

In the review report, drag and drop segment cards to reorder. Changes are saved automatically.

### Can I trim segment boundaries?

Not currently in the review interface. Segments are defined by Whisper's transcription boundaries.

**Workaround:** Trim in your NLE after export, using the handles.

### What do the delivery scores mean?

| Score | Interpretation |
|-------|----------------|
| 0.8 - 1.0 | Excellent delivery — high energy, expressive |
| 0.6 - 0.8 | Good delivery — engaging, natural |
| 0.4 - 0.6 | Moderate delivery — functional, clear |
| 0.0 - 0.4 | Lower delivery — may be monotone, quiet |

Scores combine energy, pitch variation, speech rate, and pause patterns.

### What are cultural sensitivity flags?

Segments that may require community or cultural review before publication. Examples:
- References to sacred practices
- Potentially sensitive terminology
- Content requiring context or consultation

Flags are optional and enabled with `cultural_flags: true` in config, or by using the `commercial-doc` profile.

### How do I add my own notes?

Click the "Notes" button on any segment in the review report. Notes are included in EDL/FCPXML exports.

---

## LLM

### Which model should I use?

| Model | Speed | Quality | Best For |
|-------|-------|---------|----------|
| `llama3.1:8b` | Fast | Good | Default, most projects |
| `llama3.1:70b` | Slow | Excellent | Complex narratives |
| `mistral:7b` | Fast | Good | Quick drafts |

For Apple Silicon, `llama3.1:8b` is the recommended default.

### Can I use a cloud LLM?

Yes. Set in `plotline.yaml`:

```yaml
llm_backend: claude
privacy_mode: hybrid
```

Then export your API key:
```bash
export ANTHROPIC_API_KEY=sk-...
```

Supported backends: `ollama`, `lmstudio`, `claude`, `openai`

### Why is the arc missing key messages?

**Possible causes:**

1. **No brief attached** — Add one: `plotline brief brief.md`
2. **Brief not aligned** — Ensure key messages are specific and verifiable
3. **No relevant content** — Interviews may not address all messages

Check the Coverage report to identify gaps:
```bash
plotline report coverage --open
```

### How do I improve LLM results?

1. **Add a creative brief** — Guide the LLM with your goals
2. **Try a larger model** — `llama3.1:70b` for complex narratives
3. **Adjust delivery weights** — Tune what "good delivery" means for your content
4. **Filter speakers** — Exclude interviewer questions if present

---

## Reports

### Audio not playing in reports?

**Safari:** Disable "Local File Restrictions" in Develop menu

**Firefox:** Use a local server:
```bash
cd reports && python -m http.server 8000
# Open http://localhost:8000/dashboard.html
```

**Chrome:** Works by default

### Coverage report shows "No brief attached"

Attach a creative brief first:
```bash
plotline brief brief.md
plotline report coverage --open
```

### Can I share reports with others?

Reports are self-contained HTML files. Copy the `reports/` folder to share. Recipients can open in any browser.

Note: Audio files are in `source/` and may need to be included for playback.

---

## Troubleshooting

### "Project not found"

Ensure you're in a Plotline project directory (contains `plotline.yaml`):
```bash
cd my-project
plotline status
```

### "Video has no audio track"

Plotline requires audio. Videos without audio tracks cannot be processed.

### "Insufficient disk space"

Audio extraction requires ~2MB per minute of video. Check available space:
```bash
plotline validate
```

### How do I start over?

Delete the project folder and reinitialize:
```bash
rm -rf my-project
plotline init my-project
```

To preserve source files but re-process:
```bash
rm -rf data/ reports/ export/
plotline run
```

---

## Still Have Questions?

- **[Documentation Index](index.md)** — All guides and references
- **[GitHub Issues](https://github.com/mwarf/plotline/issues)** — Report bugs
- **[GitHub Discussions](https://github.com/mwarf/plotline/discussions)** — Ask questions
