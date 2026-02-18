# Plotline Roadmap

This document outlines planned features and enhancements for future releases.

## v0.2.0 — Polish & Gaps

Released: 2026-02-17

| Feature              | Description                                                                                                                             | Status    |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------------- | --------- |
| `plotline compare`   | Side-by-side best-take comparison across interviews for the same theme/message. Rank candidates by delivery score, show audio playback. | **Done** |
| Transcript Report    | Interactive HTML report with delivery timeline, waveform visualization, and segment breakdown per interview.                            | **Done** |
| Cultural Flags (5.6) | Optional LLM pass to flag potentially sensitive cultural content for documentary ethics review.                                         | **Done** |
| Coverage Matrix      | Visualize how creative brief messages are covered across selected segments. Identify gaps.                                              | **Done** |

---

## v0.3.0 — Speed & Scale

Target: Q3 2025

| Feature              | Description                                                                                             | Status  |
| -------------------- | ------------------------------------------------------------------------------------------------------- | ------- |
| Parallel Processing  | Transcribe and analyze multiple interviews concurrently. Significant speedup for 6+ interview projects. | Planned |
| Batch Projects       | Process multiple projects in queue. Background mode with progress tracking.                             | Planned |
| Resume Interrupted   | Graceful recovery from interrupted pipelines. Continue from last successful stage.                      | Planned |
| Progress Persistence | Store progress in SQLite for long-running projects. Query status anytime.                               | Planned |

---

## v0.4.0 — Multi-Language

Target: Q4 2025

| Feature                 | Description                                                            | Status  |
| ----------------------- | ---------------------------------------------------------------------- | ------- |
| Language Auto-Detection | Whisper automatically detects spoken language per interview.           | Planned |
| Translation Pipeline    | Translate non-English transcripts to English for unified LLM analysis. | Planned |
| Mixed-Language Projects | Handle interviews in multiple languages within same project.           | Planned |

---

## v0.5.0 — Speaker Intelligence

Target: Q1 2026

| Feature               | Description                                                                             | Status  |
| --------------------- | --------------------------------------------------------------------------------------- | ------- |
| Speaker Diarization   | Identify and label different speakers within single interview file.                     | Planned |
| Speaker Profiles      | Track speaker across multiple interviews. Aggregate their themes and delivery patterns. | Planned |
| Interviewer Detection | Auto-detect and filter interviewer questions from transcript.                           | Planned |

---

## v1.0.0 — Production Ready

Target: Q2 2026

| Feature                | Description                                                                    | Status  |
| ---------------------- | ------------------------------------------------------------------------------ | ------- |
| DaVinci Resolve Plugin | Direct timeline export without EDL import. Native plugin integration.          | Planned |
| Transcript Editor UI   | Web-based transcript correction with timecode sync. Round-trip persistence.    | Planned |
| Structured Logging     | JSON logs with progress, timing, errors. Integration with observability tools. | Planned |
| Full Test Coverage     | 100% coverage on core pipeline, integration tests with real audio.             | Planned |
| Documentation Site     | Dedicated docs site with tutorials, API reference, examples.                   | Planned |

---

## Future Considerations

Ideas for future exploration. Not yet scheduled.

### Editorial Intelligence

| Feature            | Description                                                                                  |
| ------------------ | -------------------------------------------------------------------------------------------- |
| B-Roll Suggestions | LLM suggests archival footage, photos, or graphics based on segment topics.                  |
| Music Sync Points  | Detect emotional peaks, suggest music cue points and tempo matches.                          |
| AI Director Mode   | Real-time interview guidance. Alerts when coverage gaps exist, suggests follow-up questions. |
| Alternate Arcs     | Generate multiple narrative structure options for same material. Director picks.             |

### Collaboration

| Feature           | Description                                                                |
| ----------------- | -------------------------------------------------------------------------- |
| Multi-User Review | Share review reports with team. Comments, annotations, approval workflows. |
| Version Control   | Track arc iterations. Compare versions, restore previous selections.       |
| Project Templates | Save and reuse profile + prompt configurations across projects.            |
| Client Preview    | Shareable password-protected preview links for stakeholder review.         |

### Platform

| Feature              | Description                                                          |
| -------------------- | -------------------------------------------------------------------- |
| Cloud Processing     | Optional cloud tier for heavy transcription and LLM. Pay-per-minute. |
| Mobile Review        | iPad app for review with AirPlay to preview on TV. Approve on couch. |
| Premiere Pro Support | Direct XML export optimized for Premiere Pro timeline import.        |
| Avid Support         | AAF export for Avid Media Composer integration.                      |

---

## Technical Debt

Ongoing improvements to code quality and maintainability.

| Item                  | Description                                                             | Priority |
| --------------------- | ----------------------------------------------------------------------- | -------- |
| Type Hints            | Fix LSP errors in librosa/litellm interfaces. Add py.typed for package. | Medium   |
| Error Messages        | Improve error messages with actionable guidance.                        | Medium   |
| Performance Profiling | Profile long interviews, optimize bottlenecks.                          | Low      |
| API Stability         | Stabilize internal APIs for plugin/extension development.               | Low      |

---

## Contributing

Have a feature request or want to contribute?

1. Open an issue: https://github.com/mwarf/plotline/issues
2. Start a discussion: https://github.com/mwarf/plotline/discussions
3. Submit a PR: https://github.com/mwarf/plotline/pulls

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release history.
