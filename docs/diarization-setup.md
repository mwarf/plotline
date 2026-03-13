# Speaker Diarization Setup Guide

This guide walks you through setting up speaker diarization in Plotline — the ability to identify and label different speakers in your interview audio.

---

## What is Speaker Diarization?

Diarization automatically identifies who spoke when in an audio recording. In Plotline, this enables:

- **Speaker labels** on every transcript segment
- **Interviewer filtering** — Exclude questions from your final timeline
- **Speaker-specific analysis** — See delivery metrics per person
- **Better LLM context** — The AI knows who said what

---

## Prerequisites

Before you begin, you'll need:

1. **Plotline installed** — See [README](../README.md#installation)
2. **HuggingFace account** — Free, takes 1 minute
3. **Model access approval** — Requires accepting terms (can take hours)

---

## Step 1: Install Diarization Dependencies

Plotline uses [pyannote.audio](https://github.com/pyannote/pyannote-audio) for speaker diarization. Install the extra dependencies:

```bash
pip install -e ".[diarization]"
```

This installs:
- `pyannote.audio>=3.1` — Speaker diarization model
- `torch>=2.0` — Deep learning framework
- `torchaudio>=2.0` — Audio processing

### GPU Acceleration (Recommended)

Diarization is significantly faster with GPU acceleration.

**macOS (Apple Silicon M1/M2/M3):**
```bash
# MPS acceleration is automatic — no extra steps needed
pip install -e ".[diarization]"
```

**Windows/Linux with NVIDIA GPU:**
```bash
# Install CUDA-enabled PyTorch first
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121

# Then install diarization dependencies
pip install -e ".[diarization]"
```

**CPU-only (all platforms):**
```bash
# Works but slower — use only if no GPU available
pip install -e ".[diarization]"
```

### Verify GPU Detection

```bash
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, MPS: {torch.backends.mps.is_available()}')"
```

Expected output:
- **macOS**: `CUDA: False, MPS: True`
- **NVIDIA GPU**: `CUDA: True, MPS: False`
- **CPU only**: `CUDA: False, MPS: False`

---

## Step 2: Create HuggingFace Account

1. Go to [huggingface.co/join](https://huggingface.co/join)
2. Sign up with email or GitHub
3. Verify your email address

---

## Step 3: Accept Model Terms

pyannote models require you to accept their user conditions. You must do this **for both models**:

### Model 1: Segmentation

1. Go to [pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0)
2. Click **"Access repository"** or **"Agree and access repository"**
3. Accept the user conditions

### Model 2: Speaker Diarization

1. Go to [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)
2. Click **"Access repository"** or **"Agree and access repository"**
3. Accept the user conditions

> **Important:** After accepting, you'll receive an email confirmation. Access can take anywhere from a few minutes to several hours to activate. If diarization fails with a 401 error, you may need to wait.

---

## Step 4: Generate Access Token

1. Go to [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
2. Click **"Create new token"**
3. Name it (e.g., "plotline-diarization")
4. Select **"Read"** permissions (Write not needed)
5. Click **"Generate token"**
6. **Copy the token now** — you won't see it again!

Your token looks like: `hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

---

## Step 5: Configure Token

You have three options to provide your HuggingFace token to Plotline:

### Option A: Environment Variable (Recommended)

Add to your shell configuration (`~/.zshrc`, `~/.bashrc`, or PowerShell profile):

**macOS/Linux (bash/zsh):**
```bash
echo 'export HUGGINGFACE_TOKEN=hf_xxx' >> ~/.zshrc
source ~/.zshrc
```

**Windows (PowerShell):**
```powershell
[Environment]::SetEnvironmentVariable("HUGGINGFACE_TOKEN", "hf_xxx", "User")
```

### Option B: Interactive Prompt

If no token is found, Plotline will prompt you when you run `plotline diarize`:

```
HuggingFace token required for speaker diarization.

Get a token at: https://huggingface.co/settings/tokens

You must accept the user conditions at:
  - https://huggingface.co/pyannote/segmentation-3.0
  - https://huggingface.co/pyannote/speaker-diarization-3.1

Enter your HuggingFace token:
```

The token is cached at `~/.plotline/hf_token` for future use.

### Option C: Cache File

Create the cache file directly:

```bash
mkdir -p ~/.plotline
echo "hf_xxx" > ~/.plotline/hf_token
```

---

## Step 6: Enable Diarization

Edit your project's `plotline.yaml`:

```yaml
diarization_enabled: true
```

Or run diarization manually:

```bash
plotline diarize
```

---

## Platform-Specific Notes

### macOS (Apple Silicon)

- **Memory**: Diarization uses 2-4GB RAM. Close other apps if you have 8GB or less.
- **Performance**: M1/M2/M3 chips are fast — expect ~5-10 min per hour of audio.
- **MPS**: Metal Performance Shaders acceleration is automatic.

### Windows

- **CUDA**: Install CUDA toolkit 11.8+ for NVIDIA GPU acceleration.
- **PowerShell**: Use PowerShell 7+ for best compatibility.
- **Environment variables**: Restart your terminal after setting `HUGGINGFACE_TOKEN`.

### Linux

- **CUDA**: Ensure NVIDIA drivers and CUDA toolkit are installed.
- **CPU fallback**: If no GPU, diarization will use CPU (slower but functional).
- **Memory**: May need to increase shared memory in Docker: `--shm-size=4g`

---

## Troubleshooting

### "401 Unauthorized" or "Access to model is restricted"

**Cause:** You haven't accepted the model terms, or access hasn't activated yet.

**Solution:**
1. Verify you accepted terms at both model pages
2. Check your email for confirmation
3. Wait up to 24 hours for access to activate
4. Verify at [huggingface.co/pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1) — you should see the model files

### "Out of memory" or CUDA errors

**Cause:** Not enough GPU memory for the model.

**Solutions:**
1. Reduce speaker range in config:
   ```yaml
   diarization_max_speakers: 3  # Lower from default 5
   ```
2. Force CPU mode (slower but more reliable):
   ```bash
   CUDA_VISIBLE_DEVICES="" plotline diarize
   ```

### Diarization is very slow

**Cause:** Not using GPU acceleration.

**Solution:**
1. Verify GPU detection:
   ```bash
   python -c "import torch; print(torch.cuda.is_available())"
   ```
2. For NVIDIA, ensure CUDA PyTorch is installed:
   ```bash
   pip install torch --index-url https://download.pytorch.org/whl/cu121
   ```
3. Check you don't have CPU-only torch:
   ```bash
   pip show torch | grep Version
   # Should show +cu121 for CUDA, not +cpu
   ```

### "No speakers detected"

**Cause:** Audio may be too short or noisy, or min/max speakers misconfigured.

**Solutions:**
1. Ensure audio is at least 30 seconds long
2. Adjust speaker range:
   ```yaml
   diarization_min_speakers: 1
   diarization_max_speakers: 3
   ```

### Token prompt appears every time

**Cause:** Token not being cached properly.

**Solution:**
1. Check cache file exists:
   ```bash
   cat ~/.plotline/hf_token
   ```
2. Or set environment variable permanently (see Step 5)

---

## Usage Examples

### Basic Usage

```bash
# Run diarization on all interviews
plotline diarize

# Interactive speaker review (automatic after diarization)
# ? Exclude SPEAKER_00 from EDL? [Y/n] y
# ? Name SPEAKER_01: Jane Doe
```

### Force Re-diarization

```bash
plotline diarize --force
```

### Skip Interactive Prompts

```bash
plotline diarize --no-prompt
# or
plotline diarize -q
```

### Specify Speaker Count

If you know exactly how many speakers:

```bash
plotline diarize --num-speakers 2
```

Or in config:
```yaml
diarization_num_speakers: 2
```

### Configure Speakers After Diarization

```bash
# Preview with heuristics
plotline speakers --preview

# List all speakers
plotline speakers --list

# Edit in text editor
plotline speakers --edit

# Set name and role
plotline speakers SPEAKER_00 --name "Host" --role interviewer --exclude
plotline speakers SPEAKER_01 --name "Jane Doe" --role subject --include
```

---

## Configuration Reference

```yaml
# plotline.yaml

# Enable diarization in pipeline
diarization_enabled: false

# Model to use (default is recommended)
diarization_model: "pyannote/speaker-diarization-3.1"

# Exact speaker count (if known)
diarization_num_speakers: null  # Auto-detect

# Speaker range (used if num_speakers is null)
diarization_min_speakers: 2
diarization_max_speakers: 5
```

---

## Related Documentation

- [README §5.5 — Speaker Diarization](../README.md#55-speaker-diarization--filtering-optional)
- [FAQ — Diarization](FAQ.md#speaker-diarization)
- [Workflow Guide §2.5](workflow-guide.md#25-speaker-diarization-optional)
