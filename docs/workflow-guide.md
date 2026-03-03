# Plotline: End-to-End Workflow Guide

Welcome to Plotline! Plotline is an AI-assisted documentary editing toolkit. It takes raw video interviews, analyzes them for emotional delivery and thematic content, and builds a coherent narrative arc that you can directly import into your video editor (DaVinci Resolve, Premiere Pro, or Final Cut Pro).

This guide walks you through the complete end-to-end workflow: from initializing a project to exporting your timeline.

---

## Stage 1: Project Setup

Before you begin, gather your video interviews and an optional creative brief.

### 1. Initialize the Project
Create a new Plotline project directory. You can choose a profile (`documentary` or `brand`) which tunes how the AI evaluates delivery and builds the story.

```bash
plotline init my-documentary --profile documentary
cd my-documentary
```

### 2. Add Interviews
Add your raw interview video files to the project. Plotline supports common formats (MOV, MP4, MXF).

```bash
plotline add /path/to/raw/interview_01.mov
plotline add /path/to/raw/interview_02.mov
```

### 3. Add a Creative Brief (Optional but Recommended)
If you have a creative brief with target audiences, tone, and key messages, save it as `brief.md` or `brief.yaml` in your project root. Plotline uses this to grade segments on how well they align with your project goals.

---

## Stage 2: Processing & Analysis

Now, let Plotline process the media. You can run these commands step-by-step or run `plotline run` to execute all pending stages automatically.

### 1. Extract Audio
Extracts optimized audio files for transcription and analysis.
```bash
plotline extract
```

### 2. Transcribe
Transcribes the audio using AI, complete with word-level timestamps so cuts in your NLE are frame-accurate.
```bash
plotline transcribe
```

### 2.5. Speaker Diarization (Optional)
Identifies different speakers in your interviews and labels each segment with the speaker. Useful for multi-subject interviews.
```bash
# Install diarization dependencies first
pip install plotline[diarization]

# Run diarization after transcription
plotline diarize

# View and edit speaker names
plotline speakers --list
plotline speakers --edit
```

**Requirements:** HuggingFace token with accepted terms at:
- https://huggingface.co/pyannote/segmentation-3.0
- https://huggingface.co/pyannote/speaker-diarization-3.1

Set token: `export HUGGINGFACE_TOKEN=hf_xxx` or enter when prompted.

### 3. Analyze Delivery
Extracts acoustic features (energy, speech rate, pitch variation, pauses) to grade the emotional delivery of every segment.
```bash
plotline analyze
```

### 4. Enrich Segments
Merges the text transcript and the delivery analysis into a single, unified data structure.
```bash
plotline enrich
```

---

## Stage 3: Story Engine (AI Passes)

With the raw data prepped, Plotline’s LLM engine takes over to find the story.

### 1. Extract Themes
Analyzes each interview individually to find recurring themes, emotional beats, and intersecting topics.
```bash
plotline themes
```

### 2. Synthesize (Cross-Interview)
Looks across *all* interviews to unify themes, find consensus, and identify the absolute "best takes" for shared topics.
```bash
plotline synthesize
```

### 3. Construct Narrative Arc
The AI acts as a story producer, selecting the strongest segments and ordering them into a coherent narrative arc (Opening, Body, Climax, Resolution).
```bash
plotline arc
```

### 4. Cultural Sensitivity Flags (Optional)
Scans selected segments for sensitive topics, sacred names, or cultural references that might require human or community review before publication.
```bash
plotline flags
```

---

## Stage 4: The Editorial Review (HTML Reports)

Plotline generates a suite of interactive, offline HTML reports. This is where you, the editor, take control. Open the dashboard to explore:

```bash
plotline report dashboard --open
```

### Navigating the Reports
Use the top navigation bar to move seamlessly between views:

*   **Dashboard**: A high-level overview of your project, processing progress, and creative brief parameters.
*   **Transcripts**: Read transcripts while listening to audio playback. View "Energy" and "Pacing" timelines. Filter by "High Score" delivery to quickly find the best soundbites.
*   **Themes**: An interactive map of the ideas discussed. Click on themes to see all related segments. 
*   **Compare**: If multiple subjects talk about the same topic, this view stacks them side-by-side so you can easily compare the "best takes."
*   **Coverage**: A matrix showing how well your selected story aligns with the Key Messages in your Creative Brief. Click any dot on the matrix to jump straight to that segment.
*   **Summary**: A quick cheat-sheet of what the AI built, including delivery highlights and the overall theme map.

### The Review Interface (`review.html`)
This is your primary workspace. The AI has built a proposed timeline, but you have final say.

1.  **Read & Listen**: Read the AI's editorial notes and pacing guidance (e.g., *"Hold on the smile before cutting"*). Click `▶ Play` to hear the segment.
2.  **Approve / Reject**: Use the buttons or keyboard shortcuts (`A` for Approve, `X` for Reject) to make your selections.
3.  **Review Flags**: If the AI flagged a segment for cultural review, you'll see a prominent yellow warning banner explaining why.
4.  **Reorder the Timeline**: Disagree with the AI's structure? **Drag and drop** segment cards to reorder them exactly how you want them.
5.  **Add Notes**: Click `📝 Notes` to leave yourself reminders for when you get into your NLE.
6.  **Search & Batch**: Use the search bar to filter by keywords, themes, or delivery scores, and use the "Batch Actions" to approve or reject groups of clips at once.

When you are happy with the selections, click **Export Approved** in the top right. This saves your decisions to an `approvals.json` file.

---

## Stage 5: Export to NLE

Finally, generate an Edit Decision List (EDL) or Final Cut Pro XML (FCPXML) file to import directly into your video editing software.

```bash
plotline export --format edl
# or
plotline export --format fcpxml
```

### Importing into Your Editor
1. Open DaVinci Resolve, Premiere Pro, or Final Cut Pro.
2. Import your original video files into the Media Pool.
3. Go to **File > Import > Timeline** and select the `.edl` or `.fcpxml` generated by Plotline.
4. Your editor will automatically link the original media and lay out the exact segments you approved, in the order you arranged them, completely frame-accurate.

Happy editing!